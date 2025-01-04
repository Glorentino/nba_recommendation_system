import pandas as pd
from decimal import Decimal
from dynamodb_helper import upload_to_dynamodb

# Load the dataset
dataset_path = "player_data.csv"  # Update this path if necessary
data = pd.read_csv(dataset_path)

# Step 1: Verify data types and float presence
print("Verifying data types and float presence...")

# Check for remaining float columns
remaining_float_columns = data.select_dtypes(include=["float"]).columns
if len(remaining_float_columns) > 0:
    print(f"Remaining float columns: {remaining_float_columns}")
else:
    print("No float columns remain.")

# Check for any float values row-wise
def check_for_floats(row):
    return any(isinstance(val, float) for val in row.values)

float_rows = data.apply(check_for_floats, axis=1).sum()
if float_rows > 0:
    print(f"Number of rows with float values: {float_rows}")
else:
    print("No rows contain float values.")

# Step 2: Reconvert all float columns to Decimal
print("Converting float columns to Decimal...")
for column in data.columns:
    if data[column].dtype == "float64" or data[column].dtype == "object":
        try:
            data[column] = data[column].apply(lambda x: Decimal(str(x)) if pd.notnull(x) else None)
            print(f"Converted column '{column}' to Decimal.")
        except Exception as e:
            print(f"Error converting column '{column}': {e}")

# Step 3: Upload sanitized data to DynamoDB
if __name__ == "__main__":
    print("Uploading data to DynamoDB...")
    upload_to_dynamodb(data)