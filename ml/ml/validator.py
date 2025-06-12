# ml/validator.py
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score
import numpy as np

class CrossValidator:
    def validate(self, model, X: np.ndarray, y: np.ndarray, cv_folds: int = 5) -> np.ndarray:
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        scores = []
        for train_idx, test_idx in skf.split(X, y):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            model.fit(X_train, y_train)
            scores.append(f1_score(y_test, model.predict(X_test)))
        return np.array(scores)
