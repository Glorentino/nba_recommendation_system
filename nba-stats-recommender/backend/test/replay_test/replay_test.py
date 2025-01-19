import requests
import json

with open("historical_requests.json", "r") as file:
    historical_requests = json.load(file)

BASE_URL = "http://127.0.0.1:8000/api"

def compare_responses(expected, actual):
    """Recursively compare nested dictionaries."""
    def deep_compare(d1, d2):
        if isinstance(d1, dict) and isinstance(d2, dict):
            return all(deep_compare(d1.get(k), d2.get(k)) for k in d1.keys() | d2.keys())
        return d1 == d2

    return deep_compare(expected, actual)

def replay_test():
    results = []
    
    for req_data in historical_requests:
        try:
            url = f"{BASE_URL}{req_data['endpoint']}"
            method = req_data['method'].upper()
            payload = req_data.get('payload', {})
            expected_status = req_data.get('expected_status', 200)
            expected_response = req_data.get('expected_response', {})
            
            if method == "GET":
                response = requests.get(url, params=payload)
            elif method == "POST":
                response = requests.post(url, json=payload)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            actual_status = response.status_code
            actual_response = response.json()
            
            result = {
                "endpoint": req_data["endpoint"],
                "method" : method,
                "status_match": actual_status == expected_status,
                "response_match": compare_responses(expected_response, actual_response),
                "actual_status": actual_status,
                "actual_response": actual_response,
                "expected_status": expected_status,
                "expected_response": expected_response,
            }
            results.append(result)
            
            if not result["status_match"] or not result["response_match"]:
                print(f"Discrepancy found for {url}:")
                print(f"Expected: {expected_response}, Got: {actual_response}")
        except Exception as e:
            print(f"Error replaying request {req_data['endpoint']}: {e}")
            results.append({"error": str(e)})
    return results

if __name__ == "__main__":
    results = replay_test()
    with open("replay_results.json", "w") as output_file:
        json.dump(results, output_file, indent=4)