import os
import time
import pandas as pd
from datetime import datetime
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_FILE = os.path.join(BASE_DIR, "player_data.csv")

FEATURES = ["GAME_DATE", "MATCHUP", "PTS", "REB", "AST", "BLK", "PLAYER_NAME"]
THRESHOLD_COLUMNS = {
    "POINTS_THRESHOLD": ("PTS", 20),
    "REBOUNDS_THRESHOLD": ("REB", 10),
    "BLOCKS_THRESHOLD": ("BLK", 2),
    "ASSISTS_THRESHOLD": ("AST", 5),
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
    return players.get_active_players()

def get_player_gamelog(player_id, season, retries=3, delay=5):
    """
    Fetches the game log for a given player ID for the specified season.
    """
    for attempt in range(retries):
        try:
            gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season, timeout=60).get_data_frames()[0]
            return gamelog
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for player ID {player_id}: {e}")
            time.sleep(delay)
    print(f"Failed to fetch game log for player ID {player_id} after {retries} attempts.")
    return None

def generate_dataset(output_file=DATASET_FILE):
    """
    Generates a dataset of player game logs with threshold columns.
    """
    start_time = time.time()
    active_players = get_all_active_players()
    season = get_current_season()
    all_data = []

    for player in active_players:
        player_name = player["full_name"]
        print(f"Processing data for {player_name}...")

        try:
            gamelog = get_player_gamelog(player["id"], season)
            if gamelog is not None:
                # Select relevant columns and add thresholds
                gamelog = gamelog[["GAME_DATE", "MATCHUP", "PTS", "REB", "AST", "BLK"]]
                gamelog["PLAYER_NAME"] = player_name
                
                # Add threshold columns for classification
                for col, (stat, threshold) in THRESHOLD_COLUMNS.items():
                    gamelog[col] = (gamelog[stat] >= threshold).astype(int)
                
                # Ensure consistent column order
                gamelog = gamelog.reindex(columns=FEATURES + list(THRESHOLD_COLUMNS.keys()))
                
                all_data.append(gamelog)
            else:
                print(f"No data available for {player_name}.")
        except Exception as e:
            print(f"Error processing data for {player_name}: {e}")
    time.sleep(1)
    # Combine all player data into a single DataFrame
    if all_data:
        dataset = pd.concat(all_data, ignore_index=True)
        dataset.to_csv(output_file, index=False)
        print(f"Dataset saved to {output_file}")
    else:
        print("No data available to save.")
if __name__ == "__main__":
    generate_dataset()