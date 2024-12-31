import React, { useState } from "react";

const PredictionForm = () => {
    const [playerName, setPlayerName] = useState("");
    const [teamName, setTeamName] = useState("");
    const [threshold, setThreshold] = useState("");
    const [statType, setStatType] = useState("points")
    const [prediction, setPrediction] = useState(null);
    const [errorMessage, setErrorMessage] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setErrorMessage();
        setPrediction(null);
        setLoading(true);


        const API_BASE_URL = "http://127.0.0.1:8000/api";
        const apiEndpointMap = {
          points: "predict-points",
          rebounds: "predict-rebounds",
          blocks: "predict-blocks",
          assists: "predict-assists",
      };

       const endpoint = apiEndpointMap[statType];
        try {
            const response = await fetch(
                `${API_BASE_URL}/${endpoint}/${encodeURIComponent(playerName)}/${encodeURIComponent(teamName)}/${threshold}/`
            );
            const data = await response.json();
            if (response.ok) {
                setPrediction(data);
            } else {
                setErrorMessage(data.message || "An error occurred. Please try again.");
            }
        } catch (error) {
            setErrorMessage("Failed to fetch prediction. Please check your connection.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
                        <h2>Player Performance Prediction</h2>
            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    placeholder="Player Name (e.g., LeBron James)"
                    value={playerName}
                    onChange={(e) => setPlayerName(e.target.value)}
                    required
                />
                <input
                    type="text"
                    placeholder="Team Name (e.g., Golden State Warriors)"
                    value={teamName}
                    onChange={(e) => setTeamName(e.target.value)}
                    required
                />
                <input
                    type="number"
                    placeholder="Threshold (e.g., 30)"
                    value={threshold}
                    onChange={(e) => setThreshold(e.target.value)}
                    min="1" // Validation to ensure positive numbers
                    required
                />
                <select value={statType} onChange={(e) => setStatType(e.target.value)}>
                    <option value="points">Points</option>
                    <option value="rebounds">Rebounds</option>
                    <option value="blocks">Blocks</option>
                    <option value="assists">Assists</option>
                </select>
                <button type="submit" disabled={loading}> {/* Disable button while loading */}
                    {loading ? "Predicting..." : "Predict"}
                </button>
            </form>

            {/* Display Prediction */}
            {prediction && (
                <div>
                    <h2>Prediction Results</h2>
                    <p>
                        {prediction.player} has a {prediction.likelihood} chance of exceeding{" "}
                        {threshold} {statType} against {prediction.team}.
                    </p>

                    <h3>Game Logs</h3>
                    <table border="1" style={{ marginTop: "20px" }}>
                        <thead>
                            <tr>
                                <th>Game Date</th>
                                <th>Matchup</th>
                                <th>Points</th>
                                <th>Rebounds</th>
                                <th>Assists</th>
                                <th>Blocks</th>
                            </tr>
                        </thead>
                        <tbody>
                            {prediction.games.map((game, index) => (
                                <tr key={index}>
                                    <td>{game.GAME_DATE}</td>
                                    <td>{game.MATCHUP}</td>
                                    <td>{game.PTS}</td>
                                    <td>{game.REB}</td>
                                    <td>{game.AST}</td>
                                    <td>{game.BLK}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Display Error Message */}
            {errorMessage && (
                <div style={{ color: "red", marginTop: "20px" }}>
                    <h2>Error</h2>
                    <p>{errorMessage}</p>
                </div>
            )}
        </div>
      );
}
export default PredictionForm;