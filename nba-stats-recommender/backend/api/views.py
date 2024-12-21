from django.shortcuts import render 
from rest_framework.decorators import api_view
from rest_framework.response import Response
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
from .models import Player


@api_view(["GET"])
def get_player_stats(request, player_name):
    if not player_name:
        return Response({"error": "Player name is required"}, status=400)
    
    player_info = players.find_players_by_full_name(player_name)
    if not player_info:
        return Response({"error":"Player not found"}, status=404)
    
    player_id = player_info[0]["id"]
    gamelog = playergamelog.PlayerGameLog(player_id=player_id, season="2022-23")
    games = gamelog.get_data_frames()[0]
    
    stats = games[["GAME_DATE", "PTS", "REB", "AST"]].to_dict(orient="records")
    return Response({"player": player_name, "stats": stats}) 