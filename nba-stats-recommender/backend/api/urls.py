from django.urls import path
from .views import get_player_stats

urlpatterns = [
    path("player-stats/<str:player_name>/", get_player_stats, name="get_player-stats"),
]
