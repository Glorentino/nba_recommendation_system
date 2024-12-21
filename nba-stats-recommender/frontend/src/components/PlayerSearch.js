import React, { useState } from "react";

const PlayerSearch = ({ onSearch }) => {
    const [query, setQuery] = useState("");
    
    const handleInputChange = (event) => {
        setQuery(event.target.value);
    };

    const handleSearch = (event) => {
        event.preventDefault();
        if (onSearch && query) {
            onSearch(query);
        }  
    };

    return (
        <div className="player-search">
        <form onSubmit={handleSearch}>
          <input
            type="text"
            placeholder="Search for a player"
            value={query}
            onChange={handleInputChange}
          />
          <button type="submit">Search</button>
        </form>
      </div>
    );
};

export default PlayerSearch;