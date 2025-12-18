# app/ml_model.py
"""
ML model wrapper: RandomForest starter model.
Features added:
 - train_dummy(...) (unchanged) but now saves metadata via crud.save_model_metadata
 - train_from_yfinance(...) same as before
 - load_model_from_path(path) -> loads pickle into memory
 - load_latest_model_from_db() -> loads model file path recorded in DB (crud.get_latest_model)
 - predict(...) and predict_from_symbol(...) unchanged and use in-memory model
"""
import pickle
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from .historical_fetcher import fetch_recent_ohlc
from .crud import save_model_metadata, get_latest_model

MODEL_FILE = Path("app/storage/rf_model.pkl")

class MLModel:
    def __init__(self):
        self.model = None
        # try load local MODEL_FILE first
        if MODEL_FILE.exists():
            try:
                self.model = pickle.loads(MODEL_FILE.read_bytes())
            except Exception:
                self.model = None
        else:
            # try to load latest model referenced in DB
            try:
                latest = get_latest_model()
                if latest and latest.filename:
                    p = Path(latest.filename)
                    if p.exists():
                        self.model = pickle.loads(p.read_bytes())
            except Exception:
                self.model = None

    def load_model_from_path(self, path: str):
        """
        Load a pickle model file into memory from given path.
        Accepts absolute path or relative path under project root.
        """
        p = Path(path)
        if not p.exists():
            # try under app/storage
            alt = Path("app/storage") / p.name
            if alt.exists():
                p = alt
        if not p.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        data = p.read_bytes()
        m = pickle.loads(data)
        self.model = m
        # also copy to central MODEL_FILE for consistency (optional)
        try:
            MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
            MODEL_FILE.write_bytes(data)
        except Exception:
            pass
        return True

    def load_latest_model_from_db(self):
        """
        Load the latest model path from DB (crud.get_latest_model()) and load it.
        """
        latest = get_latest_model()
        if not latest or not latest.filename:
            return False
        try:
            self.load_model_from_path(latest.filename)
            return True
        except Exception:
            return False

    def train_dummy(self, hist_df: pd.DataFrame):
        """
        hist_df: DataFrame with columns ['open','high','low','close','volume']
        This trains a simple RandomForest classifier to predict next-bar up/down.
        After training it saves the model to MODEL_FILE and registers metadata in DB.
        """
        df = hist_df.copy().reset_index(drop=True)
        if df.empty or len(df) < 50:
            return {"success": False, "error": "not enough data"}
        # compute label = next close return > 0
        df['next_close'] = df['close'].shift(-1)
        df['return_next'] = (df['next_close'] - df['close']) / df['close']
        df = df.dropna().reset_index(drop=True)
        df['up'] = (df['return_next'] > 0).astype(int)

        # features
        df['r1'] = (df['close'] - df['open']) / df['open']
        df['r2'] = (df['high'] - df['low']) / df['open']
        df['vol_norm'] = (df['volume'] - df['volume'].rolling(20).mean()).fillna(0)

        features = ['r1','r2','vol_norm']
        X = df[features].fillna(0)
        y = df['up']

        m = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        m.fit(X, y)
        self.model = m

        MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        MODEL_FILE.write_bytes(pickle.dumps(m))

        # Save metadata in DB (crud)
        try:
            save_model_metadata(filename=str(MODEL_FILE), rows=len(X), metrics={"n_estimators": m.n_estimators}, notes="trained via train_dummy", active=True)
        except Exception:
            # do not break training response on DB write failure
            pass

        return {"success": True, "trained_rows": len(X)}

    def train_from_yfinance(self, yf_symbol: str, period: str = "6mo", interval: str = "5m"):
        """
        Fetch history via yfinance and train.
        Example: yf_symbol='RELIANCE.NS'
        """
        df = fetch_recent_ohlc(yf_symbol, provider_preference="yfinance", period=period, interval=interval)
        if df is None or df.empty or len(df) < 50:
            return {"success": False, "error": "not enough data"}
        return self.train_dummy(df)

    def predict(self, recent_df: pd.DataFrame):
        """
        recent_df: DataFrame with open,high,low,close,volume (rows sorted oldest->newest)
        Returns: {"prob_down": x, "prob_up": y}
        """
        if self.model is None:
            return {"prob_down": 0.5, "prob_up": 0.5}
        df = recent_df.copy().reset_index(drop=True)
        if df.empty:
            return {"prob_down": 0.5, "prob_up": 0.5}
        df['r1'] = (df['close'] - df['open']) / df['open']
        df['r2'] = (df['high'] - df['low']) / df['open']
        df['vol_norm'] = (df['volume'] - df['volume'].rolling(20).mean()).fillna(0)
        features = ['r1','r2','vol_norm']
        last = df[features].tail(1).fillna(0)
        try:
            prob = self.model.predict_proba(last)[0]
            return {"prob_down": float(prob[0]), "prob_up": float(prob[1])}
        except Exception:
            return {"prob_down": 0.5, "prob_up": 0.5}

    def predict_from_symbol(self, yf_symbol: str, period: str = "2d", interval: str = "5m"):
        """
        Convenience wrapper: fetch recent OHLC then predict.
        """
        df = fetch_recent_ohlc(yf_symbol, provider_preference="yfinance", period=period, interval=interval)
        if df is None or df.empty:
            return {"prob_down": 0.5, "prob_up": 0.5}
        recent = df.reset_index().rename(columns={"index":"timestamp"})[['open','high','low','close','volume']].tail(50)
        return self.predict(recent)

# singleton instance
ml_model = MLModel()
