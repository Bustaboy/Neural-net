"""
Enhanced Model Trainer with ensemble learning, optimization, and monitoring
"""
import os
import pickle
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List, Optional
from multiprocessing import Process, Queue
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import psutil
import json

from ..core.database import EnhancedDatabaseManager
from ..utils.notifications import EnhancedNotificationManager
from .ensemble import create_ensemble_model
from .optimizer import BayesianOptimizer
from .features import FeatureEngineer
from .validator import CrossValidator


class EnhancedModelTrainer:
    """Advanced model trainer with ensemble learning and optimization"""
    
    def __init__(self, db_manager: EnhancedDatabaseManager, 
                 notification_manager: EnhancedNotificationManager,
                 config: Dict[str, Any]):
        self.db_manager = db_manager
        self.notification_manager = notification_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Model paths
        self.model_dir = "models"
        os.makedirs(self.model_dir, exist_ok=True)
        self.model_path = os.path.join(self.model_dir, "ensemble_model.pkl")
        self.scaler_path = os.path.join(self.model_dir, "scaler.pkl")
        self.temp_model_path = os.path.join(self.model_dir, "temp_ensemble_model.pkl")
        self.temp_scaler_path = os.path.join(self.model_dir, "temp_scaler.pkl")
        
        # Model components
        self.model = None
        self.scaler = StandardScaler()
        self.feature_engineer = FeatureEngineer(config)
        self.optimizer = BayesianOptimizer()
        self.validator = CrossValidator()
        
        # Training configuration
        self.min_samples = config.get('min_training_samples', 100)
        self.lookback_days = config.get('lookback_days', 30)
        self.retrain_interval_hours = config.get('retrain_frequency_hours', 24)
        self.volatility_threshold = config.get('volatility_retrain_threshold', 0.75)
        self.max_retries = config.get('max_training_retries', 3)
        
        # Resource monitoring
        self.max_memory_percent = config.get('max_memory_percent', 80)
        self.max_cpu_percent = config.get('max_cpu_percent', 90)
        
        # State management
        self.last_train_time = None
        self.training_in_progress = False
        self.training_queue = Queue()
        
    def prepare_data(self, lookback_days: int = 30) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare features and labels with enhanced feature engineering"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Use read-only connection for data preparation
            db_path = self.db_manager.db_path
            read_only_path = f"file:{db_path}?mode=ro"
            
            import sqlite3
            with sqlite3.connect(read_only_path, uri=True) as conn:
                conn.row_factory = sqlite3.Row
                
                # Query with proper indexing
                query = """
                    SELECT t.*, 
                           m.btc_price, m.btc_dominance, m.volatility_index, 
                           m.fear_greed_index, m.market_cap_total
                    FROM trades t
                    LEFT JOIN market_conditions m ON DATE(t.timestamp) = DATE(m.timestamp)
                    WHERE t.timestamp >= ? AND t.timestamp <= ?
                    ORDER BY t.timestamp
                """
                
                cursor = conn.cursor()
                cursor.execute(query, (start_date.isoformat(), end_date.isoformat()))
                trades = [dict(row) for row in cursor.fetchall()]
                
            if len(trades) < self.min_samples:
                self.logger.warning(f"Insufficient data: {len(trades)} samples, required {self.min_samples}")
                return None, None, []
                
            # Convert to DataFrame for feature engineering
            df = pd.DataFrame(trades)
            
            # Enhanced feature engineering
            features_df, feature_names = self.feature_engineer.create_features(df)
            
            # Handle outliers - clip at 1st and 99th percentiles
            for col in features_df.columns:
                if features_df[col].dtype in ['float64', 'int64']:
                    lower = features_df[col].quantile(0.01)
                    upper = features_df[col].quantile(0.99)
                    features_df[col] = features_df[col].clip(lower, upper)
            
            # Create labels
            df['label'] = (df['profit_loss'] > 0).astype(int)
            
            # Remove any rows with NaN values after feature engineering
            valid_mask = ~features_df.isnull().any(axis=1)
            features_df = features_df[valid_mask]
            labels = df.loc[valid_mask, 'label'].values
            
            self.logger.info(f"Prepared {len(features_df)} samples with {len(feature_names)} features")
            
            return features_df.values, labels, feature_names
            
        except Exception as e:
            self.logger.error(f"Error preparing data: {e}")
            return None, None, []
    
    def train_model(self, lookback_days: int = 30, reason: str = "Scheduled") -> bool:
        """Train model with retry logic and resource monitoring"""
        for attempt in range(self.max_retries):
            try:
                if self.training_in_progress:
                    self.logger.info("Training already in progress, skipping")
                    return False
                    
                # Check resource usage before training
                if not self._check_resources():
                    self.logger.warning("Insufficient resources for training")
                    return False
                    
                self.training_in_progress = True
                start_time = time.time()
                
                # Start training in separate process
                p = Process(target=self._train_process, 
                          args=(lookback_days, reason, self.training_queue))
                p.start()
                
                # Wait for completion with timeout
                p.join(timeout=3600)  # 1 hour timeout
                
                if p.is_alive():
                    self.logger.error("Training timeout, terminating process")
                    p.terminate()
                    p.join()
                    raise TimeoutError("Training exceeded time limit")
                
                # Get results from queue
                if not self.training_queue.empty():
                    result = self.training_queue.get()
                    if result['success']:
                        # Swap models atomically
                        self._swap_models()
                        
                        # Log training history
                        self._log_training_history(result, reason, time.time() - start_time)
                        
                        # Send notification
                        self.notification_manager.send_notification(
                            "Model Training Complete",
                            f"Model retrained ({reason}) with accuracy: {result['accuracy']:.2%}",
                            priority="normal"
                        )
                        
                        self.last_train_time = datetime.now()
                        return True
                    else:
                        raise Exception(result.get('error', 'Unknown error'))
                        
            except Exception as e:
                self.logger.error(f"Training attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    self.notification_manager.send_notification(
                        "Model Training Failed",
                        f"All {self.max_retries} training attempts failed. Last error: {str(e)}",
                        priority="high"
                    )
                    self.db_manager.log_system_event(
                        event_type="MODEL_TRAINING_ERROR",
                        message=f"Training failed after {self.max_retries} attempts: {str(e)}",
                        severity="ERROR",
                        component="ModelTrainer"
                    )
                else:
                    time.sleep(60 * (attempt + 1))  # Exponential backoff
                    
            finally:
                self.training_in_progress = False
                
        return False
    
    def _train_process(self, lookback_days: int, reason: str, result_queue: Queue):
        """Training process to run in separate process"""
        try:
            # Prepare data
            X, y, feature_names = self.prepare_data(lookback_days)
            if X is None:
                result_queue.put({'success': False, 'error': 'Insufficient data'})
                return
                
            # Split data with stratification
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Optimize hyperparameters
            best_params = self.optimizer.optimize(X_train_scaled, y_train, n_trials=50)
            
            # Create ensemble model with optimized parameters
            model = create_ensemble_model(best_params)
            
            # Cross-validation
            cv_scores = self.validator.validate(model, X_train_scaled, y_train, cv_folds=5)
            
            # Train final model
            model.fit(X_train_scaled, y_train)
            
            # Evaluate on test set
            y_pred = model.predict(X_test_scaled)
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred)
            recall = recall_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred)
            
            # Feature importance (if available)
            feature_importance = {}
            if hasattr(model, 'feature_importances_'):
                importance = model.feature_importances_
                feature_importance = dict(zip(feature_names, importance))
            elif hasattr(model, 'estimators_'):
                # For voting classifier, average importances
                importances = []
                for est_name, est in model.estimators_:
                    if hasattr(est, 'feature_importances_'):
                        importances.append(est.feature_importances_)
                if importances:
                    avg_importance = np.mean(importances, axis=0)
                    feature_importance = dict(zip(feature_names, avg_importance))
            
            # Save temporary models
            with open(self.temp_model_path, 'wb') as f:
                pickle.dump(model, f)
            with open(self.temp_scaler_path, 'wb') as f:
                pickle.dump(scaler, f)
                
            # Return results
            result_queue.put({
                'success': True,
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'cv_scores': cv_scores,
                'feature_importance': feature_importance,
                'hyperparameters': best_params,
                'samples_used': len(X)
            })
            
        except Exception as e:
            result_queue.put({'success': False, 'error': str(e)})
    
    def _swap_models(self):
        """Atomically swap temporary models to production"""
        try:
            if os.path.exists(self.temp_model_path) and os.path.exists(self.temp_scaler_path):
                # Load new models to verify
                with open(self.temp_model_path, 'rb') as f:
                    new_model = pickle.load(f)
                with open(self.temp_scaler_path, 'rb') as f:
                    new_scaler = pickle.load(f)
                
                # Atomic rename
                os.rename(self.temp_model_path, self.model_path)
                os.rename(self.temp_scaler_path, self.scaler_path)
                
                # Update in-memory models
                self.model = new_model
                self.scaler = new_scaler
                
                self.logger.info("Models swapped successfully")
                
        except Exception as e:
            self.logger.error(f"Error swapping models: {e}")
            raise
    
    def _check_resources(self) -> bool:
        """Check if system has sufficient resources for training"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            if memory.percent > self.max_memory_percent:
                self.logger.warning(f"Memory usage too high: {memory.percent}%")
                return False
                
            if cpu_percent > self.max_cpu_percent:
                self.logger.warning(f"CPU usage too high: {cpu_percent}%")
                return False
                
            # Check disk space
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                self.logger.warning(f"Disk usage too high: {disk.percent}%")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking resources: {e}")
            return True  # Allow training to proceed
    
    def _log_training_history(self, result: Dict, reason: str, duration: float):
        """Log training results to database"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO training_history 
                    (reason, accuracy, precision_score, recall_score, f1_score,
                     feature_importance, hyperparameters, training_duration, samples_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    reason,
                    result['accuracy'],
                    result['precision'],
                    result['recall'],
                    result['f1_score'],
                    json.dumps(result.get('feature_importance', {})),
                    json.dumps(result.get('hyperparameters', {})),
                    duration,
                    result.get('samples_used', 0)
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error logging training history: {e}")
    
    def should_retrain(self) -> Tuple[bool, str]:
        """Determine if retraining is needed based on multiple conditions"""
        try:
            # Time-based trigger
            if self.last_train_time is None:
                return True, "Initial training"
                
            time_since_last = datetime.now() - self.last_train_time
            if time_since_last > timedelta(hours=self.retrain_interval_hours):
                return True, "Scheduled retraining"
            
            # Market condition triggers
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check volatility
                cursor.execute("""
                    SELECT volatility_index
                    FROM market_conditions
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                row = cursor.fetchone()
                if row and row['volatility_index'] > self.volatility_threshold:
                    return True, f"High volatility detected ({row['volatility_index']:.2f})"
                
                # Check recent performance degradation
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades
                    FROM trades
                    WHERE timestamp >= datetime('now', '-1 day')
                """)
                row = cursor.fetchone()
                if row and row['total_trades'] > 10:
                    win_rate = row['winning_trades'] / row['total_trades']
                    if win_rate < 0.4:  # Less than 40% win rate
                        return True, f"Poor recent performance (win rate: {win_rate:.2%})"
                
                # Check for significant market events
                cursor.execute("""
                    SELECT COUNT(*) as event_count
                    FROM system_events
                    WHERE event_type = 'MARKET_ANOMALY'
                    AND timestamp >= datetime('now', '-6 hours')
                """)
                row = cursor.fetchone()
                if row and row['event_count'] > 5:
                    return True, "Multiple market anomalies detected"
                    
            return False, "No retraining needed"
            
        except Exception as e:
            self.logger.error(f"Error checking retrain conditions: {e}")
            return False, "Error checking conditions"
    
    def load_model(self) -> bool:
        """Load saved model and scaler"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                    
                self.logger.info("Model and scaler loaded successfully")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return False
    
    def predict(self, features: np.ndarray) -> Tuple[int, float]:
        """Make prediction with confidence score"""
        if self.model is None:
            raise ValueError("No model loaded")
            
        try:
            # Scale features
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            
            # Get prediction and probability
            prediction = self.model.predict(features_scaled)[0]
            probability = self.model.predict_proba(features_scaled)[0, 1]
            
            return prediction, probability
            
        except Exception as e:
            self.logger.error(f"Error making prediction: {e}")
            raise
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the current model"""
        if self.model is None:
            return {}
            
        try:
            # Implementation depends on model type
            if hasattr(self.model, 'feature_importances_'):
                return dict(enumerate(self.model.feature_importances_))
            else:
                return {}
                
        except Exception as e:
            self.logger.error(f"Error getting feature importance: {e}")
            return {}
    
    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status and history"""
        try:
            status = {
                'training_in_progress': self.training_in_progress,
                'last_train_time': self.last_train_time.isoformat() if self.last_train_time else None,
                'model_loaded': self.model is not None,
                'next_scheduled_training': None
            }
            
            if self.last_train_time:
                next_time = self.last_train_time + timedelta(hours=self.retrain_interval_hours)
                status['next_scheduled_training'] = next_time.isoformat()
            
            # Get recent training history
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, reason, accuracy, f1_score, training_duration
                    FROM training_history
                    ORDER BY timestamp DESC
                    LIMIT 10
                """)
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'timestamp': row['timestamp'],
                        'reason': row['reason'],
                        'accuracy': row['accuracy'],
                        'f1_score': row['f1_score'],
                        'duration': row['training_duration']
                    })
                    
                status['recent_history'] = history
                
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting training status: {e}")
            return {'error': str(e)}
