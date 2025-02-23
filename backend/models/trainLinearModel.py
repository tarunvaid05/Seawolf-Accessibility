
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import joblib

# Example training data:
# Features: [distance, avg_slope, stairs]
X_train = np.array([
    [1200, 0.02, 0],
    [1500, 0.05, 1],
    [1000, 0.01, 0],
    [2000, 0.03, 0],
    [1800, 0.04, 2]
])
y_train = np.array([20, 40, 15, 30, 45])  # Target cost values (lower is better)

# Create a pipeline that first scales the features then applies linear regression.
pipeline = make_pipeline(StandardScaler(), LinearRegression())
pipeline.fit(X_train, y_train)

# Save the trained pipeline model to disk.
joblib.dump(pipeline, "trained_route_model.joblib")
print("Pipeline Linear Regression model trained and saved.")