import os
import joblib
import pandas as pd
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .utils.dynamodb_helper import query_player_stats
from .dataset_generator import generate_dataset
from .train_ml_model import train_ml_model

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
            print(f"Loaded model for {stat_type}.")
        else:
            models[stat_type] = None
            print(f"Model for {stat_type} not found. Please train the models.")
    except Exception as e:
        models[stat_type] = None
        print(f"Error loading model for {stat_type}: {e}")


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
        return Response({"message": "Dataset generated and models trained successfully."}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        return {"error": f"The model for {stat_type} is not available. Please train the models first."}, status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        # Fetch data directly from DynamoDB
        stats = query_player_stats(player_name)
        if stats.empty:
            return {"error": f"No stats found for player {player_name}."}, status.HTTP_404_NOT_FOUND

        games_against_team = stats[stats["MATCHUP"].str.contains(team_name, case=False, na=False)]
        if games_against_team.empty:
            return {"error": f"No games found for player {player_name} against team {team_name}."}, status.HTTP_404_NOT_FOUND

        stat_column = STAT_COLUMN_MAP.get(stat_type.lower())
        if not stat_column:
            return {"error": f"Invalid stat type: {stat_type}"}, status.HTTP_400_BAD_REQUEST

        # Calculate dynamic threshold if not provided
        if threshold is None or threshold == 0:
            dynamic_threshold = calculate_dynamic_threshold(games_against_team, stat_type)
            if dynamic_threshold is None:
                return {"error": f"Not enough data to calculate a dynamic threshold for {stat_type}"}, status.HTTP_400_BAD_REQUEST
            threshold = dynamic_threshold

        # Prepare input data for prediction
        feature_data = games_against_team[["PTS", "REB", "AST", "BLK"]]
        predictions = model.predict(feature_data)

        total_games = len(predictions)
        games_meeting_threshold = sum(games_against_team[stat_column] >= threshold)
        likelihood = (games_meeting_threshold / total_games) * 100

        game_details = games_against_team.to_dict(orient="records")
        return {
            "player": player_name,
            "team": team_name,
            "stat_type": stat_type,
            "threshold": threshold,
            "likelihood": f"{likelihood:.2f}%",
            "games": game_details,
        }, status.HTTP_200_OK
    except Exception as e:
        return {"error": f"An error occurred: {e}"}, status.HTTP_500_INTERNAL_SERVER_ERROR


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