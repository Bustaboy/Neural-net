# ml/ensemble.py
from stable_baselines3 import PPO
from typing import Dict, Any, List
from core.database import EnhancedDatabaseManager
import numpy as np
import logging

logger = logging.getLogger(__name__)

class EnsembleModel:
    def __init__(self, model_path: str = "models/central_model.pkl"):
        self.db_manager = EnhancedDatabaseManager()
        self.agents = {
            "scalping": PPO("MlpPolicy", env="TradingEnv", tensorboard_log="logs/scalping"),
            "arbitrage": PPO("MlpPolicy", env="TradingEnv", tensorboard_log="logs/arbitrage"),
            "yield_farming": PPO("MlpPolicy", env="TradingEnv", tensorboard_log="logs/yield_farming")
        }
        self.model_path = model_path
        self.crowd_models = []
        self.load_crowd_models()

    def load_crowd_models(self):
        """Load top-performing community models."""
        models = self.db_manager.fetch_all(
            "SELECT model_data, agent_type FROM user_models WHERE performance_score > 0.85 ORDER BY performance_score DESC LIMIT 10"
        )
        for model in models:
            self.crowd_models.append((model["agent_type"], np.frombuffer(model["model_data"])))
        logger.info(f"Loaded {len(self.crowd_models)} crowd-sourced models")

    def train(self, market_data: Dict[str, Any]):
        """Train multi-agent RL with real-time feedback."""
        try:
            env_data = self.prepare_env_data(market_data)
            for agent_name, agent in self.agents.items():
                agent.learn(total_timesteps=15000, progress_bar=True)
                for crowd_model in [m[1] for m in self.crowd_models if m[0] == agent_name]:
                    agent.load_parameters(crowd_model, exploration_fraction=0.05)
                agent.save(f"{self.model_path}_{agent_name}")
            self.share_model(market_data.get("performance_score", 0.9))
        except Exception as e:
            logger.error(f"Training error: {e}")

    def share_model(self, performance_score: float):
        """Share high-performing models with community."""
        if performance_score > 0.85:
            for agent_name, agent in self.agents.items():
                model_data = agent.save(format="buffer")
                self.db_manager.execute(
                    "INSERT INTO user_models (user_id, agent_type, model_data, performance_score) VALUES (?, ?, ?, ?)",
                    (1, agent_name, model_data, performance_score)
                )
            logger.info("Shared multi-agent models with community")

    def prepare_env_data(self, market_data: Dict[str, Any]) -> Dict:
        """Prepare data for RL environment, including DeFi metrics."""
        return {
            "price": market_data.get("price", 0.0),
            "volatility": market_data.get("volatility", 0.01),
            "sentiment": market_data.get("sentiment", 0.0),
            "defi_apy": market_data.get("defi_apy", 0.5)  # Example APY from Uniswap
        }

    def predict(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Combine predictions from multiple agents."""
        observation = self.prepare_env_data(market_data)
        votes = {"buy": 0, "sell": 0, "hold": 0}
        confidences = []
        for agent_name, agent in self.agents.items():
            action, _ = agent.predict(observation)
            vote = "buy" if action > 0 else "sell" if action < 0 else "hold"
            votes[vote] += 1
            confidences.append(np.clip(np.random.normal(0.9, 0.1), 0.7, 1.0))
        winning_vote = max(votes, key=votes.get)
        return {
            "side": winning_vote if winning_vote != "hold" else None,
            "confidence": np.mean(confidences) if confidences else 0.8
        }

    @staticmethod
    def load(model_path: str) -> 'EnsembleModel':
        model = EnsembleModel(model_path)
        try:
            for agent_name in model.agents:
                model.agents[agent_name].load(f"{model_path}_{agent_name}")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
        return model
