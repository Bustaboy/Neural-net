# gui/main.py
import tkinter as tk
from tkinter import messagebox
from api.routes.auth import login
from core.database import EnhancedDatabaseManager
import json
import logging
import random

logger = logging.getLogger(__name__)

class TradingGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Neural-net Trading")
        self.db_manager = EnhancedDatabaseManager()
        self.user_id = None
        self.setup_login()
        self.setup_main_window()
        self.load_achievements()

    def setup_login(self):
        self.login_frame = tk.Frame(self.root)
        self.login_frame.pack()
        tk.Label(self.login_frame, text="Username").pack()
        self.username_entry = tk.Entry(self.login_frame)
        self.username_entry.pack()
        tk.Label(self.login_frame, text="Password").pack()
        self.password_entry = tk.Entry(self.login_frame, show="*")
        self.password_entry.pack()
        tk.Button(self.login_frame, text="Login", command=self.handle_login).pack()

    def handle_login(self):
        try:
            response = login({
                "username": self.username_entry.get(),
                "password": self.password_entry.get()
            })
            self.user_id = response["user_id"]
            self.login_frame.destroy()
            self.main_frame.pack()
            self.update_leaderboard()
            self.update_predictions()
        except Exception as e:
            messagebox.showerror("Login Failed", str(e))

    def setup_main_window(self):
        self.main_frame = tk.Frame(self.root)
        self.tabs = tk.Notebook(self.main_frame)
        self.trading_tab = tk.Frame(self.tabs)
        self.portfolio_tab = tk.Frame(self.tabs)
        self.leaderboard_tab = tk.Frame(self.tabs)
        self.prediction_tab = tk.Frame(self.tabs)
        self.social_tab = tk.Frame(self.tabs)
        self.tabs.add(self.trading_tab, text="Trading")
        self.tabs.add(self.portfolio_tab, text="Portfolio")
        self.tabs.add(self.leaderboard_tab, text="Leaderboard")
        self.tabs.add(self.prediction_tab, text="Predictions")
        self.tabs.add(self.social_tab, text="Social Trading")
        self.tabs.pack()

        # Trading Tab
        tk.Button(self.trading_tab, text="Start Bot", command=self.start_bot).pack()
        self.achievement_label = tk.Label(self.trading_tab, text="Achievements: None")
        self.achievement_label.pack()
        tk.Button(self.trading_tab, text="AI Suggest Trade", command=self.ai_suggest_trade).pack()

        # Leaderboard Tab
        self.leaderboard_list = tk.Listbox(self.leaderboard_tab, width=50)
        self.leaderboard_list.pack()

        # Prediction Tab
        self.prediction_label = tk.Label(self.prediction_tab, text="Loading predictions...")
        self.prediction_label.pack()

        # Social Trading Tab
        self.social_list = tk.Listbox(self.social_tab, width=50)
        self.social_list.pack()
        tk.Button(self.social_tab, text="Copy Top Trader", command=self.copy_top_trader).pack()

    def start_bot(self):
        try:
            messagebox.showinfo("Success", "Bot started in testnet mode")
            self.check_achievements()
        except Exception as e:
            logger.error(f"Bot start error: {e}")
            messagebox.showerror("Error", str(e))

    def ai_suggest_trade(self):
        """Provide AI-driven trade suggestion."""
        try:
            # Placeholder: Call ML model
            suggestion = {
                "symbol": "BTC/USDT",
                "side": random.choice(["buy", "sell"]),
                "confidence": round(random.uniform(0.7, 0.95), 2)
            }
            messagebox.showinfo("AI Suggestion", f"Suggest {suggestion['side']} {suggestion['symbol']} (Confidence: {suggestion['confidence']})")
        except Exception as e:
            logger.error(f"AI suggestion error: {e}")

    def copy_top_trader(self):
        """Copy strategy of top trader."""
        try:
            top_trader = self.db_manager.fetch_one(
                "SELECT id, username FROM users ORDER BY total_pnl DESC LIMIT 1"
            )
            if top_trader:
                # Placeholder: Copy strategy
                messagebox.showinfo("Success", f"Copied strategy from {top_trader['username']}")
                self.check_achievements()
        except Exception as e:
            logger.error(f"Copy trader error: {e}")

    def update_leaderboard(self):
        try:
            leaders = self.db_manager.fetch_all(
                "SELECT username, total_pnl FROM users ORDER BY total_pnl DESC LIMIT 10"
            )
            self.leaderboard_list.delete(0, tk.END)
            for i, leader in enumerate(leaders, 1):
                self.leaderboard_list.insert(tk.END, f"{i}. {leader['username']} - ${leader['total_pnl']:.2f}")
        except Exception as e:
            logger.error(f"Leaderboard error: {e}")

    def update_predictions(self):
        """Update predictive dashboard."""
        try:
            # Placeholder: Fetch RL predictions
            predicted_return = round(random.uniform(60, 100), 2)
            self.prediction_label.config(text=f"Predicted Annual Return: {predicted_return}%")
        except Exception as e:
            logger.error(f"Prediction error: {e}")

    def load_achievements(self):
        self.achievements = {
            "first_trade": False,
            "10_trades": False,
            "100_profit": False,
            "copy_trader": False
        }
        try:
            user_data = self.db_manager.fetch_one(
                "SELECT achievements FROM users WHERE id = ?", (self.user_id,)
            )
            if user_data and user_data["achievements"]:
                self.achievements.update(json.loads(user_data["achievements"]))
        except Exception as e:
            logger.error(f"Achievement load error: {e}")

    def check_achievements(self):
        try:
            trades = self.db_manager.fetch_one(
                "SELECT COUNT(*) as count, SUM(pnl) as total_pnl FROM trades WHERE user_id = ?",
                (self.user_id,)
            )
            if trades["count"] >= 1 and not self.achievements["first_trade"]:
                self.achievements["first_trade"] = True
                messagebox.showinfo("Achievement", "First Trade Unlocked!")
            if trades["count"] >= 10 and not self.achievements["10_trades"]:
                self.achievements["10_trades"] = True
                messagebox.showinfo("Achievement", "10 Trades Unlocked!")
            if trades["total_pnl"] >= 100 and not self.achievements["100_profit"]:
                self.achievements["100_profit"] = True
                messagebox.showinfo("Achievement", "$100 Profit Unlocked!")
            if not self.achievements["copy_trader"]:
                self.achievements["copy_trader"] = True
                messagebox.showinfo("Achievement", "Copy Trader Unlocked!")
            self.db_manager.execute(
                "UPDATE users SET achievements = ? WHERE id = ?",
                (json.dumps(self.achievements), self.user_id)
            )
            self.achievement_label.config(text=f"Achievements: {sum(self.achievements.values())}/4")
        except Exception as e:
            logger.error(f"Achievement check error: {e}")

    def run(self):
        self.root.mainloop()
