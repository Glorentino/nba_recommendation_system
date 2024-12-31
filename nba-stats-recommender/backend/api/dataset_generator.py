import os
import time
import pandas as pd
from datetime import datetime
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
import logging
logging.basicConfig(filename="dataset_generator.log", level=logging.INFO, format="%(asctime)s - %(message)s")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_FILE = os.path.join(BASE_DIR, "player_data.csv")

FEATURES = ["GAME_DATE", "MATCHUP", "PTS", "REB", "AST", "BLK", "PLAYER_NAME"]
THRESHOLD_COLUMNS = {
    "POINTS_THRESHOLD": ("PTS", 10),
    "REBOUNDS_THRESHOLD": ("REB", 5),
    "BLOCKS_THRESHOLD": ("BLK", 1),
    "ASSISTS_THRESHOLD": ("AST", 3),
}


def get_current_season():
    """
    Returns the current NBA season as a string (e.g., '2023-24').
    """
    current_year = datetime.now().year
    if datetime.now().month > 9:  # After September, new season starts
        return f"{current_year}-{str(current_year + 1)[2:]}"
    else:
        return f"{current_year - 1}-{str(current_year)[2:]}"

def get_all_active_players():
    """
    Returns a list of all active NBA players.
    """
    active_players = players.get_active_players()
    if not active_players:
        logging.warning("No active players found. Check the NBA API.")
    return active_players

def get_player_gamelog(player_id, season, retries=3, delay=5):
    """
    Fetches the game log for a given player ID for the specified season.
    """
    for attempt in range(retries):
        try:
            gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season, timeout=60).get_data_frames()[0]
            return gamelog
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed for player ID {player_id}: {e}")
            time.sleep(delay)
    logging.error(f"Failed to fetch game log for player ID {player_id} after {retries} attempts.")
    return None

def generate_dataset(output_file=DATASET_FILE):
    """
    Generates a dataset of player game logs with threshold columns.
    """
    start_time = time.time()
    active_players = get_all_active_players()
    season = get_current_season()
    all_data = []
    
    if not active_players:
        logging.error("No active players found. Dataset generation aborted.")
        return
    
    for idx, player in enumerate(active_players, start=1):
        player_name = player["full_name"]
        print(f"Processing data for {player_name}...")
        logging.info(f"Processing player {idx}/{len(active_players)}: {player_name}...")

        try:
            gamelog = get_player_gamelog(player["id"], season)
            if gamelog is not None:
                # Select relevant columns and add thresholds
                gamelog = gamelog[["GAME_DATE", "MATCHUP", "PTS", "REB", "AST", "BLK"]].copy()
                gamelog["PLAYER_NAME"] = player_name

                # Add threshold columns for classification
                for col, (stat, threshold) in THRESHOLD_COLUMNS.items():
                    gamelog[col] = (gamelog[stat] >= threshold).astype(int)

                # Ensure consistent column order
                gamelog = gamelog.reindex(columns=FEATURES + list(THRESHOLD_COLUMNS.keys()))

                all_data.append(gamelog)
            else:
                logging.warning(f"No data available for {player_name}.")
        except Exception as e:
            print(f"No data available for {player_name}.")
            logging.error(f"Error processing data for {player_name}: {e}")

    # Combine all player data into a single DataFrame
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