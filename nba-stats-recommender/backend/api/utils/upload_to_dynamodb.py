import pandas as pd
import logging
from decimal import Decimal
from dynamodb_helper import upload_to_dynamodb

logging.basicConfig(
    filename="sanitize_and_upload.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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

# Step 1: Verify data types and float presence
logger.info("Verifying data types and float presence...")

# Check for remaining float columns
remaining_float_columns = data.select_dtypes(include=["float"]).columns
if len(remaining_float_columns) > 0:
    logger.warning(f"Remaining float columns: {remaining_float_columns}")
else:
    logger.info("No float columns remain.")

# Check for any float values row-wise
def check_for_floats(row):
    return any(isinstance(val, float) for val in row.values)

float_rows = data.apply(check_for_floats, axis=1).sum()
if float_rows > 0:
    logger.warning(f"Number of rows with float values: {float_rows}")
else:
    logger.info("No rows contain float values.")

# Step 2: Reconvert all float columns to Decimal
logger.info("Converting float columns to Decimal...")
for column in data.columns:
    try:
        if data[column].dtype == "float64" or data[column].dtype == "object":
            try:
                data[column] = data[column].apply(lambda x: Decimal(str(x)) if pd.notnull(x) else None)
                logger.info(f"Converted column '{column}' to Decimal.")
            except Exception as e:
                print(f"Error converting column '{column}': {e}")
    except Exception as e:
        logger.error(f"Error converting column '{column}': {e}")

# Final check for remaining float values
remaining_float_columns_after = data.select_dtypes(include=["float"]).columns
if len(remaining_float_columns_after) > 0:
    logger.warning(f"After conversion, float columns still exist: {remaining_float_columns_after}")
else:
    logger.info("All float columns successfully converted to Decimal.")

# Step 3: Upload sanitized data to DynamoDB
if __name__ == "__main__":
    logger.info("Starting upload to DynamoDB...")
    try:
        upload_to_dynamodb(data)
        logger.info("Data upload to DynamoDB completed successfully.")
    except Exception as e:
        logger.error(f"Error uploading data to DynamoDB: {e}")