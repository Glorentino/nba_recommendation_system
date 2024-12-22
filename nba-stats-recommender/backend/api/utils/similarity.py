import numpy as np

def calculate_similarity(player_stats, other_stats):
    """
    Calculate the similarity between two players based on their stats using Euclidean distance.
    
    :param player_stats: Dict with keys ['PTS', 'REB', 'AST'] for target player stats
    :param other_stats: Dict with keys ['PTS', 'REB', 'AST'] for other player stats
    :return: Similarity score (float)
    """
    
    try:
        target = np.array([player_stats.get("PTS", 0), player_stats.get("REB", 0), player_stats.get("AST", 0)])
        other = np.array([other_stats.get("PTS", 0), other_stats.get("REB", 0), other_stats.get("AST", 0)])
        print(f"Calculating similarity: Target={target}, Other={other}")  # Debugging
        return np.linalg.norm(target - other)
    except Exception as e:
        print(f"Error calculating similarity: {str(e)}")
        return float("inf")  # Return a high value for dissimilar players