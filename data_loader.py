import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def load_data():
    np.random.seed(42)

    n = 5000
    dates = [datetime.now() - timedelta(days=i) for i in range(n)]

    df = pd.DataFrame({
        "order_id": range(n),
        "customer_id": np.random.randint(1, 1000, n),
        "order_date": dates,
        "revenue": np.random.randint(100, 1000, n),
        "category": np.random.choice(["electronics","fashion","home"], n),
        "state": np.random.choice(["SP","RJ","MG"], n)
    })

    return df, False