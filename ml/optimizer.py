# ml/optimizer.py
import optuna
from sklearn.metrics import f1_score
from typing import Dict, Any

class BayesianOptimizer:
    def optimize(self, X: np.ndarray, y: np.ndarray, n_trials: int = 50) -> Dict[str, Any]:
        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 50, 200),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3)
            }
            model = RandomForestClassifier(**params, random_state=42)
            model.fit(X, y)
            return f1_score(y, model.predict(X))

        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        return study.best_params
