import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np

# Load data
data = pd.read_csv("area_demand.csv")

X = data[['day']]
y = data['total_demand']

# Train model
model = LinearRegression()
model.fit(X, y)

# Predict next 5 days
future_days = np.array([11, 12, 13, 14, 15]).reshape(-1, 1)
predictions = model.predict(future_days)

# Plot
plt.scatter(X, y, color='blue', label="Historical Demand")
plt.plot(X, model.predict(X), color='red', label="Regression Line")
plt.scatter(future_days, predictions, color='green', label="Predicted Demand")

plt.xlabel("Day")
plt.ylabel("Total Medicine Demand")
plt.title("Area Level Medicine Demand Forecast (Linear Regression)")
plt.legend()
plt.savefig("demand_forecast.png")
print("Graph saved as demand_forecast.png")
print("Predicted future demand:", predictions)


