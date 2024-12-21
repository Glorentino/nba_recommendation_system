import React, { useState, useEffect } from "react";


const PlayerStats = ({ playerName }) => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!playerName) return;
    
        const fetchPlayerStats = async () => {
          setLoading(true);
          setError("");
          try {
            const encodedName = encodeURIComponent(playerName); 
            const response = await fetch(`http://127.0.0.1:8000/api/player-stats/${encodedName}/`);
            if (!response.ok) {
              throw new Error('Player stats not found');
            }
            const data = await response.json();
            setStats(data);
          } catch (err) {
            setError(err.message);
            setStats(null);
          } finally {
            setLoading(false);
          }
        };
    
        fetchPlayerStats();
      }, [playerName]);

    return (
        <div className="player-stats">
            {loading && <p>Loading stats...</p>}
            {error && <p className="error">{error}</p>}
            {stats && (
                <div>
                    <h2>Player Stats: {stats.player}</h2>
                    <ul>
                        {stats.stats.map((game, index) => (
                            <li key={index}>
                                <strong>Game Date:</strong> {game.GAME_DATE} | <strong>PTS:</strong> {game.PTS} | <strong>REB:</strong> {game.REB} | <strong>AST:</strong> {game.AST}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    )

}
export default PlayerStats;