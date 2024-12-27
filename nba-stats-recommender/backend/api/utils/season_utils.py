from datetime import datetime

def get_current_season():
    """
    Returns the current NBA season in the format YYYY-YY (e.g., "2023-24").
    The NBA season starts in October and ends in April.
    """
    now = datetime.now()
    year = now.year
    month = now.month
    
    if month >= 10: # New NBA season starts in Octobe
        return f"{year}-{str(year + 1)[-2:]}"
    else:
        return f"{year - 1}-{str(year + 1)[-2:]}"