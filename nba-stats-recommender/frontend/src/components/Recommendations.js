import React from "react";

const Recommendations = ({ recommendations }) => {
    return (
        <div className="recommendations">
            <h2>Recommended Players</h2>
            {recommendations.length === 0 ? (
                <p>No recommendations available</p>
            ) : (
                <ul>
                    {recommendations.map((rec, index) => (
                        <li key={index}>
                            {rec[0]} - Similarity Score: {rec[1].toFixed(2)}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default Recommendations;