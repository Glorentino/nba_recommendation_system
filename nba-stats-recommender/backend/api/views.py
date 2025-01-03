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
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


# Define paths and load ML models dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Path to your fallback dataset
FALLBACK_DATASET = os.path.join(BASE_DIR, "player_data.csv")

# Filter the proxy pool
PROXY_POOL = filter_valid_proxies(PROXY_POOL)
if not PROXY_POOL:
    raise Exception("No valid proxies available. Please update the proxy list.")

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


# Utility for fetching player data using Selenium
def fetch_player_data_with_selenium(player_name, season):
    """
    Fetch player data using Selenium as a fallback for the NBA API.
    """
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        service = Service("/usr/local/bin/chromedriver")  # Path to ChromeDriver
        driver = webdriver.Chrome(service=service, options=chrome_options)

        player = players.find_players_by_full_name(player_name)
        if not player:
            raise ValueError("Player not found.")

        player_id = player[0]["id"]
        nba_url = f"https://www.nba.com/stats/player/{player_id}/?Season={season}"

        driver.get(nba_url)
        sleep(5)

        stats_table = driver.find_element(By.CLASS_NAME, "nba-stat-table")
        rows = stats_table.find_elements(By.TAG_NAME, "tr")

        data = []
        for row in rows[1:]:  # Skip the header row
            columns = row.find_elements(By.TAG_NAME, "td")
            data.append([col.text for col in columns])

        driver.quit()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Selenium Error: {e}")
        return None

# Prediction function with fallback mechanisms
def _predict_stat(model, player_name, team_name, threshold, stat_type):
    """
    Core function to predict a stat type using a specific model, with fallback mechanisms.
    """
    if model is None:
        return {"error": f"The model for {stat_type} is not available. Please train the models first."}, status.HTTP_503_SERVICE_UNAVAILABLE

    try:
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

        gamelog = playergamelog.PlayerGameLog(player_id=player_info[0]["id"], season="2023-24").get_data_frames()[0]
        stat_column = stat_type.upper()
        predictions = model.predict(gamelog[["PTS", "REB", "AST", "BLK"]])

        likelihood = (predictions >= threshold).mean() * 100
        return {
            "player": player_name,
            "team": team_info[0]["full_name"],
            "stat_type": stat_type,
            "likelihood": f"{likelihood:.2f}%",
        }, status.HTTP_200_OK
    except Exception as e:
        print(f"NBA API failed: {e}")
        print("Using Selenium as a fallback...")
        fallback_data = fetch_player_data_with_selenium(player_name, "2023-24")
        if fallback_data is not None:
            predictions = model.predict(fallback_data[["PTS", "REB", "AST", "BLK"]])
            likelihood = (predictions >= threshold).mean() * 100
            return {
                "player": player_name,
                "stat_type": stat_type,
                "likelihood": f"{likelihood:.2f}%",
                "source": "Selenium fallback",
            }, status.HTTP_200_OK
        else:
            return {"error": "Could not fetch player data using Selenium."}, status.HTTP_500_INTERNAL_SERVER_ERROR

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
