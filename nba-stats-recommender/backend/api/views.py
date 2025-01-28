import os
import joblib
import pandas as pd
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .utils.dynamodb_helper import DDBQuery
from .utils.prediction_helper import PredictionHelper
from .dataset_generator import generate_dataset
from .train_ml_model import train_ml_model

logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG for more detailed logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define paths and load ML models dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

model_paths = {
    "points": os.path.join(BASE_DIR, "ml_model_points.pkl"),
    "rebounds": os.path.join(BASE_DIR, "ml_model_rebounds.pkl"),
    "blocks": os.path.join(BASE_DIR, "ml_model_blocks.pkl"),
    "assists": os.path.join(BASE_DIR, "ml_model_assists.pkl"),
    "steals": os.path.join(BASE_DIR, "ml_model_steals.pkl"),
    "fg3m": os.path.join(BASE_DIR, "ml_model_fg3m.pkl"),
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
        player_names = DDBQuery.query_all_players()  # Fetch player names from DynamoDB
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
        team_names = DDBQuery.query_all_teams()  # Fetch team names from DynamoDB
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
def get_player_team(request, player_name):
    """
    Fetches a players own team from DDB
    """
    try:
        stats = DDBQuery.query_player_stats(player_name)
        if stats.empty:
            return Response({"error": "Player not found"}, status=status.HTTP_404_NOT_FOUND)
        player_team = stats["MATCHUP"].iloc[0].split(" ")[0]
        return Response({"team": player_team}, status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"An error occured: {e}"}, status=status.HTTP_500_INTERNAL_ERROR)


@api_view(["GET"])
def player_trends(request, player_name):
    """
    Returns a player's performance trends over time
    """
    try:
        #Fetch a player stats from DynamoDB
        stats = DDBQuery.query_player_stats(player_name)
        if stats.empty:
            logger.warning("No stats found for player %s.", player_name)
            return Response({"error": f"No stats found for player {player_name}."}, status=status.HTTP_404_NOT_FOUND)

        if "GAME_DATE" not in stats.columns or "PTS" not in stats.columns:
            logger.warning("Required columns are missing for player %s.", player_name)
            return Response({"error": "Required columns are missing in the data."}, status=status.HTTP_404_NOT_FOUND)
        
        # Sort by GAME_DATE for chronological trends
        stats["GAME_DATE"] = pd.to_datetime(stats["GAME_DATE"])
        stats = stats.sort_values("GAME_DATE")
        
        # Select columns for trends
        trends = stats[["GAME_DATE", "FG3M", "PTS", "REB", "AST", "BLK", "STL"]].to_dict(orient="records")
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
        team_names = DDBQuery.query_all_teams()
        if not team_names:
            logger.warning("No team names available.")
            return Response({"error": "No team names available."}, status=status.HTTP_404_NOT_FOUND)
        
        team_stats = []
        for team in team_names:
            # Fetch stats for each team (or aggregate in DynamoDB query for optimization)
            stats = DDBQuery.query_team_stats(team)
            if not stats.empty:
                avg_stats = {
                    "team": team,
                    "average_points": stats["PTS"].mean(),
                    "average_rebounds":stats["REB"].mean(), 
                    "average_assists": stats["AST"].mean(),
                    "average_blocks":stats["BLK"].mean(), 
                    "average_steals":stats["STL"].mean(),
                    "average_3pointers":stats["FG3M"].mean(),
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
        stats = DDBQuery.query_player_stats(player_name)
        if stats.empty:
            logger.warning("No stats found for player %s.", player_name)
            return Response({"error": f"No stats found for player {player_name}."}, status=status.HTTP_404_NOT_FOUND)
        
        if "MATCHUP" not in stats.columns or "PTS" not in stats.columns:
            logger.warning("Required columns are missing for player %s.", player_name)
            return Response({"error": "Required columns are missing in the data."}, status=status.HTTP_400_BAD_REQUEST)
        
        # group by opponent (team) and calculate averages
        stats["Opponent"] = stats["MATCHUP"].str.extract(r'vs\. (\w+)|@ (\w+)', expand=True).bfill(axis=1)[0]
        averages = stats.groupby("Opponent")[["PTS","FG3M", "REB", "AST", "BLK", "STL"]].mean().reset_index()
        averages_dict = averages.to_dict(orient="records")
        
        logger.info("Calculated averages against opponents for player %s.", player_name)
        return Response({"player": player_name, "averages_vs_opponents": averages_dict}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error fetching averages for player %s: %s", player_name, e)
        return Response({"error":f"An error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  
    

@api_view(["GET"])
def recommend_similar_players(request, player_name, opponent_team, stat_type, threshold):
    try:
        logger.info(f"Fetching recommendations for player: {player_name} against {opponent_team}.")

        # Fetch the player's team
        player_stats = DDBQuery.query_player_stats(player_name)
        if player_stats.empty or "TEAM_NAME" not in player_stats.columns:
            return Response({"error": f"No stats or TEAM_NAME for player '{player_name}'."}, status=status.HTTP_404_NOT_FOUND)
        
        player_team = player_stats["TEAM_NAME"].iloc[0]

        # Get all players from the same team excluding the selected player
        team_players = DDBQuery.query_players_from_same_team(player_team)
        team_players = [p for p in team_players if p != player_name]

        if not team_players:
            logger.warning(f"No other players found on team '{player_team}'.")
            return Response({"message": f"No other players found on team '{player_team}'."}, status=status.HTTP_200_OK)

        # Initialize recommendations
        recommendations = []

        # Predict likelihood for each player in the team
        for teammate in team_players:
            likelihood_response, status_code = PredictionHelper._predict_stat(
                models.get(stat_type), 
                teammate, 
                opponent_team, 
                threshold, 
                stat_type
            )
            if status_code == status.HTTP_200_OK:
                likelihood = likelihood_response.get("likelihood", "0%").strip('%')
                recommendations.append({
                    "player_name": teammate,
                    "likelihood": float(likelihood)
                })

        # Sort recommendations by likelihood and return the top 5
        recommendations = sorted(recommendations, key=lambda x: x["likelihood"], reverse=True)[:5]
        return Response({"recommendations": recommendations}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in recommend_similar_players: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def predict_points(request, player_name, team_name, threshold):
    try:
        logger.info("Predicting points for player %s against team %s with threshold %s.", player_name, team_name, threshold)
        response, status_code = PredictionHelper._predict_stat(models["points"], player_name, team_name, threshold, "points")
        return Response(response, status=status_code)
    except Exception as e:
        logger.error("Error in predict_points: %s", e)
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def predict_rebounds(request, player_name, team_name, threshold):
    try:
        logger.info("Predicting rebounds for player %s against team %s with threshold %s.", player_name, team_name, threshold)
        response, status_code = PredictionHelper._predict_stat(models["rebounds"], player_name, team_name, threshold, "rebounds")
        return Response(response, status=status_code)
    except Exception as e:
        logger.error("Error in predict_rebounds: %s", e)
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def predict_blocks(request, player_name, team_name, threshold):
    try:
        logger.info("Predicting blocks for player %s against team %s with threshold %s.", player_name, team_name, threshold)
        response, status_code = PredictionHelper._predict_stat(models["blocks"], player_name, team_name, threshold, "blocks")
        return Response(response, status=status_code)
    except Exception as e:
        logger.error("Error in predict_blocks: %s", e)
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def predict_assists(request, player_name, team_name, threshold):
    try:
        logger.info("Predicting assists for player %s against team %s with threshold %s.", player_name, team_name, threshold)
        response, status_code = PredictionHelper._predict_stat(models["assists"], player_name, team_name, threshold, "assists")
        return Response(response, status=status_code)
    except Exception as e:
        logger.error("Error in predict_assists: %s", e)
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def predict_steals(request, player_name, team_name, threshold):
    try:
        logger.info("Predicting steals for player %s against team %s with threshold %s.", player_name, team_name, threshold)
        response, status_code = PredictionHelper._predict_stat(models["steals"], player_name, team_name, threshold, "steals")
        return Response(response, status=status_code)
    except Exception as e:
        logger.error("Error in predict_steals: %s", e)
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(["GET"])
def predict_3pointers(request, player_name, team_name, threshold):
    try:
        logger.info("Predicting 3points for player %s against team %s with threshold %s.", player_name, team_name, threshold)
        response, status_code = PredictionHelper._predict_stat(models["fg3m"], player_name, team_name, threshold, "fg3m")
        return Response(response, status=status_code)
    except Exception as e:
        logger.error("Error in predict_fg3m: %s", e)
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)