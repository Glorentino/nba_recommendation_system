import joblib
import pandas as pd
import logging
from rest_framework.response import Response
from rest_framework import status
from .dynamodb_helper import DDBQuery

logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG for more detailed logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
def stat_column_map(stat_type):
    STAT_COLUMN_MAP = {
    "points": "PTS",
    "rebounds": "REB",
    "assists": "AST",
    "blocks": "BLK",
    "steals": "STL",
    "fg3m" : "FG3M"
    }
    return STAT_COLUMN_MAP[stat_type]

class PredictionHelper:

    def _predict_stat(model, player_name, team_name, threshold, stat_type):
        if model is None:
            logger.warning("Model for %s is not available. Returning error.", stat_type)
            return {"error": f"The model for {stat_type} is not available. Please train the models first."}, status.HTTP_503_SERVICE_UNAVAILABLE

        try:
            # Fetch data directly from DynamoDB
            stats = DDBQuery.query_player_stats(player_name)
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
            stat_column = stat_column_map(stat_type.lower())
            
            # stat_column = STAT_COLUMN_MAP.get(stat_type.lower())
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