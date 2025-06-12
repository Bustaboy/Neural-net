"""
Ensemble model implementations with multiple algorithms
"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier, VotingClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from typing import Dict, Any, List
import logging

# Optional imports with fallback
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("XGBoost not available, using alternative models")

try:
    from lightgbm import LGBMClassifier
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logging.warning("LightGBM not available, using alternative models")


def create_ensemble_model(params: Dict[str, Any] = None) -> VotingClassifier:
    """
    Create an ensemble model with optimized parameters
    
    Args:
        params: Dictionary of hyperparameters for each model
        
    Returns:
        VotingClassifier ensemble model
    """
    if params is None:
        params = get_default_params()
    
    estimators = []
    
    # Random Forest
    rf_params = params.get('random_forest', {})
    rf = RandomForestClassifier(
        n_estimators=rf_params.get('n_estimators', 100),
        max_depth=rf_params.get('max_depth', 10),
        min_samples_split=rf_params.get('min_samples_split', 5),
        min_samples_leaf=rf_params.get('min_samples_leaf', 2),
        max_features=rf_params.get('max_features', 'sqrt'),
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'
    )
    estimators.append(('rf', rf))
    
    # Gradient Boosting
    gb_params = params.get('gradient_boosting', {})
    gb = GradientBoostingClassifier(
        n_estimators=gb_params.get('n_estimators', 100),
        max_depth=gb_params.get('max_depth', 5),
        learning_rate=gb_params.get('learning_rate', 0.1),
        subsample=gb_params.get('subsample', 0.8),
        random_state=42
    )
    estimators.append(('gb', gb))
    
    # XGBoost (if available)
    if XGBOOST_AVAILABLE:
        xgb_params = params.get('xgboost', {})
        xgb = XGBClassifier(
            n_estimators=xgb_params.get('n_estimators', 100),
            max_depth=xgb_params.get('max_depth', 6),
            learning_rate=xgb_params.get('learning_rate', 0.1),
            subsample=xgb_params.get('subsample', 0.8),
            colsample_bytree=xgb_params.get('colsample_bytree', 0.8),
            gamma=xgb_params.get('gamma', 0.1),
            random_state=42,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        estimators.append(('xgb', xgb))
    
    # LightGBM (if available)
    if LIGHTGBM_AVAILABLE:
        lgb_params = params.get('lightgbm', {})
        lgb = LGBMClassifier(
            n_estimators=lgb_params.get('n_estimators', 100),
            max_depth=lgb_params.get('max_depth', -1),
            learning_rate=lgb_params.get('learning_rate', 0.1),
            num_leaves=lgb_params.get('num_leaves', 31),
            subsample=lgb_params.get('subsample', 0.8),
            colsample_bytree=lgb_params.get('colsample_bytree', 0.8),
            random_state=42,
            verbosity=-1
        )
        estimators.append(('lgb', lgb))
    
    # Neural Network
    nn_params = params.get('neural_network', {})
    nn = MLPClassifier(
        hidden_layer_sizes=nn_params.get('hidden_layers', (100, 50)),
        activation=nn_params.get('activation', 'relu'),
        solver=nn_params.get('solver', 'adam'),
        alpha=nn_params.get('alpha', 0.0001),
        learning_rate_init=nn_params.get('learning_rate_init', 0.001),
        max_iter=nn_params.get('max_iter', 500),
        early_stopping=True,
        random_state=42
    )
    estimators.append(('nn', nn))
    
    # Logistic Regression (for baseline)
    lr_params = params.get('logistic_regression', {})
    lr = LogisticRegression(
        C=lr_params.get('C', 1.0),
        max_iter=1000,
        random_state=42,
        class_weight='balanced'
    )
    estimators.append(('lr', lr))
    
    # Support Vector Machine (optional, can be slow)
    if params.get('include_svm', False):
        svm_params = params.get('svm', {})
        svm = SVC(
            C=svm_params.get('C', 1.0),
            kernel=svm_params.get('kernel', 'rbf'),
            gamma=svm_params.get('gamma', 'scale'),
            probability=True,
            random_state=42,
            class_weight='balanced'
        )
        estimators.append(('svm', svm))
    
    # Create voting classifier
    voting_type = params.get('voting_type', 'soft')
    weights = params.get('estimator_weights', None)
    
    ensemble = VotingClassifier(
        estimators=estimators,
        voting=voting_type,
        weights=weights,
        n_jobs=-1
    )
    
    return ensemble


def get_default_params() -> Dict[str, Any]:
    """Get default hyperparameters for ensemble models"""
    return {
        'random_forest': {
            'n_estimators': 100,
            'max_depth': 10,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'max_features': 'sqrt'
        },
        'gradient_boosting': {
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.1,
            'subsample': 0.8
        },
        'xgboost': {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'gamma': 0.1
        },
        'lightgbm': {
            'n_estimators': 100,
            'max_depth': -1,
            'learning_rate': 0.1,
            'num_leaves': 31,
            'subsample': 0.8,
            'colsample_bytree': 0.8
        },
        'neural_network': {
            'hidden_layers': (100, 50),
            'activation': 'relu',
            'solver': 'adam',
            'alpha': 0.0001,
            'learning_rate_init': 0.001,
            'max_iter': 500
        },
        'logistic_regression': {
            'C': 1.0
        },
        'svm': {
            'C': 1.0,
            'kernel': 'rbf',
            'gamma': 'scale'
        },
        'voting_type': 'soft',
        'include_svm': False,
        'estimator_weights': None
    }


def create_stacking_ensemble(base_models: List[tuple], meta_model=None):
    """
    Create a stacking ensemble with custom base models and meta-learner
    
    Args:
        base_models: List of (name, model) tuples
        meta_model: Meta-learner model (default: LogisticRegression)
        
    Returns:
        StackingClassifier ensemble
    """
    from sklearn.ensemble import StackingClassifier
    
    if meta_model is None:
        meta_model = LogisticRegression(random_state=42, class_weight='balanced')
    
    stacking = StackingClassifier(
        estimators=base_models,
        final_estimator=meta_model,
        cv=5,  # 5-fold cross-validation for generating meta-features
        stack_method='predict_proba',
        n_jobs=-1
    )
    
    return stacking


def create_model_by_market_condition(market_condition: str) -> Any:
    """
    Create specialized models for different market conditions
    
    Args:
        market_condition: One of 'bull', 'bear', 'sideways', 'volatile'
        
    Returns:
        Configured model for the market condition
    """
    if market_condition == 'bull':
        # Trend-following model for bull markets
        return GradientBoostingClassifier(
            n_estimators=150,
            max_depth=7,
            learning_rate=0.15,
            subsample=0.9,
            random_state=42
        )
    
    elif market_condition == 'bear':
        # Conservative model for bear markets
        return RandomForestClassifier(
            n_estimators=200,
            max_depth=5,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            class_weight='balanced'
        )
    
    elif market_condition == 'sideways':
        # Mean reversion model for sideways markets
        return VotingClassifier([
            ('rf', RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)),
            ('lr', LogisticRegression(C=0.5, random_state=42, class_weight='balanced')),
            ('nn', MLPClassifier(hidden_layer_sizes=(50, 25), random_state=42))
        ], voting='soft')
    
    elif market_condition == 'volatile':
        # Robust model for volatile markets
        if XGBOOST_AVAILABLE:
            return XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.7,
                colsample_bytree=0.7,
                gamma=0.2,
                random_state=42,
                use_label_encoder=False,
                eval_metric='logloss'
            )
        else:
            return GradientBoostingClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.7,
                random_state=42
            )
    
    else:
        # Default ensemble for unknown conditions
        return create_ensemble_model()


class AdaptiveEnsemble:
    """Ensemble that adapts weights based on recent performance"""
    
    def __init__(self, base_models: List[tuple], window_size: int = 100):
        self.base_models = base_models
        self.window_size = window_size
        self.model_weights = np.ones(len(base_models)) / len(base_models)
        self.performance_history = {name: [] for name, _ in base_models}
        
    def fit(self, X, y):
        """Fit all base models"""
        for name, model in self.base_models:
            model.fit(X, y)
        return self
    
    def predict_proba(self, X):
        """Predict with weighted average"""
        predictions = []
        for i, (name, model) in enumerate(self.base_models):
            pred = model.predict_proba(X)
            predictions.append(pred * self.model_weights[i])
        
        # Weighted average
        final_pred = np.sum(predictions, axis=0)
        # Normalize
        final_pred = final_pred / final_pred.sum(axis=1, keepdims=True)
        
        return final_pred
    
    def predict(self, X):
        """Predict class labels"""
        proba = self.predict_proba(X)
        return np.argmax(proba, axis=1)
    
    def update_weights(self, X, y_true):
        """Update model weights based on recent performance"""
        for i, (name, model) in enumerate(self.base_models):
            y_pred = model.predict(X)
            accuracy = np.mean(y_pred == y_true)
            
            # Update performance history
            self.performance_history[name].append(accuracy)
            if len(self.performance_history[name]) > self.window_size:
                self.performance_history[name].pop(0)
            
            # Calculate average recent performance
            if len(self.performance_history[name]) > 0:
                avg_performance = np.mean(self.performance_history[name])
                self.model_weights[i] = avg_performance
        
        # Normalize weights
        if np.sum(self.model_weights) > 0:
            self.model_weights = self.model_weights / np.sum(self.model_weights)
        else:
            self.model_weights = np.ones(len(self.base_models)) / len(self.base_models)