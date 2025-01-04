import boto3
import pandas as pd
from botocore.exceptions import ClientError
from decimal import Decimal

# Define the constants
DYNAMODB_TABLE = "PlayerStats"
REGION = "us-east-1"

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


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
            "HOME_AWAY": row["HOME_AWAY"],
            "POINTS_THRESHOLD": int(row["POINTS_THRESHOLD"]),
            "REBOUNDS_THRESHOLD": int(row["REBOUNDS_THRESHOLD"]),
            "BLOCKS_THRESHOLD": int(row["BLOCKS_THRESHOLD"]),
            "ASSISTS_THRESHOLD": int(row["ASSISTS_THRESHOLD"]),
            "ROLLING_PTS_AVG": convert_to_decimal(row["ROLLING_PTS_AVG"]),
            "ROLLING_REB_AVG": convert_to_decimal(row["ROLLING_REB_AVG"]),
            "ROLLING_AST_AVG": convert_to_decimal(row["ROLLING_AST_AVG"]),
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
            print(f"Uploaded data for {row['PLAYER_NAME']} on {row['GAME_DATE']}")
        except ClientError as e:
            print(f"Error uploading data: {e}")


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
            return pd.DataFrame(filtered_items)
        return pd.DataFrame(items)
    except ClientError as e:
        print(f"Error querying data: {e}")
        return pd.DataFrame()