import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np
import os
def predict_next_week_demand():
    # Load data
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    data = pd.read_csv(os.path.join(BASE_DIR, "area_demand.csv"))

    X = data[['day']]
    y = data['total_demand']

    # Train model
    model = LinearRegression()
    model.fit(X, y)

    # Predict next 7 days
    last_day = X['day'].max()
    future_days = np.array(range(last_day+1, last_day+8)).reshape(-1, 1)
    predictions = model.predict(future_days)

    # Plot
    plt.figure(figsize=(8,5))
    plt.scatter(X, y, label="Historical Demand")
    plt.plot(X, model.predict(X), label="Regression Line")
    plt.scatter(future_days, predictions, label="Next Week Prediction")
    plt.xlabel("Day")
    plt.ylabel("Total Medicine Demand")
    plt.title("Weekly Area Demand Forecast (Linear Regression)")
    plt.legend()
    plt.savefig("demand_forecast.png")

    # Total next week demand
    total_weekly_demand = int(predictions.sum())

    return total_weekly_demand, predictions


if __name__== "__main__":
    total, predictions = predict_next_week_demand()

    print("Predicted daily demand for next 7 days:")
    print(predictions)

    print("\nTotal predicted demand for next week:", total)