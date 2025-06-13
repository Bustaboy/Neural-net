# utils/notifications.py
import telegram
from typing import Dict, Any
import asyncio
import logging
import json
from web3 import Web3

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.bot = telegram.Bot(token="YOUR_TELEGRAM_BOT_TOKEN")
        self.sharded_channels = {
            0: "@NeuralNetTrading0",
            1: "@NeuralNetTrading1"
        }
        self.db_manager = EnhancedDatabaseManager()
        self.w3 = Web3(Web3.HTTPProvider("YOUR_ETHEREUM_NODE"))
        self.token_contract = self.w3.eth.contract(
            address="0xYOUR_TOKEN_ADDRESS",
            abi=[{"function": "transfer", "inputs": [{"type": "address"}, {"type": "uint256"}]}]
        )
        self.nft_contract = self.w3.eth.contract(
            address="0xYOUR_NFT_ADDRESS",
            abi=[{"function": "mint", "inputs": [{"type": "uint256"}, {"type": "string"}]}]
        )
        self.batch_transactions = []

    async def send_notification(self, user_id: int, message: str):
        try:
            shard_id = user_id % len(self.sharded_channels)
            await self.bot.send_message(chat_id=user_id, text=message)
            if "Achievement" in message or "Profit" in message:
                await self.bot.send_message(
                    chat_id=self.sharded_channels[shard_id],
                    text=f"User {user_id} achieved: {message}"
                )
                await self.queue_token_award(user_id, 20)
                await self.queue_nft_mint(user_id)
            logger.info(f"Sent notification: {message}")
        except Exception as e:
            logger.error(f"Notification error: {e}")

    async def notify_trade(self, user_id: int, trade: Dict[str, Any]):
        message = f"Trade executed: {trade['side']} {trade['quantity']} {trade['symbol']} at ${trade['price']}"
        await self.send_notification(user_id, message)

    async def queue_token_award(self, user_id: int, amount: int):
        try:
            user_address = self.db_manager.fetch_one(
                "SELECT eth_address FROM users WHERE id = ?", (user_id,)
            )["eth_address"]
            self.batch_transactions.append({
                "type": "token",
                "user_id": user_id,
                "address": user_address,
                "amount": amount
            })
            if len(self.batch_transactions) >= 100:  # Batch size
                await self.process_batch_transactions()
        except Exception as e:
            logger.error(f"Token award queue error: {e}")

    async def queue_nft_mint(self, user_id: int):
        try:
            user_address = self.db_manager.fetch_one(
                "SELECT eth_address FROM users WHERE id = ?", (user_id,)
            )["eth_address"]
            self.batch_transactions.append({
                "type": "nft",
                "user_id": user_id,
                "address": user_address
            })
            if len(self.batch_transactions) >= 100:
                await self.process_batch_transactions()
        except Exception as e:
            logger.error(f"NFT mint queue error: {e}")

    async def process_batch_transactions(self):
        try:
            for tx in self.batch_transactions:
                if tx["type"] == "token":
                    self.db_manager.execute(
                        "UPDATE users SET token_balance = token_balance + ? WHERE id = ?",
                        (tx["amount"], tx["user_id"])
                    )
                    logger.info(f"Mock token transfer: {tx['amount']} to {tx['address']}")
                    await self.bot.send_message(
                        chat_id=tx["user_id"],
                        text=f"Awarded {tx['amount']} NEURAL tokens for your contribution!"
                    )
                elif tx["type"] == "nft":
                    logger.info(f"Mock NFT mint for user {tx['user_id']}")
                    await self.bot.send_message(
                        chat_id=tx["user_id"],
                        text="Minted Strategy NFT for your trading success!"
                    )
            self.batch_transactions.clear()
            logger.info("Processed batch transactions")
        except Exception as e:
            logger.error(f"Batch transaction error: {e}")

    async def vote_on_proposal(self, user_id: int, proposal_id: int, vote: bool):
        try:
            user_address = self.db_manager.fetch_one(
                "SELECT eth_address FROM users WHERE id = ?", (user_id,)
            )["eth_address"]
            logger.info(f"Mock vote: User {user_id} voted {'for' if vote else 'against'} proposal {proposal_id}")
            await self.bot.send_message(
                chat_id=user_id,
                text=f"Voted {'for' if vote else 'against'} proposal {proposal_id}"
            )
            logger.info(f"User {user_id} voted on proposal {proposal_id}")
        except Exception as e:
            logger.error(f"Governance vote error: {e}")
