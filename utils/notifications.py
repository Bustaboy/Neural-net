# utils/notifications.py
import telegram
from typing import Dict, Any
import asyncio
import logging
import json

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.bot = telegram.Bot(token="YOUR_TELEGRAM_BOT_TOKEN")  # Replace with actual token
        self.sharded_channels = {
            0: "@NeuralNetTrading0",  # Replace with actual chat IDs
            1: "@NeuralNetTrading1"
        }
        self.db_manager = EnhancedDatabaseManager()
        self.mock_contract = {"tokens": {}, "nfts": {}, "proposals": {}}

    async def send_notification(self, user_id: int, message: str):
        try:
            shard_id = user_id % len(self.sharded_channels)
            await self.bot.send_message(chat_id=user_id, text=message)
            if "Achievement" in message or "Profit" in message:
                await self.bot.send_message(
                    chat_id=self.sharded_channels[shard_id],
                    text=f"User {user_id} achieved: {message}"
                )
                await self.award_tokens(user_id, 20)
                await self.mint_strategy_nft(user_id)
            logger.info(f"Sent notification: {message}")
        except Exception as e:
            logger.error(f"Notification error: {e}")

    async def notify_trade(self, user_id: int, trade: Dict[str, Any]):
        message = f"Trade executed: {trade['side']} {trade['quantity']} {trade['symbol']} at ${trade['price']}"
        await self.send_notification(user_id, message)

    async def award_tokens(self, user_id: int, amount: int):
        try:
            self.db_manager.execute(
                "UPDATE users SET token_balance = token_balance + ? WHERE id = ?",
                (amount, user_id)
            )
            self.mock_contract["tokens"][user_id] = self.mock_contract["tokens"].get(user_id, 0) + amount
            if sum(self.mock_contract["tokens"].values()) > 1000000:  # Vesting cap
                amount = max(0, amount - (sum(self.mock_contract["tokens"].values()) - 1000000))
            await self.bot.send_message(
                chat_id=user_id,
                text=f"Awarded {amount} NEURAL tokens for your contribution!"
            )
            logger.info(f"Awarded {amount} tokens to user {user_id}")
        except Exception as e:
            logger.error(f"Token award error: {e}")

    async def mint_strategy_nft(self, user_id: int):
        try:
            nft_id = len(self.mock_contract["nfts"])
            self.mock_contract["nfts"][nft_id] = {"owner": user_id, "strategy": "MockStrategy"}
            await self.bot.send_message(
                chat_id=user_id,
                text=f"Minted Strategy NFT #{nft_id} for your trading success!"
            )
            logger.info(f"Minted Strategy NFT for user {user_id}")
        except Exception as e:
            logger.error(f"NFT mint error: {e}")

    async def vote_on_proposal(self, user_id: int, proposal_id: int, vote: bool):
        try:
            if proposal_id not in self.mock_contract["proposals"]:
                self.mock_contract["proposals"][proposal_id] = {"yes": 0, "no": 0}
            self.mock_contract["proposals"][proposal_id]["yes" if vote else "no"] += self.mock_contract["tokens"].get(user_id, 0)
            await self.bot.send_message(
                chat_id=user_id,
                text=f"Voted {'for' if vote else 'against'} proposal {proposal_id}"
            )
            logger.info(f"User {user_id} voted on proposal {proposal_id}")
        except Exception as e:
            logger.error(f"Governance vote error: {e}")
