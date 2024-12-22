from django.shortcuts import render 
from rest_framework.decorators import api_view
from rest_framework.response import Response
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
from .models import Player
from .utils.similarity import calculate_similarity
from .utils.filters import filter_by_date_range, filter_by_threshold
import pandas as pd



@api_view(["GET"])
def get_player_stats(request, player_name):
    """
    Get stats for a specific player with optional filters.
    """
    if not player_name:
        return Response({"error": "Player name is required"}, status=400)
    
    player_info = players.find_players_by_full_name(player_name)
    if not player_info:
        return Response({"error":"Player not found"}, status=404)
    
    player_id = player_info[0]["id"]
    
    try:
        gamelog = playergamelog.PlayerGameLog(player_id=player_id, season="2022-23").get_data_frames()[0]
    except Exception as e:
        return Response({"error": f"Failed to fetch stats: {str(e)}"}, status=500)
    
    # Apply Extra Filters
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    points_threshold = request.GET.get("points", None)
    
    if start_date or end_date:
        gamelog = filter_by_date_range(gamelog, start_date, end_date)
    if points_threshold:
        gamelog = filter_by_threshold(gamelog, "PTS", int(points_threshold))
    
    stats = gamelog[["GAME_DATE", "PTS", "REB", "AST"]].to_dict(orient="records")
    print(f"Game log before filtering: {gamelog}")
    print(f"Game log after filtering: {gamelog}")
    return Response({"player": player_name, "stats": stats}) 

@api_view(["GET"])
def recommend_players(request, player_name):
    if not player_name:
        return Response({"error": "Player name is required"}, status=400)

    # Find the player by name
    player_info = players.find_players_by_full_name(player_name)
    if not player_info:
        return Response({"error": "Player not found"}, status=404)

    target_player_id = player_info[0]["id"]

    try:
        # Fetch the game log for the target player
        gamelog = playergamelog.PlayerGameLog(player_id=target_player_id, season="2022-23").get_data_frames()[0]

        # Debugging: Print the fetched game log and its columns
        print(f"Fetched game log for player {player_name}:")
        print(gamelog)
        print(f"Columns: {gamelog.columns}")  # Debugging

        # Handle empty or invalid game log
        if gamelog.empty:
            raise ValueError(f"Game log is empty for player ID: {target_player_id}")

        # Calculate mean stats
        target_stats = {
            "PTS": gamelog["PTS"].mean(),
            "REB": gamelog["REB"].mean(),
            "AST": gamelog["AST"].mean(),
        }
        print(f"Target stats: {target_stats}")  # Debugging

    except KeyError as ke:
        print(f"KeyError - Missing column in game log: {ke}")
        return Response({"error": f"Game log missing required columns: {ke}"}, status=500)
    except Exception as e:
        # Enhanced Debugging
        import traceback
        traceback.print_exc()
        print(f"Unexpected error while processing target player stats: {e}")
        return Response({"error": f"Failed to fetch target player stats: {e}"}, status=500)

    # Find active players for recommendations
    all_players = players.get_active_players()
    recommendations = []
    for other_player in all_players:
        try:
            # Fetch game log for other players
            other_player_id = other_player["id"]
            other_gamelog = playergamelog.PlayerGameLog(player_id=other_player_id, season="2022-23").get_data_frames()[0]

            # Debugging: Print the fetched game log and its columns
            print(f"Fetched game log for player {other_player['full_name']}:")
            print(other_gamelog)
            print(f"Columns: {other_gamelog.columns}")  # Debugging

            # Skip if game log is empty
            if other_gamelog.empty:
                print(f"Game log is empty for player {other_player['full_name']}")  # Debugging
                continue

            # Calculate mean stats for the other player
            other_stats = {
                "PTS": other_gamelog["PTS"].mean(),
                "REB": other_gamelog["REB"].mean(),
                "AST": other_gamelog["AST"].mean(),
            }
            print(f"Other stats for {other_player['full_name']}: {other_stats}")  # Debugging

            # Calculate similarity and add to recommendations
            similarity_score = calculate_similarity(target_stats, other_stats)
            recommendations.append((other_player["full_name"], similarity_score))
        except KeyError as ke:
            print(f"KeyError - Missing column in game log for player {other_player['full_name']}: {ke}")
        except Exception as e:
            print(f"Unexpected error for player {other_player['full_name']}: {e}")
            continue

    # Sort and return top recommendations
    recommendations = sorted(recommendations, key=lambda x: x[1])[:5]
    print(f"Final recommendations: {recommendations}")  # Debugging
    return Response({"player": player_name, "recommendations": recommendations})