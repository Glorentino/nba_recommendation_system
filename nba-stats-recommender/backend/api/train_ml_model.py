import os
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "utils/player_data.csv")
MODEL_FILES = {
    "points": os.path.join(BASE_DIR, "ml_model_points.pkl"),
    "rebounds": os.path.join(BASE_DIR, "ml_model_rebounds.pkl"),
    "blocks": os.path.join(BASE_DIR, "ml_model_blocks.pkl"),
    "assists": os.path.join(BASE_DIR, "ml_model_assists.pkl"),
}

REQUIRED_COLUMNS = ["PTS", "REB", "AST", "BLK", 
                    "POINTS_THRESHOLD", "REBOUNDS_THRESHOLD", 
                    "BLOCKS_THRESHOLD", "ASSISTS_THRESHOLD"]


def validate_columns(data, required_columns):
    """
    Validate if required columns exist in the dataset.
    """
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        print(f"Error: Missing columns in dataset: {', '.join(missing_columns)}")
        return False
    return True

def train_ml_model():
    # Load dataset
    try:
        data = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        print(f"Error: Data file {DATA_FILE} not found.")
        return
    except Exception as e:
        print(f"Error loading data file: {e}")
        return

    # Validate required columns
    if not validate_columns(data, REQUIRED_COLUMNS):
        return

    # Train models for each stat
    for stat, model_file in MODEL_FILES.items():
        stat_col = f"{stat.upper()}_THRESHOLD"  # e.g., POINTS_THRESHOLD
        if stat_col not in data.columns:
            print(f"Warning: Missing label column {stat_col}. Skipping {stat} model.")
            continue

        try:
            labels = data[stat_col]
            # Dynamically determine feature columns
            feature_columns = ["PTS", "REB", "AST", "BLK"]  # Add or modify features as needed
            features = data[feature_columns]

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)
            print("Training data size:", len(X_train))
            print("Test data size:", len(X_test))
            # Train model
            print(f"Training model for {stat}...")
            model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
            model.fit(X_train, y_train)

            # Save model
            joblib.dump(model, model_file)
            print(f"Model for {stat} saved to {model_file}.")

            # Evaluate model
            accuracy = accuracy_score(y_test, model.predict(X_test))
            print(f"Accuracy for {stat} model: {accuracy * 100:.2f}%")
        except Exception as e:
            print(f"Error training model for {stat}: {e}")

if __name__ == "__main__":
    train_ml_model()
