import React, { useState } from 'react';
import PlayerSearch from './components/PlayerSearch';
import PlayerStats from './components/PlayerStats';
import PredictionForm from './components/PredictionForm';

function App() {
  const [playerName, setPlayerName] = useState("");

  const handleSearch = (query) => {
    setPlayerName(query);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>NBA Stats Recommendation System</h1>
      </header>
      <PredictionForm />
    </div>
  );
}

export default App;
