"""
Area demand forecast (linear regression on daily totals).

Training and serving are split:
  - train_and_save() is run offline by `manage.py train_demand_model`.
  - predict_next_week_demand() is what request code calls; it only loads the
    saved model and predicts. It never trains, reads the CSV or plots.
"""
import os

import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "area_demand.csv")
MODEL_PATH = os.environ.get("DEMAND_MODEL_PATH", os.path.join(BASE_DIR, "demand_model.joblib"))


class ModelNotTrained(Exception):
    """No saved model on disk; run `python manage.py train_demand_model`."""


# (mtime, artifact) of the last model loaded, so a retrain is picked up
# without a restart and unchanged files are not re-read on every request.
_loaded = None


def train_and_save(data_path=DATA_PATH, model_path=None, plot_path=None):
    model_path = model_path or MODEL_PATH
    from sklearn.linear_model import LinearRegression

    data = pd.read_csv(data_path)

    X = data[['day']]
    y = data['total_demand']

    model = LinearRegression()
    model.fit(X, y)

    artifact = {"model": model, "last_day": int(X['day'].max())}

    # Write then rename so a request never loads a half-written file.
    tmp_path = f"{model_path}.tmp"
    joblib.dump(artifact, tmp_path)
    os.replace(tmp_path, model_path)

    if plot_path:
        _save_plot(artifact, X, y, plot_path)

    return artifact


def _future_days(artifact):
    last_day = artifact["last_day"]
    return pd.DataFrame({"day": range(last_day + 1, last_day + 8)})


def _save_plot(artifact, X, y, plot_path):
    # Imported here so matplotlib is only ever loaded by the offline command.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    model = artifact["model"]
    future_days = _future_days(artifact)

    plt.figure(figsize=(8,5))
    plt.scatter(X, y, label="Historical Demand")
    plt.plot(X, model.predict(X), label="Regression Line")
    plt.scatter(future_days, model.predict(future_days), label="Next Week Prediction")
    plt.xlabel("Day")
    plt.ylabel("Total Medicine Demand")
    plt.title("Weekly Area Demand Forecast (Linear Regression)")
    plt.legend()
    plt.savefig(plot_path)
    plt.close()


def load_model(model_path=None):
    global _loaded
    model_path = model_path or MODEL_PATH

    try:
        mtime = os.path.getmtime(model_path)
    except OSError:
        raise ModelNotTrained(
            f"No trained model at {model_path}. Run: python manage.py train_demand_model"
        )

    if _loaded is None or _loaded[0] != (model_path, mtime):
        _loaded = ((model_path, mtime), joblib.load(model_path))

    return _loaded[1]


def predict_next_week_demand(model_path=None):
    artifact = load_model(model_path)

    # Predict next 7 days
    predictions = artifact["model"].predict(_future_days(artifact))

    # Total next week demand
    total_weekly_demand = int(predictions.sum())

    return total_weekly_demand, np.asarray(predictions)
