import pandas as pd
from prophet import Prophet

def forecast_revenue(df):
    ts = df.groupby("order_date")["revenue"].sum().reset_index()
    ts.columns = ["ds", "y"]

    model = Prophet()
    model.fit(ts)

    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)

    return forecast