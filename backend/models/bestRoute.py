import numpy as np
import joblib
from costModel import extract_features

# Load the trained linear regression model.
model = joblib.load("trained_route_model.joblib")

def select_best_route(candidate_routes):
    """
    Given a list of candidate route dictionaries,
    extract the features for each route, predict its cost using
    the trained model, and return the route with the lowest predicted cost.
    """
    predictions = []
    for route in candidate_routes:
        features = extract_features(route)
        predicted_cost = model.predict(np.array(features).reshape(1, -1))[0]
        predictions.append(predicted_cost)
    best_index = np.argmin(predictions)
    return candidate_routes[best_index]

if __name__ == "__main__":
    # Example candidate routes.
    candidate_routes = [
        {"distance": 1200, "path": [(40.910412, -73.124705), (40.911000, -73.125000)], "stairs": 0},
        {"distance": 1500, "path": [(40.910412, -73.124705), (40.912000, -73.126000)], "stairs": 1},
    ]
    best = select_best_route(candidate_routes)
    print("Best route selected:", best)