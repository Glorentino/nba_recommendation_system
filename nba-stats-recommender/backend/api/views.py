import os
import joblib
import pandas as pd
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .utils.dynamodb_helper import query_player_stats, query_all_players, query_all_teams, query_team_stats
from .dataset_generator import generate_dataset
from .train_ml_model import train_ml_model

logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG for more detailed logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define paths and load ML models dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYER_DATA_PATH = os.path.join(BASE_DIR, "utils/player_data.csv")

model_paths = {
    "points": os.path.join(BASE_DIR, "ml_model_points.pkl"),
    "rebounds": os.path.join(BASE_DIR, "ml_model_rebounds.pkl"),
    "blocks": os.path.join(BASE_DIR, "ml_model_blocks.pkl"),
    "assists": os.path.join(BASE_DIR, "ml_model_assists.pkl"),
}

models = {}
for stat_type, path in model_paths.items():
    try:
        if os.path.exists(path):
            models[stat_type] = joblib.load(path)
            logger.info("Loaded model for %s.", stat_type)
        else:
            models[stat_type] = None
            logger.warning("Model for %s not found. Please train the models.", stat_type)
    except Exception as e:
        models[stat_type] = None
        logger.error("Error loading model for %s: %s", stat_type, e)


STAT_COLUMN_MAP = {
    "points": "PTS",
    "rebounds": "REB",
    "assists": "AST",
    "blocks": "BLK",
}

@api_view(["POST"])
def generate_and_train(request):
    """
    Generate dataset and train ML models automatically.
    """
    try:
        generate_dataset(output_file="utils/player_data.csv")  # Generate dataset
        train_ml_model()  # Train models
        logger.info("Dataset generated and models trained successfully.")
        return Response({"message": "Dataset generated and models trained successfully."}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error during dataset generation and model training: %s", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def get_player_names(request):
    """
    Fetch all unique player names from DynamoDB.
    """
    try:
        player_names = query_all_players()  # Fetch player names from DynamoDB
        if not player_names:
            logger.warning("No player names found.")
            return Response({"message": "No player names found."}, status=status.HTTP_404_NOT_FOUND)
        player_names_sorted = sorted(player_names)  # Sort player names alphabetically
        logger.info("Fetched %d player names.", len(player_names_sorted))
        return Response(player_names_sorted, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error fetching player names: %s", e)
        return Response({"error": f"An error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def get_team_names(request):
    """
    Fetch all unique team names from DynamoDB.
    """
    try:
        team_names = query_all_teams()  # Fetch team names from DynamoDB
        if not team_names:
            logger.warning("No team names found.")
            return Response({"message": "No team names found."}, status=status.HTTP_404_NOT_FOUND)
        team_names_sorted = sorted(team_names)  # Sort team names alphabetically
        logger.info("Fetched %d team names.", len(team_names_sorted))
        return Response(team_names_sorted, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error fetching team names: %s", e)
        return Response({"error": f"An error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def player_trends(request, player_name):
    """
    Returns a player's performance trends over time
    """
    try:
        #Fetch a player stats from DynamoDB
        stats = query_player_stats(player_name)
        if stats.empty:
            logger.warning("No stats found for player %s.", player_name)
            return Response({"error": f"No stats found for player {player_name}."}, status=status.HTTP_404_NOT_FOUND)
    
        # Sort by GAME_DATE for chronological trends
        stats["GAME_DATE"] = pd.to_datetime(stats["GAME_DATE"])
        stats = stats.sort_values("GAME_DATE")
        
        # Select columns for trends
        trends = stats[["GAME_DATE", "PTS", "REB", "AST", "BLK"]].to_dict(orient="records")
        logger.info("Fetched trends for player %s.", player_name)
        return Response({"player": player_name, "trends":trends}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error fetching trends for player %s: %s", player_name, e)
        return Response({"error":f"An error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def team_comparisons(request):
    """
    Compare stats across teams
    """
    try:
        # fetch all teams data (I should aggregate this in my database some how for efficiency)
        team_names = query_all_teams()
        team_stats = []
        
        for team in team_names:
            # Fetch stats for each team (or aggregate in DynamoDB query for optimization)
            stats = query_team_stats(team)
            if not stats.empty:
                avg_stats = {
                    "team": team,
                    "average_points": stats["PTS"].mean(),
                    "average_rebounds":stats["REB"].mean(), 
                    "average_assists": stats["AST"].mean(),
                    "average_blocks":stats["BLK"].mean(), 
                }
                team_stats.append(avg_stats)
        logger.info("Team comparisons calculated for %d teams.", len(team_stats))
        return Response({"team_comparison": team_stats}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error in team comparisons: %s", e)
        return Response({"error":f"An error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)        

@api_view(["GET"])
def player_averages_vs_opponents(request, player_name):
    """
    Returns a player's average stats against all opponents
    """
    try:
        # Fetch player stats
        stats = query_player_stats(player_name)
        if stats.empty:
            return Response({"error": f"No stats found for player {player_name}."}, status=status.HTTP_404_NOT_FOUND)
        # group by opponent (team) and calculate averages
        stats["Opponent"] = stats["MATCHUP"].str.extract(r'vs\. (\w+)|@ (\w+)', expand=True).bfill(axis=1)[0]
        averages = stats.groupby("Opponent")[["PTS", "REB", "AST", "BLK"]].mean().reset_index()
        
        averages_dict = averages.to_dict(orient="records")
        logger.info("Calculated averages against opponents for player %s.", player_name)
        return Response({"player": player_name, "averages_vs_opponents": averages_dict}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error fetching averages for player %s: %s", player_name, e)
        return Response({"error":f"An error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  

def calculate_dynamic_threshold(games_against_team, stat_type):
    stat_column = STAT_COLUMN_MAP.get(stat_type.lower())
    if not stat_column:
        print(f"Invalid stat type: {stat_type}")
        return None

    if games_against_team.empty:
        print(f"No data available to calculate dynamic threshold for {stat_type}.")
        return None

    avg_stat = games_against_team[stat_column].mean()
    std_dev_stat = games_against_team[stat_column].std()

    if pd.isna(avg_stat) or pd.isna(std_dev_stat):
        print(f"Insufficient data to calculate threshold for {stat_type}.")
        return None

    dynamic_threshold = avg_stat + (0.5 * std_dev_stat)
    print(f"Dynamic threshold for {stat_type}: {dynamic_threshold:.2f}")
    return dynamic_threshold


def _predict_stat(model, player_name, team_name, threshold, stat_type):
    if model is None:
        logger.warning("Model for %s is not available. Returning error.", stat_type)
        return {"error": f"The model for {stat_type} is not available. Please train the models first."}, status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        # Fetch data directly from DynamoDB
        stats = query_player_stats(player_name)
        if stats.empty:
            logger.warning("No stats found for player %s.", player_name)
            return {"error": f"No stats found for player {player_name}."}, status.HTTP_404_NOT_FOUND

        # Sort stats by GAME_DATE and get the last 5 games
        stats["GAME_DATE"] = pd.to_datetime(stats["GAME_DATE"])
        recent_games = stats.sort_values(by="GAME_DATE", ascending=False).head(5)
        logger.info("Fetched last 5 recent games for player %s.", player_name)
        
        # Filter games against the specified team
        games_against_team = stats[stats["MATCHUP"].str.contains(team_name, case=False, na=False)]

        if games_against_team.empty:
            logger.info(
                "No games found for player %s against team %s. Using only recent games.", 
                player_name, 
                team_name
            )
        
        # Combine recent games and games against the team
        combined_games = pd.concat([games_against_team, recent_games]).drop_duplicates()

        if combined_games.empty:
            logger.warning(
                "No data available to make a prediction for player %s against team %s.", 
                player_name, 
                team_name
            )
            return {"error": "No data available to make a prediction."}, status.HTTP_404_NOT_FOUND

        stat_column = STAT_COLUMN_MAP.get(stat_type.lower())
        if not stat_column:
            logger.error("Invalid stat type: %s", stat_type)
            return {"error": f"Invalid stat type: {stat_type}"}, status.HTTP_400_BAD_REQUEST

        # Calculate the likelihood based on the combined dataset
        total_games = len(combined_games)
        games_meeting_threshold = sum(combined_games[stat_column] >= threshold)
        likelihood = (games_meeting_threshold / total_games) * 100
        logger.info(
            "Prediction for %s (%s): Total games: %d, Meeting threshold: %d, Likelihood: %.2f%%.",
            player_name, stat_type, total_games, games_meeting_threshold, likelihood
        )
        
        # Prepare the response
        recent_game_details = recent_games.to_dict(orient="records")
        game_details = games_against_team.to_dict(orient="records")

        return {
            "player": player_name,
            "team": team_name,
            "stat_type": stat_type,
            "threshold": threshold,
            "likelihood": f"{likelihood:.2f}%",
            "recent_games": recent_game_details,  # Include recent games
            "games": game_details,  # Include games against the team
        }, status.HTTP_200_OK
    except Exception as e:
        logger.error("Error predicting stats for player %s: %s", player_name, e)
        return {"error": f"An error occurred: {e}"}, status.HTTP_500_INTERNAL_SERVER_ERROR

@api_view(["GET"])
def predict_points(request, player_name, team_name, threshold):
    try:
        logger.info("Predicting points for player %s against team %s with threshold %s.", player_name, team_name, threshold)
        response, status_code = _predict_stat(models["points"], player_name, team_name, threshold, "points")
        return Response(response, status=status_code)
    except Exception as e:
        logger.error("Error in predict_points: %s", e)
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def predict_rebounds(request, player_name, team_name, threshold):
    try:
        logger.info("Predicting rebounds for player %s against team %s with threshold %s.", player_name, team_name, threshold)
        response, status_code = _predict_stat(models["rebounds"], player_name, team_name, threshold, "rebounds")
        return Response(response, status=status_code)
    except Exception as e:
        logger.error("Error in predict_rebounds: %s", e)
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def predict_blocks(request, player_name, team_name, threshold):
    try:
        logger.info("Predicting blocks for player %s against team %s with threshold %s.", player_name, team_name, threshold)
        response, status_code = _predict_stat(models["blocks"], player_name, team_name, threshold, "blocks")
        return Response(response, status=status_code)
    except Exception as e:
        logger.error("Error in predict_blocks: %s", e)
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def predict_assists(request, player_name, team_name, threshold):
    try:
        logger.info("Predicting assists for player %s against team %s with threshold %s.", player_name, team_name, threshold)
        response, status_code = _predict_stat(models["assists"], player_name, team_name, threshold, "assists")
        return Response(response, status=status_code)
    except Exception as e:
        logger.error("Error in predict_assists: %s", e)
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)