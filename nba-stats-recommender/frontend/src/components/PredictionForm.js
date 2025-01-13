import React, { useState, useEffect } from "react";
import Select from "react-select";


const PredictionForm = () => {
    const [playerName, setPlayerName] = useState("");
    const [teamName, setTeamName] = useState("");
    const [threshold, setThreshold] = useState("");
    const [statType, setStatType] = useState("points");
    const [players, setPlayers] = useState([]);
    const [teams, setTeams] = useState([]);
    const [playerTeam, setPlayerTeam] = useState("");
    const [prediction, setPrediction] = useState(null);
    const [errorMessage, setErrorMessage] = useState("");
    const [loading, setLoading] = useState(false);

    const API_BASE_URL = "https://dfpuypxamy.us-east-1.awsapprunner.com/api";
    //const API_BASE_URL = "http://127.0.0.1:8000/api";

    useEffect(() => {
        // Fetch players
        const fetchPlayers = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/player-names/`);
                const data = await response.json();
                const sortedPlayers = data.sort((a, b) => a.localeCompare(b));
                setPlayers(sortedPlayers.map((player) => ({ label: player, value: player })));
            } catch (error) {
                console.error("Error fetching player names:", error);
            }
        };

        // Fetch teams
        const fetchTeams = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/team-names/`);
                const data = await response.json();
                const sortedTeams = data.sort((a, b) => a.localeCompare(b));
                setTeams(sortedTeams.map((team) => ({ label: team, value: team })));
            } catch (error) {
                console.error("Error fetching team names:", error);
            }
        };

        fetchPlayers();
        fetchTeams();
    }, []);

    const handlePlayerChange = async (selectedOption) => {
        setPlayerName(selectedOption.value);
        setPlayerTeam("");
        setTeamName("");
        try{
            const response = await fetch(`${API_BASE_URL}/player-team/${encodeURIComponent(selectedOption.value)}/`);
            const data = await response.json();
            setPlayerTeam(data.team);
        } catch (error) {
            console.error("Error fetching player's team", error);
        }
    };

    const filteredTeams = teams.filter((team) => team.value !== playerTeam);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setErrorMessage("");
        setPrediction(null);
        setLoading(true);

        const apiEndpointMap = {
            points: "predict-points",
            rebounds: "predict-rebounds",
            blocks: "predict-blocks",
            assists: "predict-assists",
            steals: "predict-steals",
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
                setErrorMessage(data.error || "An error occurred. Please try again.");
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
            <form onSubmit={handleSubmit} >
                {/* Player Dropdown with Search */}
                <p>Select A Player:</p>
                <Select
                    options={players}
                    onChange={handlePlayerChange}
                    placeholder="Select Player"
                    isSearchable
                    required
                    styles={{
                        control: (base) => ({
                            ...base,
                            maxWidth: "300px", 
                            minWidth: "150px",
                        }),
                        menu: (base) => ({
                            ...base,
                            maxWidth: "300px", 
                        }),
                    }}
                />

                {/* Team Dropdown with Search */}
                <p>Against Which Team:</p>
                <Select
                    options={filteredTeams}
                    onChange={(selectedOption) => setTeamName(selectedOption.value)}
                    placeholder="Select Team"
                    isSearchable
                    required
                    isDisabled={!playerTeam}
                                        styles={{
                        control: (base) => ({
                            ...base,
                            maxWidth: "300px", 
                            minWidth: "150px",
                        }),
                        menu: (base) => ({
                            ...base,
                            maxWidth: "300px", 
                        }),
                    }}
                />
                <p>Select The Stat:</p>
                <input
                    type="number"
                    placeholder="Threshold (e.g., 30)"
                    value={threshold}
                    onChange={(e) => setThreshold(e.target.value)}
                    min="1"
                    required
                />
                <select value={statType} onChange={(e) => setStatType(e.target.value)}>
                    <option value="points">Points</option>
                    <option value="rebounds">Rebounds</option>
                    <option value="blocks">Blocks</option>
                    <option value="assists">Assists</option>
                    <option value="steals">Steals</option>
                </select>
                <button type="submit" disabled={loading}>
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

                    <h3>Game Logs (Against {teamName})</h3>
                    <table border="1" style={{ marginTop: "20px" }}>
                        <thead>
                            <tr>
                                <th>Game Date</th>
                                <th>Matchup</th>
                                <th>Points</th>
                                <th>Rebounds</th>
                                <th>Assists</th>
                                <th>Blocks</th>
                                <th>Steals</th>
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
                                    <td>{game.STL}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    <h3>Last 5 Recent Games</h3>
                    <table border="1" style={{ marginTop: "20px" }}>
                        <thead>
                            <tr>
                                <th>Game Date</th>
                                <th>Matchup</th>
                                <th>Points</th>
                                <th>Rebounds</th>
                                <th>Assists</th>
                                <th>Blocks</th>
                                <th>Steals</th>
                            </tr>
                        </thead>
                        <tbody>
                            {prediction.recent_games.map((game, index) => (
                                <tr key={index}>
                                    <td>{game.GAME_DATE}</td>
                                    <td>{game.MATCHUP}</td>
                                    <td>{game.PTS}</td>
                                    <td>{game.REB}</td>
                                    <td>{game.AST}</td>
                                    <td>{game.BLK}</td>
                                    <td>{game.STL}</td>
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
};

export default PredictionForm;