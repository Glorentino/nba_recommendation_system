import os
import joblib
import pandas as pd
import requests
from time import sleep
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players, teams
from .utils.season_utils import get_current_season
from .dataset_generator import generate_dataset
from .train_ml_model import train_ml_model

# Define paths and load ML models dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Path to your fallback dataset
FALLBACK_DATASET = os.path.join(BASE_DIR, "player_data.csv")
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
            print(f"Loaded model for {stat_type}.")
        else:
            models[stat_type] = None
            print(f"Model for {stat_type} not found. Please train the models.")
    except Exception as e:
        models[stat_type] = None
        print(f"Error loading model for {stat_type}: {e}")

@api_view(["POST"])
def generate_and_train(request):
    """
    Generate dataset and train ML models automatically.
    """
    try:
        generate_dataset(output_file="player_data.csv")  # Generate dataset
        train_ml_model()  # Train models
        return Response({"message": "Dataset generated and models trained successfully."}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
STAT_COLUMN_MAP = {
    "points": "PTS",
    "rebounds": "REB",
    "assists": "AST",
    "blocks": "BLK",
}
def calculate_dynamic_threshold(games_against_team, stat_type):
    """
    Calculate a dynamic threshold based on the player's historical stats against the team.

    Args:
        games_against_team (DataFrame): Filtered game log data for games against a specific team.
        stat_type (str): Human-readable stat type (e.g., "points", "rebounds").

    Returns:
        float: Dynamic threshold value based on historical stats, or None if insufficient data.
    """
    # Map the stat_type to the actual column name
    stat_column = STAT_COLUMN_MAP.get(stat_type.lower())
    if not stat_column:
        print(f"Invalid stat type: {stat_type}")
        return None

    if games_against_team.empty:
        print(f"No data available to calculate dynamic threshold for {stat_type}.")
        return None

    if stat_column not in games_against_team.columns:
        print(f"Column '{stat_column}' not found in the dataset.")
        return None

    avg_stat = games_against_team[stat_column].mean()
    std_dev_stat = games_against_team[stat_column].std()

    if pd.isna(avg_stat) or pd.isna(std_dev_stat):
        print(f"Insufficient data to calculate threshold for {stat_type}.")
        return None

    dynamic_threshold = avg_stat + (0.5 * std_dev_stat)
    print(f"Dynamic threshold for {stat_type}: {dynamic_threshold:.2f}")
    return dynamic_threshold


def fetch_gamelog_with_retries(player_id, season, max_retries=5, backoff_factor=2):
    """
    Fetch player game log with retries on rate-limit errors.

    Args:
        player_id (str): The player's ID.
        season (str): The season to fetch data for.
        max_retries (int): Maximum number of retries.
        backoff_factor (int): Backoff multiplier for retries.

    Returns:
        DataFrame: Game log data.
    """
    for attempt in range(max_retries):
        try:
            return playergamelog.PlayerGameLog(player_id=player_id, season=season).get_data_frames()[0]
        except requests.exceptions.RequestException as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                wait_time = backoff_factor * (2 ** attempt)
                print(f"Rate limit hit. Retrying in {wait_time} seconds...")
                sleep(wait_time)
            else:
                raise e
    raise Exception("Max retries exceeded. Could not fetch player game log.")

def _predict_stat(model, player_name, team_name, threshold, stat_type):
    """
    Core function to predict a stat type using a specific model, with a fallback mechanism.
    """
    if model is None:
        return {"error": f"The model for {stat_type} is not available. Please train the models first."}, status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        # Try fetching player and team info from NBA API
        player_info = players.find_players_by_full_name(player_name)
        if not player_info:
            raise ValueError("Player not found")

        team_info = [
            team for team in teams.get_teams()
            if team_name.lower() in team["full_name"].lower() or
            team_name.lower() in team["nickname"].lower() or
            team_name.lower() in team["abbreviation"].lower()
        ]
        if not team_info:
            raise ValueError(f"Team '{team_name}' not found.")

        current_season = get_current_season()
        gamelog = fetch_gamelog_with_retries(player_info[0]["id"], current_season)
        team_abbreviation = team_info[0]["abbreviation"]
        games_against_team = gamelog[gamelog["MATCHUP"].str.contains(team_abbreviation)]

        if games_against_team.empty:
            return {"message": f"No games found against {team_info[0]['full_name']} this season."}, status.HTTP_404_NOT_FOUND

        stat_column = STAT_COLUMN_MAP.get(stat_type.lower())
        if stat_column is None:
            return {"error": f"Invalid stat type: {stat_type}"}, status.HTTP_400_BAD_REQUEST

        # Calculate dynamic threshold if not provided
        if threshold is None or threshold == 0:
            dynamic_threshold = calculate_dynamic_threshold(games_against_team, stat_column)
            if dynamic_threshold is None:
                return {"error": f"Not enough data to calculate a dynamic threshold for {stat_type}"}, status.HTTP_400_BAD_REQUEST
            threshold = dynamic_threshold

        # Prepare input data for prediction
        feature_data = games_against_team[["PTS", "REB", "AST", "BLK"]]
        predictions = model.predict(feature_data)

        # Calculate likelihood dynamically
        total_games = len(predictions)
        games_meeting_threshold = sum(games_against_team[stat_column] >= threshold)
        likelihood = (games_meeting_threshold / total_games) * 100

        game_details = games_against_team[["GAME_DATE", "MATCHUP", "PTS", "REB", "AST", "BLK"]].to_dict(orient="records")

        return {
            "player": player_name,
            "team": team_info[0]["full_name"],
            "stat_type": stat_type,
            "threshold": threshold,
            "likelihood": f"{likelihood:.2f}%",
            "games": game_details,
        }, status.HTTP_200_OK
    except Exception as e:
        print(f"Error with NBA API: {e}")
        # Fallback to local dataset
        if os.path.exists(FALLBACK_DATASET):
            try:
                fallback_data = pd.read_csv(FALLBACK_DATASET)
                filtered_data = fallback_data[(fallback_data["Player"] == player_name) & (fallback_data["Team"] == team_name)]
                if filtered_data.empty:
                    return {"error": f"No data available for {player_name} in {team_name}."}, status.HTTP_404_NOT_FOUND

                stat_value = filtered_data[stat_type.upper()].mean()
                return {
                    "player": player_name,
                    "team": team_name,
                    "stat_type": stat_type,
                    "fallback_value": stat_value,
                    "message": "Prediction made using fallback dataset.",
                }, status.HTTP_200_OK
            except Exception as fallback_error:
                print(f"Error with fallback mechanism: {fallback_error}")
                return {"error": f"An error occurred: {fallback_error}"}, status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            return {"error": "Fallback dataset not found. Please ensure 'player_data.csv' is available."}, status.HTTP_500_INTERNAL_SERVER_ERROR
@api_view(["GET"])
def predict_points(request, player_name, team_name, threshold):
    try:
        response, status_code = _predict_stat(models["points"], player_name, team_name, threshold, "points")
        return Response(response, status=status_code)
    except Exception as e:
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def predict_rebounds(request, player_name, team_name, threshold):
    try:
        response, status_code = _predict_stat(models["rebounds"], player_name, team_name, threshold, "rebounds")
        return Response(response, status=status_code)
    except Exception as e:
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["GET"])
def predict_blocks(request, player_name, team_name, threshold):
    try:
        response, status_code = _predict_stat(models["blocks"], player_name, team_name, threshold, "blocks")
        return Response(response, status=status_code)
    except Exception as e:
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def predict_assists(request, player_name, team_name, threshold):
    try:
        response, status_code = _predict_stat(models["assists"], player_name, team_name, threshold, "assists")
        return Response(response, status=status_code)
    except Exception as e:
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
