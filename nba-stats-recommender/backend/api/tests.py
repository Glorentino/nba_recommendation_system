from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from nba_api.stats.endpoints import playergamelog
import pandas as pd


class PlayerStatsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.valid_player = "LeBron James"
        self.invalid_player = "Unknown Player"

    @patch("nba_api.stats.endpoints.playergamelog.PlayerGameLog.get_data_frames")
    def test_get_player_stats_valid(self, mock_get_data_frames):
        """
        Test fetching stats for a valid player with mocked API response.
        """
        mock_get_data_frames.return_value = [
            pd.DataFrame([
                {"GAME_DATE": "2022-12-01", "PTS": 30, "REB": 10, "AST": 8},
                {"GAME_DATE": "2022-12-03", "PTS": 25, "REB": 9, "AST": 7},
            ])
        ]

        response = self.client.get(reverse("get_player-stats", args=[self.valid_player]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["player"], self.valid_player)
        self.assertEqual(len(response.data["stats"]), 2)
        self.assertEqual(response.data["stats"][0]["PTS"], 30)

    def test_get_player_stats_invalid(self):
        """
        Test fetching stats for an invalid player.
        """
        response = self.client.get(reverse("get_player-stats", args=[self.invalid_player]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)

    @patch("nba_api.stats.endpoints.playergamelog.PlayerGameLog.get_data_frames")
    def test_get_player_stats_with_filters(self, mock_get_data_frames):
        """
        Test fetching stats for a valid player with date and points filters.
        """
        mock_get_data_frames.return_value = [
            pd.DataFrame([
                {"GAME_DATE": "2022-12-01", "PTS": 30, "REB": 10, "AST": 8},  # Should match filters
                {"GAME_DATE": "2022-11-25", "PTS": 15, "REB": 5, "AST": 2},  # Should be excluded
            ])
        ]

        response = self.client.get(reverse("get_player-stats", args=[self.valid_player]), {
            "start_date": "2022-12-01",
            "end_date": "2022-12-31",
            "points": 20
        })
        print("Response data:", response.data)  # Debugging step
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["stats"]), 1)  # Only 1 entry should match
        self.assertEqual(response.data["stats"][0]["PTS"], 30)


class PredictPointsTests(TestCase):
    @patch("nba_api.stats.endpoints.playergamelog.PlayerGameLog.get_data_frames")
    def test_predict_points(self, mock_get_data_frames):
        # Mock game logs
        mock_get_data_frames.return_value = [
            pd.DataFrame({
                "MATCHUP": ["LAL vs GSW", "LAL vs GSW"],
                "PTS": [35, 28]
            })
        ]

        response = self.client.get("/api/predict-points/LeBron James/Golden State Warriors/30/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("likelihood", response.json())