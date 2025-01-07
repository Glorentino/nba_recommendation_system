import React from 'react';
import PredictionForm from './components/PredictionForm';

function App() {

  return (
    <div className="App">
      <header className="App-header">
        <h1><img  src={"/logo.png"} alt="Logo"  style={{ width: "50px", height: "50px" }}/>
        NBA Player Performance Predictor</h1>
      </header>
      <PredictionForm />
    </div>
  );
}

export default App;
