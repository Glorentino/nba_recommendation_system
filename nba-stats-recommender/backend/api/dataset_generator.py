import os
import time
import pandas as pd
from datetime import datetime
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def get_player_gamelog(player_name, season="2023-24"):
    """
    Fetches the game log for a given player for the specified season.
    """
    player_info = players.find_players_by_full_name(player_name)
    if not player_info:
        raise ValueError(f"Player {player_name} not found.")

    player_id = player_info[0]["id"]
    gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season).get_data_frames()[0]
    return gamelog

def generate_dataset(output_file="player_data.csv"):
    all_data = []

    for player_name in ["LeBron James", "Stephen Curry", "Kevin Durant"]:
        try:
            gamelog = get_player_gamelog(player_name)  # Fetch game logs
            gamelog = gamelog[["GAME_DATE", "MATCHUP", "PTS", "REB", "AST", "BLK"]]

            # Add threshold columns for classification
            gamelog["POINTS_THRESHOLD"] = (gamelog["PTS"] >= 20).astype(int)
            gamelog["REBOUNDS_THRESHOLD"] = (gamelog["REB"] >= 10).astype(int)
            gamelog["BLOCKS_THRESHOLD"] = (gamelog["BLK"] >= 2).astype(int)
            gamelog["ASSISTS_THRESHOLD"] = (gamelog["AST"] >= 5).astype(int)

            all_data.append(gamelog)
        except Exception as e:
            print(f"Error processing data for {player_name}: {e}")

    # Combine all player data into a single DataFrame
    if all_data:
        dataset = pd.concat(all_data, ignore_index=True)
        dataset.to_csv(output_file, index=False)
        print(f"Dataset saved to {output_file}")
    else:
        print("No data available to save.")
if __name__ == "__main__":
    generate_dataset()