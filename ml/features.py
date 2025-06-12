# ml/features.py
import pandas as pd
import numpy as np
from typing import Tuple, List

class FeatureEngineer:
    def __init__(self, config: dict):
        self.config = config

    def create_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        features = df.copy()
        feature_names = []

        # Technical indicators from ml_config.yaml
        if 'rsi_14' in self.config['feature_engineering']['technical_indicators']:
            features['rsi_14'] = self._calculate_rsi(df['price'])
            feature_names.append('rsi_14')

        # Market features
        for feature in self.config['feature_engineering']['market_features']:
            if feature in df.columns:
                features[feature] = df[feature]
                feature_names.append(feature)

        return features[feature_names], feature_names

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
