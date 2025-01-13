import os
import time
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
import logging

# Create logs directory
os.makedirs("logs", exist_ok=True)

# Set up logging
logging.basicConfig(
    filename="logs/dataset_generator.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_FILE = os.path.join(BASE_DIR, "utils/player_data.csv")
#PLAYER_DIR = os.path.join(BASE_DIR, "player_data")  # Directory for intermediate player-level files
#os.makedirs(PLAYER_DIR, exist_ok=True)

FEATURES = ["GAME_DATE", "MATCHUP", "PTS", "REB", "AST", "BLK","STL", "PLAYER_NAME", "HOME_AWAY"]
THRESHOLD_COLUMNS = {
    "POINTS_THRESHOLD": ("PTS", 10),
    "REBOUNDS_THRESHOLD": ("REB", 5),
    "BLOCKS_THRESHOLD": ("BLK", 1),
    "ASSISTS_THRESHOLD": ("AST", 3),
    "STEALS_THRESHOLD": ("STL", 1),
}

# Dynamic thresholds
DYNAMIC_THRESHOLDS = {
    "ROLLING_PTS_AVG": ("PTS", 5),
    "ROLLING_REB_AVG": ("REB", 5),
    "ROLLING_BLK_AVG": ("BLK", 5),
    "ROLLING_AST_AVG": ("AST", 5),
    "ROLLING_STL_AVG": ("STL", 5),
}

def get_current_season():
    current_year = datetime.now().year
    if datetime.now().month > 9:  # After September, new season starts
        return f"{current_year}-{str(current_year + 1)[2:]}"
    else:
        return f"{current_year - 1}-{str(current_year)[2:]}"

def get_all_active_players():
    try:
        active_players = players.get_active_players()
        if not active_players:
            logger.warning("No active players found. Check the NBA API.")
        return active_players
    except Exception as e:
        logger.error(f"Error fetching active players: {e}")
        return []


def get_player_gamelog(player_name, player_id, season, retries=3, delay=5):
    for attempt in range(retries):
        try:
            gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season).get_data_frames()[0]
            return gamelog
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for player ID {player_id} ({player_name}): {e}")
            logging.error(f"Attempt {attempt + 1} failed for player ID {player_id} ({player_name}): {e}")
            time.sleep(delay)
            

    logging.error(f"Failed to fetch game log for player ID {player_id} ({player_name}) after {retries} attempts.")
    return None

def process_player_data(player, season):
    player_name = player["full_name"]
    logging.info(f"Processing player: {player_name} (ID: {player['id']})")
    print(f"Processing player: {player_name} (ID: {player['id']})")
    try:
        gamelog = get_player_gamelog(player_name, player["id"], season)
        if gamelog is not None:
            gamelog["PLAYER_NAME"] = player_name
            gamelog["HOME_AWAY"] = gamelog["MATCHUP"].apply(lambda x: "Home" if "vs." in x else "Away")

            gamelog["TEAM_NAME"] = gamelog["MATCHUP"].apply(lambda x: x.split(" ")[0])
            
            # Add thresholds
            for col, (stat, threshold) in THRESHOLD_COLUMNS.items():
                if stat in gamelog.columns:
                    gamelog[col] = (gamelog[stat] >= threshold).astype(int)
                else:
                    logging.warning(f"Missing column {stat} for player {player_name}. Threshold not applied.")
            # Add rolling averages
            for col, (stat, window) in DYNAMIC_THRESHOLDS.items():
                if stat in gamelog.columns:
                    gamelog[col] = gamelog[stat].rolling(window=window).mean().fillna(0)
                else:
                    logging.warning(f"Missing column {stat} for player {player_name}. Rolling average not calculated.")

            # Save intermediate player data
            #player_file = os.path.join(PLAYER_DIR, f"{player_name.replace(' ', '_')}.csv")
            # gamelog.to_csv(player_file, index=False)

            return gamelog
        else:
            logging.warning(f"No data available for {player_name}.")
            return pd.DataFrame()  # Return empty DataFrame for failed players
    except Exception as e:
        logging.error(f"Error processing data for {player_name}: {e}")
        return pd.DataFrame()

def generate_dataset(output_file=DATASET_FILE):
    start_time = time.time()
    active_players = get_all_active_players()
    season = get_current_season()
    if not active_players:
        logging.error("No active players found. Dataset generation aborted.")
        return

    all_data = []
    with ThreadPoolExecutor(max_workers=10) as executor:  # Parallelize API calls
        future_to_player = {executor.submit(process_player_data, player, season): player for player in active_players}
        for future in as_completed(future_to_player):
            try:
                data = future.result()
                if not data.empty:
                    all_data.append(data)
            except Exception as e:
                logging.error(f"Error processing player: {e}")

    if all_data:
        dataset = pd.concat(all_data, ignore_index=True)
        dataset.to_csv(output_file, index=False)
        logging.info(f"Dataset saved to {output_file}. Total players processed: {len(all_data)}")
    else:
        logging.error("No data available to save.")

    elapsed_time = time.time() - start_time
    logging.info(f"Dataset generation completed in {elapsed_time:.2f} seconds.")

if __name__ == "__main__":
    generate_dataset()
