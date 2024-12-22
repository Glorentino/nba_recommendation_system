
def filter_by_date_range(data, start_date=None, end_date=None):
    """
    Filter stats by date range.

    :param data: DataFrame containing stats with a 'GAME_DATE' column
    :param start_date: Start date as a string (YYYY-MM-DD)
    :param end_date: End date as a string (YYYY-MM-DD)
    :return: Filtered DataFrame
    """
    if start_date:
        data = data[data["GAME_DATE"] >= start_date]
    if end_date:
        data = data[data["GAME_DATE"] <= end_date]
    return data

def filter_by_threshold(data, column, threshold):
    """
    Filter stats by a numeric threshold.

    :param data: DataFrame containing stats
    :param column: Column name to filter by
    :param threshold: Minimum value to filter
    :return: Filtered DataFrame
    """
    return data[data[column] >= threshold]