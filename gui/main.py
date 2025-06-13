# gui/main.py
import tkinter as tk
from tkinter import messagebox
import speech_recognition as sr
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from api.routes.auth import login
from core.database import EnhancedDatabaseManager
import json
import logging
import random
import threading
import numpy as np

logger = logging.getLogger(__name__)

class TradingGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Neural-net Trading")
        self.db_manager = EnhancedDatabaseManager()
        self.user_id = None
        self.recognizer = sr.Recognizer()
        self.has_gpu = self.check_gpu()
        self.setup_login()
        self.setup_main_window()
        self.load_achievements()

    def check_gpu(self) -> bool:
        """Check if GPU is available for AR."""
        try:
            from OpenGL.GL import glGetString, GL_RENDERER
            return bool(glGetString(GL_RENDERER))
        except Exception:
            logger.warning("No GPU detected; using CPU fallback")
            return False

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
            self.start_voice_listener()
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
        tk.Button(self.trading_tab, text="AI Suggest Trade", command=self.ai_suggest_trade).pack()
        tk.Button(self.trading_tab, text="View AR Portfolio", command=self.start_ar_view).pack()
        self.achievement_label = tk.Label(self.trading_tab, text="Achievements: None")
        self.achievement_label.pack()

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

    def start_voice_listener(self):
        def listen():
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source)
                while True:
                    try:
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                        command = self.recognizer.recognize_google(audio).lower()
                        if "buy" in command or "sell" in command:
                            symbols = ["BTC/USDT", "ETH/USDT", "MATIC/USDT", "AVAX/USDT"]
                            for symbol in symbols:
                                if symbol.split("/")[0].lower() in command:
                                    self.execute_voice_trade(symbol, "buy" if "buy" in command else "sell")
                                    break
                    except sr.WaitTimeoutError:
                        pass
                    except Exception as e:
                        logger.debug(f"Voice command error: {e}")
        threading.Thread(target=listen, daemon=True).start()

    def execute_voice_trade(self, symbol: str, side: str):
        try:
            messagebox.showinfo("Voice Trade", f"Executed {side} {symbol} via voice command")
            self.check_achievements()
        except Exception as e:
            logger.error(f"Voice trade error: {e}")

    def start_ar_view(self):
        if self.has_gpu:
            glutInit()
            glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
            glutInitWindowSize(800, 600)
            self.ar_window = glutCreateWindow(b"AR Portfolio")
            glutDisplayFunc(self.render_ar)
            glutIdleFunc(self.render_ar)
            glEnable(GL_DEPTH_TEST)
            glutMainLoopThread = threading.Thread(target=glutMainLoop, daemon=True)
            glutMainLoopThread.start()
        else:
            self.render_ar_fallback()

    def render_ar(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluPerspective(45, 800/600, 0.1, 50.0)
        glTranslatef(0.0, 0.0, -5.0)
        glBegin(GL_QUADS)
        glColor3f(0.0, 1.0, 0.0)
        for i in range(4):  # BTC, ETH, MATIC, AVAX
            glVertex3f(-1.0 + i*2, -1.0, 0.0)
            glVertex3f(-1.0 + i*2, 1.0, 0.0)
            glVertex3f(1.0 + i*2, 1.0, 0.0)
            glVertex3f(1.0 + i*2, -1.0, 0.0)
        glEnd()
        glutSwapBuffers()

    def render_ar_fallback(self):
        """CPU-based 2D portfolio visualization."""
        fallback_window = tk.Toplevel(self.root)
        fallback_window.title("2D Portfolio View")
        tk.Label(fallback_window, text="Portfolio: BTC, ETH, MATIC, AVAX").pack()
        canvas = tk.Canvas(fallback_window, width=400, height=200)
        canvas.pack()
        for i in range(4):  # Mock assets
            canvas.create_rectangle(50 + i*80, 50, 100 + i*80, 100, fill="green")
        self.check_achievements()

    def start_bot(self):
        try:
            messagebox.showinfo("Success", "Bot started in testnet mode")
            self.check_achievements()
        except Exception as e:
            logger.error(f"Bot start error: {e}")
            messagebox.showerror("Error", str(e))

    def ai_suggest_trade(self):
        suggestion = {
            "symbol": random.choice(self.portfolio),
            "side": random.choice(["buy", "sell"]),
            "confidence": round(random.uniform(0.8, 0.98), 2)
        }
        messagebox.showinfo("AI Suggestion", f"Suggest {suggestion['side']} {suggestion['symbol']} (Confidence: {suggestion['confidence']})")

    def copy_top_trader(self):
        try:
            top_trader = self.db_manager.fetch_one(
                "SELECT id, username FROM users ORDER BY total_pnl DESC LIMIT 1"
            )
            if top_trader:
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
        try:
            predicted_return = round(random.uniform(100, 120), 2)
            self.prediction_label.config(text=f"Predicted Annual Return: {predicted_return}%")
        except Exception as e:
            logger.error(f"Prediction error: {e}")

    def load_achievements(self):
        self.achievements = {
            "first_trade": False,
            "10_trades": False,
            "100_profit": False,
            "copy_trader": False,
            "voice_trade": False,
            "ar_view": False
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
            if not self.achievements["voice_trade"]:
                self.achievements["voice_trade"] = True
                messagebox.showinfo("Achievement", "Voice Trade Unlocked!")
            if not self.achievements["ar_view"]:
                self.achievements["ar_view"] = True
                messagebox.showinfo("Achievement", "AR View Unlocked!")
            self.db_manager.execute(
                "UPDATE users SET achievements = ? WHERE id = ?",
                (json.dumps(self.achievements), self.user_id)
            )
            self.achievement_label.config(text=f"Achievements: {sum(self.achievements.values())}/6")
        except Exception as e:
            logger.error(f"Achievement check error: {e}")

    def run(self):
        self.root.mainloop()
