import os
import joblib
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
model_paths = {
    "points": os.path.join(BASE_DIR, "ml_model_points.pkl"),
    "rebounds": os.path.join(BASE_DIR, "ml_model_rebounds.pkl"),
    "blocks": os.path.join(BASE_DIR, "ml_model_blocks.pkl"),
    "assists": os.path.join(BASE_DIR, "ml_model_assists.pkl"),
}
models = {}

# Load models if files exist
for stat_type, path in model_paths.items():
    if os.path.exists(path):
        models[stat_type] = joblib.load(path)
    else:
        models[stat_type] = None


@api_view(["POST"])
def generate_and_train(request):
    """
    Generate dataset and train ML models automatically.
    """
    try:
        # Generate dataset
        generate_dataset(output_path="player_data.csv")
        print("Dataset generated successfully.")

        # Train models
        train_ml_model()
        print("Model training completed.")

        return Response({"message": "Dataset generated and models trained successfully."}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _predict_stat(model, player_name, team_name, threshold, stat_type):
    """
    Core function to predict a stat type using a specific model.
    """
    if model is None:
        return Response({"error": f"The model for {stat_type} is not available. Please train the models first."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    player_info = players.find_players_by_full_name(player_name)
    if not player_info:
        return Response({"error": "Player not found"}, status=status.HTTP_404_NOT_FOUND)

    team_info = [
        team for team in teams.get_teams()
        if team_name.lower() in team["full_name"].lower() or team_name.lower() in team["nickname"].lower()
    ]
    if not team_info:
        return Response({"error": "Team not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        current_season = get_current_season()
        gamelog = playergamelog.PlayerGameLog(player_id=player_info[0]["id"], season=current_season).get_data_frames()[0]
        team_abbreviation = team_info[0]["abbreviation"]
        games_against_team = gamelog[gamelog["MATCHUP"].str.contains(team_abbreviation)]

        if games_against_team.empty:
            return Response({"message": f"No games found against {team_info[0]['full_name']} this season."},
                            status=status.HTTP_404_NOT_FOUND)

        # Prepare input data for prediction
        feature_data = games_against_team[["REB", "AST", "BLK", "PTS"]]  # Include relevant features
        predictions = model.predict(feature_data)

        total_games = len(predictions)
        games_meeting_threshold = sum(pred >= threshold for pred in predictions)
        likelihood = (games_meeting_threshold / total_games) * 100

        game_details = games_against_team[["GAME_DATE", "MATCHUP", "PTS", "REB", "AST", "BLK"]].to_dict(orient="records")

        return Response({
            "player": player_name,
            "team": team_info[0]["full_name"],
            "stat_type": stat_type,
            "threshold": threshold,
            "likelihood": f"{likelihood:.2f}%",
            "games": game_details,
        })
    except Exception as e:
        return Response({"error": f"An error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def predict_points(request, player_name, team_name, threshold):
    return _predict_stat(models["points"], player_name, team_name, threshold, "points")


@api_view(["GET"])
def predict_rebounds(request, player_name, team_name, threshold):
    return _predict_stat(models["rebounds"], player_name, team_name, threshold, "rebounds")


@api_view(["GET"])
def predict_blocks(request, player_name, team_name, threshold):
    return _predict_stat(models["blocks"], player_name, team_name, threshold, "blocks")


@api_view(["GET"])
def predict_assists(request, player_name, team_name, threshold):
    return _predict_stat(models["assists"], player_name, team_name, threshold, "assists")