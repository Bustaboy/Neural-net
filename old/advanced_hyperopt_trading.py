# advanced_hyperparameter_optimization.py

import optuna
from optuna.samplers import TPESampler, CmaEsSampler, RandomSampler
from optuna.pruners import MedianPruner, HyperbandPruner
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import xgboost as xgb
import lightgbm as lgb
from sklearn.neural_network import MLPClassifier
import warnings
import logging
import json
from datetime import datetime
import joblib
from typing import Dict, Tuple, Any, Optional
import matplotlib.pyplot as plt
import seaborn as sns

# Import from your main bot
from enhanced_trading_bot_complete import EnhancedMLPredictor

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AdvancedHyperparameterOptimizer:
    """
    Advanced hyperparameter optimization for trading ML models.
    Supports multiple algorithms and optimization strategies.
    """
    
    def __init__(self, n_trials: int = 100, n_jobs: int = -1):
        self.n_trials = n_trials
        self.n_jobs = n_jobs
        self.best_params = {}
        self.optimization_history = []
        self.logger = logging.getLogger(__name__)
        
    def create_model(self, trial: optuna.Trial, model_type: str) -> Any:
        """
        Create model with hyperparameters suggested by Optuna.
        
        Args:
            trial: Optuna trial object
            model_type: Type of model to create
            
        Returns:
            Configured model instance
        """
        if model_type == "random_forest":
            return RandomForestClassifier(
                n_estimators=trial.suggest_int('rf_n_estimators', 50, 500),
                max_depth=trial.suggest_int('rf_max_depth', 5, 50),
                min_samples_split=trial.suggest_int('rf_min_samples_split', 2, 20),
                min_samples_leaf=trial.suggest_int('rf_min_samples_leaf', 1, 10),
                max_features=trial.suggest_categorical('rf_max_features', ['sqrt', 'log2', None]),
                bootstrap=trial.suggest_categorical('rf_bootstrap', [True, False]),
                random_state=42,
                n_jobs=self.n_jobs
            )
            
        elif model_type == "xgboost":
            return xgb.XGBClassifier(
                n_estimators=trial.suggest_int('xgb_n_estimators', 50, 500),
                max_depth=trial.suggest_int('xgb_max_depth', 3, 20),
                learning_rate=trial.suggest_float('xgb_learning_rate', 0.01, 0.3, log=True),
                subsample=trial.suggest_float('xgb_subsample', 0.6, 1.0),
                colsample_bytree=trial.suggest_float('xgb_colsample_bytree', 0.6, 1.0),
                gamma=trial.suggest_float('xgb_gamma', 0, 5),
                reg_alpha=trial.suggest_float('xgb_reg_alpha', 0, 1),
                reg_lambda=trial.suggest_float('xgb_reg_lambda', 0, 1),
                min_child_weight=trial.suggest_int('xgb_min_child_weight', 1, 10),
                random_state=42,
                n_jobs=self.n_jobs,
                use_label_encoder=False,
                eval_metric='logloss'
            )
            
        elif model_type == "lightgbm":
            return lgb.LGBMClassifier(
                n_estimators=trial.suggest_int('lgb_n_estimators', 50, 500),
                max_depth=trial.suggest_int('lgb_max_depth', 3, 20),
                learning_rate=trial.suggest_float('lgb_learning_rate', 0.01, 0.3, log=True),
                num_leaves=trial.suggest_int('lgb_num_leaves', 20, 300),
                feature_fraction=trial.suggest_float('lgb_feature_fraction', 0.5, 1.0),
                bagging_fraction=trial.suggest_float('lgb_bagging_fraction', 0.5, 1.0),
                bagging_freq=trial.suggest_int('lgb_bagging_freq', 1, 10),
                min_child_samples=trial.suggest_int('lgb_min_child_samples', 5, 100),
                lambda_l1=trial.suggest_float('lgb_lambda_l1', 0, 1),
                lambda_l2=trial.suggest_float('lgb_lambda_l2', 0, 1),
                random_state=42,
                n_jobs=self.n_jobs,
                verbosity=-1
            )
            
        elif model_type == "gradient_boosting":
            return GradientBoostingClassifier(
                n_estimators=trial.suggest_int('gb_n_estimators', 50, 300),
                max_depth=trial.suggest_int('gb_max_depth', 3, 10),
                learning_rate=trial.suggest_float('gb_learning_rate', 0.01, 0.3, log=True),
                min_samples_split=trial.suggest_int('gb_min_samples_split', 2, 20),
                min_samples_leaf=trial.suggest_int('gb_min_samples_leaf', 1, 10),
                subsample=trial.suggest_float('gb_subsample', 0.6, 1.0),
                max_features=trial.suggest_categorical('gb_max_features', ['sqrt', 'log2', None]),
                random_state=42
            )
            
        elif model_type == "neural_network":
            n_layers = trial.suggest_int('nn_n_layers', 1, 3)
            layers = []
            for i in range(n_layers):
                layers.append(trial.suggest_int(f'nn_layer_{i}_size', 50, 200))
                
            return MLPClassifier(
                hidden_layer_sizes=tuple(layers),
                activation=trial.suggest_categorical('nn_activation', ['relu', 'tanh']),
                solver=trial.suggest_categorical('nn_solver', ['adam', 'lbfgs']),
                alpha=trial.suggest_float('nn_alpha', 0.0001, 0.1, log=True),
                learning_rate=trial.suggest_categorical('nn_learning_rate', ['constant', 'adaptive']),
                learning_rate_init=trial.suggest_float('nn_learning_rate_init', 0.001, 0.1, log=True),
                max_iter=trial.suggest_int('nn_max_iter', 200, 1000),
                early_stopping=True,
                random_state=42
            )
            
    def objective(self, trial: optuna.Trial, X: np.ndarray, y: np.ndarray, 
                  model_type: str, eval_metric: str = 'sharpe_ratio') -> float:
        """
        Objective function for Optuna optimization.
        
        Args:
            trial: Optuna trial
            X: Features
            y: Labels
            model_type: Type of model to optimize
            eval_metric: Metric to optimize ('sharpe_ratio', 'accuracy', 'f1', 'profit')
            
        Returns:
            Metric value to optimize
        """
        # Create model with trial parameters
        model = self.create_model(trial, model_type)
        
        # Use time series cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        
        if eval_metric == 'sharpe_ratio':
            # Custom evaluation using backtesting
            sharpe_ratios = []
            
            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X[train_idx], X[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]
                
                # Train model
                model.fit(X_train, y_train)
                
                # Get predictions
                predictions = model.predict(X_val)
                
                # Calculate returns (simplified)
                returns = []
                for i, (pred, actual) in enumerate(zip(predictions, y_val)):
                    if pred == 1:  # Buy signal
                        ret = 1 if actual == 1 else -1  # Simplified return calculation
                        returns.append(ret)
                
                if returns:
                    sharpe = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)
                    sharpe_ratios.append(sharpe)
                    
            return np.mean(sharpe_ratios) if sharpe_ratios else 0
            
        elif eval_metric == 'accuracy':
            scores = cross_val_score(model, X, y, cv=tscv, scoring='accuracy', n_jobs=1)
            return scores.mean()
            
        elif eval_metric == 'f1':
            scores = cross_val_score(model, X, y, cv=tscv, scoring='f1', n_jobs=1)
            return scores.mean()
            
        elif eval_metric == 'profit':
            # Custom profit-based evaluation
            profits = []
            
            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X[train_idx], X[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]
                
                model.fit(X_train, y_train)
                predictions = model.predict_proba(X_val)[:, 1]
                
                # Calculate profit with position sizing based on confidence
                profit = 0
                for pred_prob, actual in zip(predictions, y_val):
                    if pred_prob > 0.6:  # Only trade high confidence
                        position_size = min(pred_prob, 0.9)  # Cap position size
                        profit += position_size if actual == 1 else -position_size
                        
                profits.append(profit)
                
            return np.mean(profits)
    
    def optimize(self, X: np.ndarray, y: np.ndarray, model_types: list = None,
                 eval_metric: str = 'sharpe_ratio', sampler: str = 'tpe') -> Dict:
        """
        Run hyperparameter optimization for multiple model types.
        
        Args:
            X: Training features
            y: Training labels
            model_types: List of model types to optimize
            eval_metric: Metric to optimize
            sampler: Optuna sampler type ('tpe', 'cmaes', 'random')
            
        Returns:
            Dictionary of best parameters for each model type
        """
        if model_types is None:
            model_types = ['random_forest', 'xgboost', 'lightgbm']
            
        results = {}
        
        for model_type in model_types:
            self.logger.info(f"Optimizing {model_type} model...")
            
            # Select sampler
            if sampler == 'tpe':
                study_sampler = TPESampler(seed=42)
            elif sampler == 'cmaes':
                study_sampler = CmaEsSampler(seed=42)
            else:
                study_sampler = RandomSampler(seed=42)
                
            # Create study with pruning
            study = optuna.create_study(
                direction='maximize',
                sampler=study_sampler,
                pruner=MedianPruner(n_startup_trials=10, n_warmup_steps=5)
            )
            
            # Optimize
            study.optimize(
                lambda trial: self.objective(trial, X, y, model_type, eval_metric),
                n_trials=self.n_trials,
                n_jobs=1  # Set to 1 to avoid conflicts with model parallelization
            )
            
            # Store results
            results[model_type] = {
                'best_params': study.best_params,
                'best_value': study.best_value,
                'best_trial': study.best_trial.number,
                'study': study
            }
            
            self.logger.info(f"Best {eval_metric} for {model_type}: {study.best_value:.4f}")
            
        self.best_params = results
        return results
    
    def ensemble_optimization(self, X: np.ndarray, y: np.ndarray, 
                            base_models: list = None) -> Dict:
        """
        Optimize an ensemble of models with weighted voting.
        
        Args:
            X: Training features
            y: Training labels
            base_models: List of base model types
            
        Returns:
            Optimal ensemble configuration
        """
        if base_models is None:
            base_models = ['random_forest', 'xgboost', 'lightgbm']
            
        # First optimize individual models
        individual_results = self.optimize(X, y, base_models)
        
        # Then optimize ensemble weights
        def ensemble_objective(trial):
            weights = []
            for model_type in base_models:
                weight = trial.suggest_float(f'weight_{model_type}', 0, 1)
                weights.append(weight)
                
            # Normalize weights
            weights = np.array(weights)
            weights = weights / weights.sum()
            
            # Create models with best parameters
            models = []
            for model_type, weight in zip(base_models, weights):
                best_params = individual_results[model_type]['best_params']
                # Create model (simplified - remove prefixes from params)
                if model_type == 'random_forest':
                    clean_params = {k.replace('rf_', ''): v for k, v in best_params.items()}
                    model = RandomForestClassifier(**clean_params, random_state=42)
                elif model_type == 'xgboost':
                    clean_params = {k.replace('xgb_', ''): v for k, v in best_params.items()}
                    model = xgb.XGBClassifier(**clean_params, random_state=42, use_label_encoder=False)
                elif model_type == 'lightgbm':
                    clean_params = {k.replace('lgb_', ''): v for k, v in best_params.items()}
                    model = lgb.LGBMClassifier(**clean_params, random_state=42, verbosity=-1)
                    
                models.append((model, weight))
            
            # Evaluate ensemble
            tscv = TimeSeriesSplit(n_splits=5)
            scores = []
            
            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X[train_idx], X[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]
                
                # Train all models
                predictions = []
                for model, weight in models:
                    model.fit(X_train, y_train)
                    pred_proba = model.predict_proba(X_val)[:, 1]
                    predictions.append(pred_proba * weight)
                
                # Weighted average
                ensemble_pred = np.sum(predictions, axis=0)
                ensemble_binary = (ensemble_pred > 0.5).astype(int)
                
                score = f1_score(y_val, ensemble_binary)
                scores.append(score)
                
            return np.mean(scores)
        
        # Optimize ensemble weights
        ensemble_study = optuna.create_study(direction='maximize')
        ensemble_study.optimize(ensemble_objective, n_trials=50)
        
        ensemble_results = {
            'base_models': individual_results,
            'ensemble_weights': ensemble_study.best_params,
            'ensemble_performance': ensemble_study.best_value
        }
        
        return ensemble_results
    
    def bayesian_optimization_with_gaussian_process(self, X: np.ndarray, y: np.ndarray,
                                                  model_type: str = 'xgboost') -> Dict:
        """
        Advanced Bayesian optimization using Gaussian Process surrogate.
        
        Args:
            X: Training features
            y: Training labels
            model_type: Model type to optimize
            
        Returns:
            Optimization results
        """
        from skopt import BayesSearchCV
        from skopt.space import Real, Integer
        
        # Define search space based on model type
        if model_type == 'xgboost':
            search_spaces = {
                'n_estimators': Integer(50, 500),
                'max_depth': Integer(3, 20),
                'learning_rate': Real(0.01, 0.3, prior='log-uniform'),
                'subsample': Real(0.6, 1.0),
                'colsample_bytree': Real(0.6, 1.0),
                'gamma': Real(0, 5),
                'reg_alpha': Real(0, 1),
                'reg_lambda': Real(0, 1)
            }
            base_model = xgb.XGBClassifier(random_state=42, use_label_encoder=False)
            
        elif model_type == 'lightgbm':
            search_spaces = {
                'n_estimators': Integer(50, 500),
                'max_depth': Integer(3, 20),
                'learning_rate': Real(0.01, 0.3, prior='log-uniform'),
                'num_leaves': Integer(20, 300),
                'feature_fraction': Real(0.5, 1.0),
                'bagging_fraction': Real(0.5, 1.0),
                'lambda_l1': Real(0, 1),
                'lambda_l2': Real(0, 1)
            }
            base_model = lgb.LGBMClassifier(random_state=42, verbosity=-1)
            
        # Perform Bayesian optimization
        bayes_search = BayesSearchCV(
            base_model,
            search_spaces,
            n_iter=self.n_trials,
            cv=TimeSeriesSplit(n_splits=5),
            n_jobs=self.n_jobs,
            verbose=0,
            random_state=42
        )
        
        bayes_search.fit(X, y)
        
        return {
            'best_params': bayes_search.best_params_,
            'best_score': bayes_search.best_score_,
            'optimizer': bayes_search
        }
    
    def save_optimization_results(self, filepath: str):
        """Save optimization results to file."""
        results_to_save = {
            'best_params': self.best_params,
            'optimization_history': self.optimization_history,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(results_to_save, f, indent=4, default=str)
            
        self.logger.info(f"Optimization results saved to {filepath}")
    
    def visualize_optimization(self, study: optuna.Study, model_type: str):
        """
        Create visualizations of the optimization process.
        
        Args:
            study: Optuna study object
            model_type: Model type name for titles
        """
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Hyperparameter Optimization Results - {model_type}', fontsize=16)
        
        # 1. Optimization history
        ax = axes[0, 0]
        trials = [t.value for t in study.trials if t.value is not None]
        ax.plot(trials, 'b-', alpha=0.5)
        ax.plot(np.maximum.accumulate(trials), 'r-', linewidth=2, label='Best value')
        ax.set_xlabel('Trial')
        ax.set_ylabel('Objective Value')
        ax.set_title('Optimization History')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 2. Parameter importance
        ax = axes[0, 1]
        try:
            importance = optuna.importance.get_param_importances(study)
            params = list(importance.keys())
            values = list(importance.values())
            y_pos = np.arange(len(params))
            ax.barh(y_pos, values)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(params)
            ax.set_xlabel('Importance')
            ax.set_title('Parameter Importance')
            ax.grid(True, alpha=0.3, axis='x')
        except:
            ax.text(0.5, 0.5, 'Not enough trials for importance', 
                   ha='center', va='center', transform=ax.transAxes)
        
        # 3. Parallel coordinate plot (simplified)
        ax = axes[1, 0]
        ax.text(0.5, 0.5, 'Use optuna.visualization for\ninteractive parallel coordinates', 
               ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Parameter Relationships')
        
        # 4. Best trial parameters
        ax = axes[1, 1]
        ax.axis('off')
        best_trial = study.best_trial
        param_text = "Best Trial Parameters:\n\n"
        for key, value in best_trial.params.items():
            param_text += f"{key}: {value:.4f}\n" if isinstance(value, float) else f"{key}: {value}\n"
        param_text += f"\nBest Value: {best_trial.value:.4f}"
        ax.text(0.1, 0.9, param_text, transform=ax.transAxes, 
               fontsize=10, verticalalignment='top', fontfamily='monospace')
        
        plt.tight_layout()
        plt.savefig(f'optimization_{model_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        plt.show()


class AutoMLTradingBot:
    """
    Trading bot with automated machine learning and hyperparameter optimization.
    """
    
    def __init__(self, optimizer: AdvancedHyperparameterOptimizer = None):
        self.optimizer = optimizer or AdvancedHyperparameterOptimizer()
        self.models = {}
        self.ensemble_config = None
        self.logger = logging.getLogger(__name__)
        
    def auto_train(self, X: np.ndarray, y: np.ndarray, 
                   optimize_models: list = None,
                   use_ensemble: bool = True) -> Dict:
        """
        Automatically train and optimize models.
        
        Args:
            X: Training features
            y: Training labels
            optimize_models: List of models to optimize
            use_ensemble: Whether to create an ensemble
            
        Returns:
            Training results
        """
        self.logger.info("Starting automated training and optimization...")
        
        # Run optimization
        optimization_results = self.optimizer.optimize(
            X, y, 
            model_types=optimize_models,
            eval_metric='sharpe_ratio'
        )
        
        # Train final models with best parameters
        for model_type, results in optimization_results.items():
            self.logger.info(f"Training final {model_type} model...")
            
            # Create model with best parameters
            best_params = results['best_params']
            
            if model_type == 'random_forest':
                clean_params = {k.replace('rf_', ''): v for k, v in best_params.items()}
                model = RandomForestClassifier(**clean_params, random_state=42)
            elif model_type == 'xgboost':
                clean_params = {k.replace('xgb_', ''): v for k, v in best_params.items()}
                model = xgb.XGBClassifier(**clean_params, random_state=42, use_label_encoder=False)
            elif model_type == 'lightgbm':
                clean_params = {k.replace('lgb_', ''): v for k, v in best_params.items()}
                model = lgb.LGBMClassifier(**clean_params, random_state=42, verbosity=-1)
                
            # Train on full dataset
            model.fit(X, y)
            self.models[model_type] = model
            
        # Create ensemble if requested
        if use_ensemble and len(self.models) > 1:
            self.logger.info("Creating optimized ensemble...")
            self.ensemble_config = self.optimizer.ensemble_optimization(X, y, list(self.models.keys()))
            
        return {
            'optimization_results': optimization_results,
            'trained_models': list(self.models.keys()),
            'ensemble_config': self.ensemble_config
        }
    
    def predict_with_confidence(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions with confidence scores.
        
        Args:
            X: Features to predict
            
        Returns:
            Tuple of (predictions, confidence_scores)
        """
        if self.ensemble_config:
            # Use ensemble
            predictions = []
            weights = self.ensemble_config['ensemble_weights']
            
            for model_type, model in self.models.items():
                weight = weights.get(f'weight_{model_type}', 1.0 / len(self.models))
                pred_proba = model.predict_proba(X)[:, 1]
                predictions.append(pred_proba * weight)
                
            ensemble_proba = np.sum(predictions, axis=0)
            ensemble_pred = (ensemble_proba > 0.5).astype(int)
            
            return ensemble_pred, ensemble_proba
        else:
            # Use best single model
            best_model = list(self.models.values())[0]
            predictions = best_model.predict(X)
            confidence = best_model.predict_proba(X)[:, 1]
            
            return predictions, confidence


# Example usage and integration
if __name__ == "__main__":
    # Generate example data
    print("Generating example data...")
    np.random.seed(42)
    n_samples = 1000
    n_features = 23
    
    X = np.random.randn(n_samples, n_features)
    # Create a more realistic target with some pattern
    y = ((X[:, 0] > 0) & (X[:, 1] > 0.5)).astype(int)
    y[::10] = 1 - y[::10]  # Add some noise
    
    # Initialize optimizer
    optimizer = AdvancedHyperparameterOptimizer(n_trials=20)
    
    # Run optimization for multiple models
    print("\n1. Running multi-model optimization...")
    results = optimizer.optimize(
        X, y,
        model_types=['random_forest', 'xgboost', 'lightgbm'],
        eval_metric='sharpe_ratio'
    )
    
    # Print results
    print("\n--- Optimization Results ---")
    for model_type, result in results.items():
        print(f"\n{model_type.upper()}:")
        print(f"  Best Sharpe Ratio: {result['best_value']:.4f}")
        print(f"  Best Trial: #{result['best_trial']}")
        print("  Best Parameters:")
        for param, value in result['best_params'].items():
            print(f"    {param}: {value}")
    
    # Visualize results for best model
    best_model_type = max(results.items(), key=lambda x: x[1]['best_value'])[0]
    optimizer.visualize_optimization(results[best_model_type]['study'], best_model_type)
    
    # Save results
    optimizer.save_optimization_results('optimization_results.json')
    
    # 2. Test ensemble optimization
    print("\n\n2. Running ensemble optimization...")
    ensemble_results = optimizer.ensemble_optimization(X, y)
    print(f"\nEnsemble Performance: {ensemble_results['ensemble_performance']:.4f}")
    print("Ensemble Weights:")
    for param, value in ensemble_results['ensemble_weights'].items():
        print(f"  {param}: {value:.4f}")
    
    # 3. Test AutoML bot
    print("\n\n3. Testing AutoML Trading Bot...")
    automl_bot = AutoMLTradingBot(optimizer)
    training_results = automl_bot.auto_train(X, y, use_ensemble=True)
    
    # Make predictions
    X_test = np.random.randn(10, n_features)
    predictions, confidence = automl_bot.predict_with_confidence(X_test)
    
    print("\nSample Predictions:")
    for i in range(min(5, len(predictions))):
        signal = "BUY" if predictions[i] == 1 else "HOLD"
        print(f"  Sample {i}: {signal} (confidence: {confidence[i]:.2%})")
