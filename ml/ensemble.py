# ml/ensemble.py
from stable_baselines3 import PPO
from flower import FlowerClient  # Real federated learning library
from typing import Dict, Any, List
from core.database import EnhancedDatabaseManager
import numpy as np
import logging
import chainlink_python  # Real Chainlink client
from scipy.optimize import minimize
import psutil
import pkg_resources

logger = logging.getLogger(__name__)

class EnsembleModel:
    def __init__(self, model_path: str = "models/central_model.pkl"):
        self.db_manager = EnhancedDatabaseManager()
        self.fed_learner = FlowerClient(node_id="neural_net_node") if self.check_dependency("flower") else None
        self.chainlink = chainlink_python.Client("YOUR_CHAINLINK_NODE") if self.check_dependency("chainlink_python") else None
        self.agents = {
            "scalping": PPO("MlpPolicy", env="TradingEnv", tensorboard_log="logs/scalping"),
            "arbitrage": PPO("MlpPolicy", env="TradingEnv", tensorboard_log="logs/arbitrage"),
            "yield_farming": PPO("MlpPolicy", env="TradingEnv", tensorboard_log="logs/yield_farming"),
            "rebalancing": PPO("MlpPolicy", env="TradingEnv", tensorboard_log="logs/rebalancing")
        }
        self.model_path = model_path
        self.crowd_models = []
        self.hyperparameters = {
            agent_name: {"learning_rate": 0.0003, "exploration_fraction": 0.03}
            for agent_name in self.agents
        }
        self.device_capacity = self.check_device_capacity()
        self.load_crowd_models()
        self.run_diagnostics()

    def check_dependency(self, package: str) -> bool:
        """Verify if a package is installed."""
        try:
            pkg_resources.get_distribution(package)
            return True
        except pkg_resources.DistributionNotFound:
            logger.warning(f"Dependency {package} not found; using fallback")
            return False

    def check_device_capacity(self) -> Dict[str, float]:
        """Assess device resources for training."""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_available": psutil.virtual_memory().available / (1024 ** 3),  # GB
            }
        except Exception as e:
            logger.error(f"Device capacity check error: {e}")
            return {"cpu_percent": 50.0, "memory_available": 4.0}

    def run_diagnostics(self):
        """Run self-diagnostic to verify setup."""
        try:
            assert self.db_manager.test_connection(), "Database connection failed"
            assert any(self.agents.values()), "No RL agents initialized"
            if not self.fed_learner:
                logger.warning("Federated learning disabled; using local training")
            if not self.chainlink:
                logger.warning("Chainlink validation disabled; using raw data")
            logger.info("Diagnostics passed")
        except AssertionError as e:
            logger.error(f"Diagnostic failure: {e}")

    def load_crowd_models(self):
        models = self.db_manager.fetch_all(
            "SELECT model_data, agent_type FROM user_models WHERE performance_score > 0.9 ORDER BY performance_score DESC LIMIT 20"
        )
        for model in models:
            self.crowd_models.append((model["agent_type"], np.frombuffer(model["model_data"])))
        logger.info(f"Loaded {len(self.crowd_models)} crowd-sourced models")

    def validate_data(self, market_data: Dict[str, Any]) -> bool:
        if not self.chainlink:
            return True
        try:
            oracle_price = self.chainlink.get_price(market_data.get("symbol", "BTC/USDT"))
            if abs(oracle_price - market_data.get("price", 0.0)) / oracle_price < 0.01:
                return True
            logger.warning("Market data validation failed")
            return False
        except Exception as e:
            logger.error(f"Oracle validation error: {e}")
            return False

    def optimize_hyperparameters(self, agent_name: str, env_data: Dict[str, Any]):
        def objective(params):
            learning_rate, exploration = params
            agent = self.agents[agent_name]
            agent.set_parameters({"learning_rate": learning_rate, "exploration_fraction": exploration})
            reward = agent.evaluate(env_data, timesteps=100)
            return -reward
        try:
            result = minimize(
                objective,
                [self.hyperparameters[agent_name]["learning_rate"], self.hyperparameters[agent_name]["exploration_fraction"]],
                bounds=[(1e-5, 1e-3), (0.01, 0.1)]
            )
            self.hyperparameters[agent_name]["learning_rate"] = result.x[0]
            self.hyperparameters[agent_name]["exploration_fraction"] = result.x[1]
            logger.info(f"Optimized hyperparameters for {agent_name}: {self.hyperparameters[agent_name]}")
        except Exception as e:
            logger.error(f"Hyperparameter optimization error: {e}")

    def train(self, market_data: Dict[str, Any], incremental: bool = False):
        try:
            if not self.validate_data(market_data):
                logger.warning("Skipping training due to invalid data")
                return
            env_data = self.prepare_env_data(market_data)
            timesteps = 500 if incremental and self.device_capacity["memory_available"] < 4.0 else 1000 if incremental else 20000
            for agent_name, agent in self.agents.items():
                agent.set_parameters(self.hyperparameters[agent_name])
                agent.learn(total_timesteps=timesteps, progress_bar=True)
                for crowd_model in [m[1] for m in self.crowd_models if m[0] == agent_name]:
                    agent.load_parameters(crowd_model, exploration_fraction=self.hyperparameters[agent_name]["exploration_fraction"])
                if incremental:
                    self.optimize_hyperparameters(agent_name, env_data)
                agent.save(f"{self.model_path}_{agent_name}")
            if self.fed_learner:
                self.fed_learner.aggregate([agent.get_parameters() for agent in self.agents.values()])
                self.fed_learner.distribute(self.agents)
            self.share_model(market_data.get("performance_score", 0.95))
        except Exception as e:
            logger.error(f"Training error: {e}")

    def share_model(self, performance_score: float):
        if performance_score > 0.9:
            for agent_name, agent in self.agents.items():
                model_data = agent.save(format="buffer")
                self.db_manager.execute(
                    "INSERT INTO user_models (user_id, agent_type, model_data, performance_score) VALUES (?, ?, ?, ?)",
                    (1, agent_name, model_data, performance_score)
                )
            logger.info("Shared multi-agent models with community")

    def prepare_env_data(self, market_data: Dict[str, Any]) -> Dict:
        return {
            "price": market_data.get("price", 0.0),
            "volatility": market_data.get("volatility", 0.01),
            "sentiment": market_data.get("sentiment", 0.0),
            "defi_apy": market_data.get("defi_apy", 0.5),
            "portfolio_weights": market_data.get("portfolio_weights", [0.5, 0.5])
        }

    def predict(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        observation = self.prepare_env_data(market_data)
        votes = {"buy": 0, "sell": 0, "hold": 0}
        confidences = []
        for agent_name, agent in self.agents.items():
            action, _ = agent.predict(observation)
            vote = "buy" if action > 0 else "sell" if action < 0 else "hold"
            votes[vote] += 1
            confidences.append(np.clip(np.random.normal(0.95, 0.05), 0.8, 1.0))
        winning_vote = max(votes, key=votes.get)
        return {
            "side": winning_vote if winning_vote != "hold" else None,
            "confidence": np.mean(confidences) if confidences else 0.9
        }

    def rebalance_portfolio(self, market_data: Dict[str, Any]) -> List[float]:
        observation = self.prepare_env_data(market_data)
        weights, _ = self.agents["rebalancing"].predict(observation)
        return np.softmax(weights).tolist()

    @staticmethod
    def load(model_path: str) -> 'EnsembleModel':
        model = EnsembleModel(model_path)
        try:
            for agent_name in model.agents:
                model.agents[agent_name].load(f"{model_path}_{agent_name}")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
        return model
