import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import websocket
import threading
import os
from pathlib import Path

class NeuralNetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Neural-net Trading App")
        self.root.geometry("800x600")

        # API and WebSocket settings
        self.api_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000/ws"
        self.token = None
        self.config_file = Path("config.json")

        # Load or prompt for API keys
        self.load_config()

        # Create notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, expand=True)

        # Trading tab
        self.trading_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.trading_frame, text="Trading")
        self.setup_trading_tab()

        # Portfolio tab
        self.portfolio_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.portfolio_frame, text="Portfolio")
        self.setup_portfolio_tab()

        # Market Data tab
        self.market_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.market_frame, text="Market Data")
        self.setup_market_tab()

        # Settings tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        self.setup_settings_tab()

        # Start WebSocket for live updates
        self.start_websocket()

    def load_config(self):
        """Load or prompt for API keys and save to config.json."""
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                config = json.load(f)
                self.market_api_key = config.get("market_api_key", "")
                self.exchange_api_key = config.get("exchange_api_key", "")
                self.exchange_secret = config.get("exchange_secret", "")
        else:
            self.market_api_key = ""
            self.exchange_api_key = ""
            self.exchange_secret = ""
            self.save_config()

    def save_config(self):
        """Save API keys to config.json."""
        config = {
            "market_api_key": self.market_api_key,
            "exchange_api_key": self.exchange_api_key,
            "exchange_secret": self.exchange_secret
        }
        with open(self.config_file, "w") as f:
            json.dump(config, f)

    def setup_trading_tab(self):
        """Set up the trading interface."""
        tk.Label(self.trading_frame, text="Trading Dashboard").pack(pady=10)

        # Symbol input
        tk.Label(self.trading_frame, text="Symbol (e.g., BTC):").pack()
        self.symbol_entry = tk.Entry(self.trading_frame)
        self.symbol_entry.pack()
        self.symbol_entry.insert(0, "BTC")

        # Amount input
        tk.Label(self.trading_frame, text="Amount (e.g., 0.01):").pack()
        self.amount_entry = tk.Entry(self.trading_frame)
        self.amount_entry.pack()
        self.amount_entry.insert(0, "0.01")

        # Buy/Sell buttons
        tk.Button(self.trading_frame, text="Buy", command=lambda: self.make_trade("buy")).pack(pady=5)
        tk.Button(self.trading_frame, text="Sell", command=lambda: self.make_trade("sell")).pack(pady=5)

        # Status label
        self.trade_status = tk.Label(self.trading_frame, text="Ready to trade")
        self.trade_status.pack(pady=10)

    def setup_portfolio_tab(self):
        """Set up the portfolio interface."""
        tk.Label(self.portfolio_frame, text="Your Portfolio").pack(pady=10)
        self.portfolio_text = tk.Text(self.portfolio_frame, height=10, width=50)
        self.portfolio_text.pack()
        tk.Button(self.portfolio_frame, text="Refresh", command=self.update_portfolio).pack(pady=5)
        self.update_portfolio()

    def setup_market_tab(self):
        """Set up the market data interface."""
        tk.Label(self.market_frame, text="Market Data").pack(pady=10)
        self.market_text = tk.Text(self.market_frame, height=10, width=50)
        self.market_text.pack()

    def setup_settings_tab(self):
        """Set up the settings interface."""
        tk.Label(self.settings_frame, text="Settings").pack(pady=10)

        # Market API key
        tk.Label(self.settings_frame, text="Alpha Vantage API Key:").pack()
        self.market_api_entry = tk.Entry(self.settings_frame)
        self.market_api_entry.pack()
        self.market_api_entry.insert(0, self.market_api_key)

        # Exchange API key
        tk.Label(self.settings_frame, text="Exchange API Key (Binance/Coinbase):").pack()
        self.exchange_api_entry = tk.Entry(self.settings_frame)
        self.exchange_api_entry.pack()
        self.exchange_api_entry.insert(0, self.exchange_api_key)

        # Exchange secret
        tk.Label(self.settings_frame, text="Exchange Secret:").pack()
        self.exchange_secret_entry = tk.Entry(self.settings_frame)
        self.exchange_secret_entry.pack()
        self.exchange_secret_entry.insert(0, self.exchange_secret)

        tk.Button(self.settings_frame, text="Save Settings", command=self.save_settings).pack(pady=10)

    def save_settings(self):
        """Save API keys from settings tab."""
        self.market_api_key = self.market_api_entry.get()
        self.exchange_api_key = self.exchange_api_entry.get()
        self.exchange_secret = self.exchange_secret_entry.get()
        self.save_config()
        messagebox.showinfo("Success", "Settings saved!")

    def login(self):
        """Log in to get an access token (simplified for single user)."""
        try:
            response = requests.post(f"{self.api_url}/auth/login", json={"username": "user", "password": "password"})
            if response.status_code == 200:
                self.token = response.json().get("access_token")
            else:
                messagebox.showerror("Error", "Login failed. Check backend is running.")
        except requests.RequestException:
            messagebox.showerror("Error", "Cannot connect to backend. Ensure app is running.")

    def make_trade(self, trade_type):
        """Send a trade request to the backend."""
        if not self.token:
            self.login()
        symbol = self.symbol_entry.get()
        amount = self.amount_entry.get()
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"symbol": symbol, "amount": float(amount), "type": trade_type}
        try:
            response = requests.post(f"{self.api_url}/trading/trade", json=payload, headers=headers)
            if response.status_code == 200:
                self.trade_status.config(text=f"{trade_type.capitalize()} successful: {response.json()['trade_id']}")
            else:
                self.trade_status.config(text=f"Error: {response.json().get('detail', 'Trade failed')}")
        except requests.RequestException:
            self.trade_status.config(text="Error: Cannot connect to backend.")

    def update_portfolio(self):
        """Fetch and display portfolio data."""
        if not self.token:
            self.login()
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(f"{self.api_url}/portfolio", headers=headers)
            if response.status_code == 200:
                portfolio = response.json()
                self.portfolio_text.delete(1.0, tk.END)
                self.portfolio_text.insert(tk.END, f"Cash: ${portfolio['cash']:.2f}\n")
                for asset in portfolio['assets']:
                    self.portfolio_text.insert(tk.END, f"{asset['name']}: ${asset['value']:.2f}\n")
            else:
                self.portfolio_text.delete(1.0, tk.END)
                self.portfolio_text.insert(tk.END, "Error fetching portfolio.")
        except requests.RequestException:
            self.portfolio_text.delete(1.0, tk.END)
            self.portfolio_text.insert(tk.END, "Error: Cannot connect to backend.")

    def on_websocket_message(self, ws, message):
        """Handle WebSocket market data updates."""
        try:
            data = json.loads(message)
            if data.get("type") == "market_update":
                self.market_text.delete(1.0, tk.END)
                self.market_text.insert(tk.END, f"{data['data']['symbol']}: ${data['data']['price']:.2f} ({data['data']['change']:+.2f}%)\n")
        except json.JSONDecodeError:
            pass

    def start_websocket(self):
        """Start WebSocket connection in a separate thread."""
        def run_websocket():
            ws = websocket.WebSocketApp(self.ws_url, on_message=self.on_websocket_message)
            ws.run_forever()

        threading.Thread(target=run_websocket, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = NeuralNetApp(root)
    root.mainloop()
