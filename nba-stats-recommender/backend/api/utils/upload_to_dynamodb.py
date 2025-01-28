import pandas as pd
import logging
from decimal import Decimal
from dynamodb_helper import DDBQuery

# Set up logging
logging.basicConfig(
    filename="sanitize_and_upload.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def safe_convert_to_decimal(value):
    """
    Safely convert values to Decimal for DynamoDB compatibility.
    """
    try:
        if pd.notnull(value) and value != "":
            return Decimal(str(value))
    except Exception as e:
        logger.error(f"Error converting value {value}: {e}")
    return None

# Load the dataset
dataset_path = "player_data.csv"  # Update this path if necessary
try:
    data = pd.read_csv(dataset_path)
    logger.info(f"Dataset loaded successfully from {dataset_path}.")
except FileNotFoundError:
    logger.error(f"Dataset file not found at {dataset_path}. Exiting script.")
    exit(1)
except Exception as e:
    logger.error(f"Error loading dataset: {e}. Exiting script.")
    exit(1)

# Step 1: Validate required columns
required_columns = ["PLAYER_NAME", "TEAM_NAME", "GAME_DATE"]
missing_columns = [col for col in required_columns if col not in data.columns]
if missing_columns:
    logger.error(f"Missing required columns: {missing_columns}. Exiting script.")
    exit(1)

# Step 2: Remove rows with null values in critical columns
if data["PLAYER_NAME"].isnull().any():
    missing_count = data["PLAYER_NAME"].isnull().sum()
    logger.error(f"'PLAYER_NAME' column contains {missing_count} null values. Removing invalid rows.")
    data = data.dropna(subset=["PLAYER_NAME"])

if data["TEAM_NAME"].isnull().any():
    missing_count = data["TEAM_NAME"].isnull().sum()
    logger.error(f"'TEAM_NAME' column contains {missing_count} null values. Removing invalid rows.")
    data = data.dropna(subset=["TEAM_NAME"])

if data["GAME_DATE"].isnull().any():
    missing_count = data["GAME_DATE"].isnull().sum()
    logger.error(f"'GAME_DATE' column contains {missing_count} null values. Removing invalid rows.")
    data = data.dropna(subset=["GAME_DATE"])

# Step 3: Remove duplicates based on PLAYER_NAME and GAME_DATE
duplicate_rows = data.duplicated(subset=["PLAYER_NAME", "GAME_DATE"])
if duplicate_rows.any():
    logger.warning(f"Found {duplicate_rows.sum()} duplicate rows. Removing duplicates.")
    data = data.drop_duplicates(subset=["PLAYER_NAME", "GAME_DATE"])

# Step 4: Normalize TEAM_NAME
data["TEAM_NAME"] = data["TEAM_NAME"].str.strip().str.upper()

# Step 5: Replace NaN values in optional fields with defaults
data.fillna(value={
    "MATCHUP": "Unknown",
    "WL": "Unknown",
    "VIDEO_AVAILABLE": 0  # Replace with a default value if necessary
}, inplace=True)

# Step 6: Convert numeric columns to Decimal
logger.info("Converting numeric columns to Decimal...")
numeric_columns = [
    "MIN", "FGM", "FGA", "FG_PCT", "FG3M", "FG3A", "FG3_PCT", "FTM", "FTA", "FT_PCT",
    "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV", "PF", "PTS", "PLUS_MINUS",
    "POINTS_THRESHOLD", "FG3M_THRESHOLD", "REBOUNDS_THRESHOLD", "BLOCKS_THRESHOLD", "STL_THRESHOLD", "ASSISTS_THRESHOLD",
    "ROLLING_PTS_AVG", "ROLLING_REB_AVG", "ROLLING_AST_AVG", "ROLLING_BLK_AVG", "ROLLING_STL_AVG", "ROLLING_FG3M_AVG"
]

for column in numeric_columns:
    if column in data.columns:
        try:
            data[column] = data[column].apply(safe_convert_to_decimal)
            logger.info(f"Converted column '{column}' to Decimal.")
        except Exception as e:
            logger.error(f"Error converting column '{column}': {e}")

# Step 7: Log rows containing float values
logger.info("Checking for remaining float values...")
float_rows = data.applymap(lambda x: isinstance(x, float)).any(axis=1)
if float_rows.any():
    problematic_rows = data[float_rows]
    logger.error(f"Rows containing float values:\n{problematic_rows}")
else:
    logger.info("All numeric columns successfully converted to Decimal.")

# Step 8: Log a preview of sanitized data
logger.info(f"Sample sanitized data:\n{data.head()}")

# Step 9: Upload sanitized data to DynamoDB
if __name__ == "__main__":
    logger.info("Starting upload to DynamoDB...")
    try:
        DDBQuery.upload_to_dynamodb(data)
        logger.info("Data upload to DynamoDB completed successfully.")
    except Exception as e:
        logger.error(f"Error uploading data to DynamoDB: {e}")