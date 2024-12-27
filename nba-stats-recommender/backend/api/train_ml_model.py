import os
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "player_data.csv")
MODEL_FILES = {
    "points": os.path.join(BASE_DIR, "ml_model_points.pkl"),
    "rebounds": os.path.join(BASE_DIR, "ml_model_rebounds.pkl"),
    "blocks": os.path.join(BASE_DIR, "ml_model_blocks.pkl"),
    "assists": os.path.join(BASE_DIR, "ml_model_assists.pkl"),
}

REQUIRED_COLUMNS = ["PTS", "REB", "AST", "BLK", "POINTS_THRESHOLD"]

def train_ml_model():
    data = pd.read_csv(DATA_FILE)

    # Validate required columns
    for col in REQUIRED_COLUMNS:
        if col not in data.columns:
            print(f"Warning: Missing column {col}. Skipping...")
            continue

    for stat, model_file in MODEL_FILES.items():
        stat_col = f"{stat.upper()}_THRESHOLD"  # e.g., POINTS_THRESHOLD
        if stat_col not in data.columns:
            print(f"Warning: Missing label column {stat_col}. Skipping {stat} model.")
            continue

        labels = data[stat_col]
        features = data[["PTS", "REB", "AST", "BLK"]]  # Adjust as necessary

        # Train the model
        X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)
        model = RandomForestClassifier()
        model.fit(X_train, y_train)
        joblib.dump(model, model_file)

        accuracy = accuracy_score(y_test, model.predict(X_test))
        print(f"Model for {stat} saved to {model_file}. Accuracy: {accuracy * 100:.2f}%")

if __name__ == "__main__":
    train_ml_model()
