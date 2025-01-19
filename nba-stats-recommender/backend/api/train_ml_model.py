import os
import pandas as pd
import joblib
import logging
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more verbose output
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "utils/player_data.csv")
MODEL_FILES = {
    "points": os.path.join(BASE_DIR, "ml_model_points.pkl"),
    "rebounds": os.path.join(BASE_DIR, "ml_model_rebounds.pkl"),
    "blocks": os.path.join(BASE_DIR, "ml_model_blocks.pkl"),
    "assists": os.path.join(BASE_DIR, "ml_model_assists.pkl"),
    "steals": os.path.join(BASE_DIR, "ml_model_steals.pkl"),
}

REQUIRED_COLUMNS = ["PTS", "REB", "AST", "BLK", "STL",
                    "POINTS_THRESHOLD", "REBOUNDS_THRESHOLD", "BLOCKS_THRESHOLD", "ASSISTS_THRESHOLD", "STEALS_THRESHOLD"]


def validate_columns(data, required_columns):
    """
    Validate if required columns exist in the dataset.
    """
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        logger.error("Missing columns in dataset: %s", ', '.join(missing_columns))
        return False
    return True

def train_ml_model():
    # Load dataset
    try:
        data = pd.read_csv(DATA_FILE)
        logger.info("Loaded data file: %s", DATA_FILE)
    except FileNotFoundError:
        logger.error("Data file %s not found.", DATA_FILE)
        return
    except Exception as e:
        logger.error("Error loading data file: %s", e)
        return

    # Validate required columns
    if not validate_columns(data, REQUIRED_COLUMNS):
        return

    param_distributions = {
        'n_estimators': [100, 200, 300, 500],
        'max_depth': [10, 20, 30, None],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
        'max_features': ['auto', 'sqrt', 'log2'],
        'bootstrap': [True, False]
    }


    # Train models for each stat
    for stat, model_file in MODEL_FILES.items():
        stat_col = f"{stat.upper()}_THRESHOLD"  # e.g., POINTS_THRESHOLD
        if stat_col not in data.columns:
            print(f"Warning: Missing label column {stat_col}. Skipping {stat} model.")
            continue

        try:
            labels = data[stat_col]
            # Dynamically determine feature columns
            feature_columns = ["PTS", "REB", "AST", "BLK", "STL"]  # Add or modify features as needed
            features = data[feature_columns]

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)
            logger.info(
                "Training %s model. Training data size: %d, Test data size: %d", 
                stat, len(X_train), len(X_test)
            )
            
            # Train model
            rf = RandomForestRegressor(random_state=42)
            grid_search = GridSearchCV(
                estimator=rf, 
                param_grid=param_distributions,  # Note the change to param_grid
                cv=3,
                verbose=2,
                n_jobs=-1
            )
            grid_search.fit(X_train, y_train)

            best_model = grid_search.best_estimator_
            logger.info("Best parameters for %s model: %s", stat, grid_search.best_params_)
            
            # Save model
            joblib.dump(best_model, model_file)
            logger.info("Model for %s saved to %s.", stat, model_file)

            # Evaluate model
            predictions = best_model.predict(X_test)
            mae = mean_absolute_error(y_test, predictions)
            mse = mean_squared_error(y_test, predictions)
            r2 = r2_score(y_test, predictions)

            logger.info(
                "Metrics for %s model: MAE=%.2f, MSE=%.2f, R²=%.2f",
                stat, mae, mse, r2
            )
        except Exception as e:
            logger.error("Error training model for %s: %s", stat, e)

if __name__ == "__main__":
    train_ml_model()
