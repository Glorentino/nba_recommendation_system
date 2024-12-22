from django.urls import path
from .views import get_player_stats, recommend_players

urlpatterns = [
    path("player-stats/<str:player_name>/", get_player_stats, name="get_player-stats"),
    path("recommend/<str:player_name>/", recommend_players, name="recommend-players"),
]
