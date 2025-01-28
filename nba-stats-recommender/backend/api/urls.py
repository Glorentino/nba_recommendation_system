from django.urls import path
from . import views

urlpatterns = [
    path('generate-and-train/', views.generate_and_train, name='generate_and_train'),
    path('predict-points/<str:player_name>/<str:team_name>/<int:threshold>/', views.predict_points, name='predict_points'),
    path('predict-rebounds/<str:player_name>/<str:team_name>/<int:threshold>/', views.predict_rebounds, name='predict_rebounds'),
    path('predict-blocks/<str:player_name>/<str:team_name>/<int:threshold>/', views.predict_blocks, name='predict_blocks'),
    path('predict-assists/<str:player_name>/<str:team_name>/<int:threshold>/', views.predict_assists, name='predict_assists'),
    path('predict-steals/<str:player_name>/<str:team_name>/<int:threshold>/', views.predict_steals, name='predict_steals'),
    path('predict-fg3m/<str:player_name>/<str:team_name>/<int:threshold>/', views.predict_3pointers, name='predict_3pointers'),
    path("player-names/", views.get_player_names, name="player_names"),
    path("team-names/", views.get_team_names, name="team_names"),
    path("player-trends/<str:player_name>/", views.player_trends, name="player_trends"),
    path("team-comparison/", views.team_comparisons, name="team_comparisons"),
    path("player-averages-vs-opponents/<str:player_name>/", views.player_averages_vs_opponents, name="player_averages_vs_opponents"),
    path("player-team/<str:player_name>/", views.get_player_team, name="player_team"),
    path('recommend-players/<str:player_name>/<str:opponent_team>/<str:stat_type>/<int:threshold>/', views.recommend_similar_players, name='recommend_similar_players'),
]
