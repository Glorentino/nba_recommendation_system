import boto3
import pandas as pd
from botocore.exceptions import ClientError
from decimal import Decimal
import logging 
from boto3.dynamodb.conditions import Attr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define the constants
DYNAMODB_TABLE = "PlayerStats"
REGION = "us-east-1"

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


def query_all_players():
    """
    Fetch all unique player names from DynamoDB.
    """
    try:
        player_names = set()
        response = table.scan(ProjectionExpression="PLAYER_NAME")
        while True:
            items = response.get("Items", [])
            player_names.update(item["PLAYER_NAME"] for item in items if "PLAYER_NAME" in item)
            if 'LastEvaluatedKey' not in response:
                break
            response = table.scan(ProjectionExpression="PLAYER_NAME", ExclusiveStartKey=response['LastEvaluatedKey'])
        logging.info("Fetched %d unique player names.", len(player_names))
        return list(player_names)
    except Exception as e:
        logger.error("Error fetching players: %s", e)
        return []

def query_all_teams():
    """
    Fetch all unique team names from DynamoDB.
    """
    try:
        response = table.scan(ProjectionExpression="MATCHUP")
        items = response.get("Items", [])
        team_names = set()
        for item in items:
            if "MATCHUP" in item:
                matchup = item["MATCHUP"]
                teams = matchup.split(" vs. ") if " vs. " in matchup else matchup.split(" @ ")
                team_names.update(teams)
        logger.info("Fetched %d unique team names.", len(team_names))
        return list(team_names)
    except ClientError as e:
        logger.error("Error fetching team names: %s", e)
        return []

def convert_to_decimal(value):
    """
    Convert numeric values to Decimal for DynamoDB compatibility.
    """
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return value


def upload_to_dynamodb(dataframe):
    """
    Upload a Pandas DataFrame to DynamoDB.
    """
    for _, row in dataframe.iterrows():
        item = {
            "SEASON_ID": str(row["SEASON_ID"]),
            "Player_ID": str(row["Player_ID"]),
            "Game_ID": str(row["Game_ID"]),
            "GAME_DATE": row["GAME_DATE"],
            "MATCHUP": row["MATCHUP"],
            "WL": row["WL"],
            "PLAYER_NAME": row["PLAYER_NAME"],
            "TEAM_NAME": row["TEAM_NAME"],
            "HOME_AWAY": row["HOME_AWAY"],
            "POINTS_THRESHOLD": int(row["POINTS_THRESHOLD"]),
            "REBOUNDS_THRESHOLD": int(row["REBOUNDS_THRESHOLD"]),
            "BLOCKS_THRESHOLD": int(row["BLOCKS_THRESHOLD"]),
            "ASSISTS_THRESHOLD": int(row["ASSISTS_THRESHOLD"]),
            "STEALS_THRESHOLD": int(row["STEALS_THRESHOLD"]),
            "ROLLING_PTS_AVG": convert_to_decimal(row["ROLLING_PTS_AVG"]),
            "ROLLING_REB_AVG": convert_to_decimal(row["ROLLING_REB_AVG"]),
            "ROLLING_BLK_AVG": convert_to_decimal(row["ROLLING_BLK_AVG"]),
            "ROLLING_AST_AVG": convert_to_decimal(row["ROLLING_AST_AVG"]),
            "ROLLING_STL_AVG": convert_to_decimal(row["ROLLING_STL_AVG"]),
        }

        # Include non-null values for additional fields
        for field in [
            "MIN", "FGM", "FGA", "FG_PCT", "FG3M", "FG3A", "FG3_PCT",
            "FTM", "FTA", "FT_PCT", "OREB", "DREB", "REB", "AST", "STL",
            "BLK", "TOV", "PF", "PTS", "PLUS_MINUS", "VIDEO_AVAILABLE"
        ]:
            if pd.notna(row[field]):
                item[field] = convert_to_decimal(row[field])

        try:
            table.put_item(Item=item)
            logger.info("Uploaded data for %s on %s", row["PLAYER_NAME"], row["GAME_DATE"])
        except ClientError as e:
            logger.error("Error uploading data: %s", e)
            


def query_player_stats(player_name, start_date=None, end_date=None):
    """
    Query player stats from DynamoDB.
    """
    try:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("PLAYER_NAME").eq(player_name)
        )
        items = response.get("Items", [])
        if start_date or end_date:
            # Filter the results based on the provided date range
            filtered_items = [
                item for item in items
                if (not start_date or item["GAME_DATE"] >= start_date) and
                   (not end_date or item["GAME_DATE"] <= end_date)
            ]
            logger.info("Fetched %d stats for player %s within the date range.", len(filtered_items), player_name)
            return pd.DataFrame(filtered_items)
        logger.info("Fetched %d stats for player %s.", len(items), player_name)
        return pd.DataFrame(items)
    except ClientError as e:
        logger.error("Error querying stats for player %s: %s", player_name, e)
        return pd.DataFrame()

def query_team_stats(team_name):
    """
    Fetch all stats for games played by a specific team.
    """
    try:
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("MATCHUP").contains(team_name)
        )
        items = response.get("Items", [])
        
        # Handle pagination (if necessary)
        while "LastEvaluatedKey" in response:
            response = table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr("MATCHUP").contains(team_name),
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))
        
        if not items:
            return pd.DataFrame()  # Return empty DataFrame if no results found

        # Convert results to DataFrame
        stats_df = pd.DataFrame(items)
        
        # Ensure numerical columns are appropriately typed
        numeric_columns = [
            "PTS", "REB", "AST", "BLK", "STL", "MIN", "FGM", "FGA", "FG_PCT", "FG3M",
            "FG3A", "FG3_PCT", "FTM", "FTA", "FT_PCT", "OREB", "DREB", "TOV", "PF", "PLUS_MINUS"
        ]
        for col in numeric_columns:
            if col in stats_df.columns:
                stats_df[col] = pd.to_numeric(stats_df[col], errors="coerce")
        logger.info("Fetched %d stats for team %s.", len(items), team_name)
        return stats_df

    except ClientError as e:
        logger.error("Error querying stats for team %s: %s", team_name, e)
        return pd.DataFrame()
    
def query_all_player_stats():
    """
    Fetch all player stats from DynamoDB.
    """
    try:
        all_player_stats = []
        response = table.scan()
        while True:
            items = response.get("Items", [])
            all_player_stats.extend(items)
            if 'LastEvaluatedKey' not in response:
                break
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        
        # Convert results to a dictionary with player names as keys
        player_stats_dict = {}
        for item in all_player_stats:
            player_name = item.get("PLAYER_NAME")
            if player_name not in player_stats_dict:
                player_stats_dict[player_name] = []
            player_stats_dict[player_name].append(item)
        
        # Convert stats for each player into DataFrames
        for player_name, stats in player_stats_dict.items():
            player_stats_dict[player_name] = pd.DataFrame(stats)
        
        logger.info("Fetched stats for %d players.", len(player_stats_dict))
        return player_stats_dict

    except Exception as e:
        logger.error("Error fetching all player stats: %s", e)
        return {}