import React, { useState } from "react";

const Filters = ({ onlyApplyFilers }) => {
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [points, setPoints] = useState("");

    const handleSubmit = (e) => {
        e.preventDefault();
        onlyApplyFilers({ startDate, endDate, points})
    };

    return (
        <form onSubmit={handleSubmit}>
            <h3>Filter Stats</h3>
            <div>
                <label>Start Date:</label>
                <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                />
            </div>
            <div>
                <label>End Date:</label>
                <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                />
            </div>
            <div>
                <label>Points Threshold:</label>
                <input
                    type="number"
                    value={points}
                    onChange={(e) => setPoints(e.target.value)}
                />
            </div>
            <button type="submit">Apply Filters</button>
        </form>
    );
};

export default Filters;