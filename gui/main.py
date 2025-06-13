import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import websocket
import threading
import subprocess

class NeuralNetApp:
    def __init__(self, root):
        """Initialize the app with a login window."""
        self.root = root
        self.root.title("Neural-net Trading App")
        self.root.geometry("800x600")  # Set main window size
        self.api_url = "http://localhost:8000"  # Backend API address
        self.ws_url = "ws://localhost:8000/ws"  # WebSocket address
        self.token = None  # User authentication token
        self.user_id = None  # User ID for multi-user support
        self.show_login_window()  # Start with login screen

    def show_login_window(self):
        """Display a login window for user authentication or registration."""
        self.login_window = tk.Toplevel(self.root)
        self.login_window.title("Login to Neural-net")
        self.login_window.geometry("300x250")  # Fixed size for login window
        self.login_window.resizable(False, False)  # Prevent resizing

        # Welcome message
        tk.Label(self.login_window, text="Welcome! Log in or register", font=("Arial", 12)).pack(pady=10)
        
        # Username input
        tk.Label(self.login_window, text="Username:").pack(pady=5)
        self.username_entry = tk.Entry(self.login_window, width=20)
        self.username_entry.pack()
        
        # Password input
        tk.Label(self.login_window, text="Password:").pack(pady=5)
        self.password_entry = tk.Entry(self.login_window, show="*", width=20)  # Hide password
        self.password_entry.pack()
        
        # Login and Register buttons
        tk.Button(self.login_window, text="Login", command=self.login, width=10).pack(pady=10)
        tk.Button(self.login_window, text="Register", command=self.register, width=10).pack(pady=5)

    def login(self):
        """Log in by calling the backend's /auth/login API."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password.", parent=self.login_window)
            return
        try:
            response = requests.post(
                f"{self.api_url}/auth/login",
                json={"username": username, "password": password},
                timeout=5  # Wait up to 5 seconds
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.user_id = data.get("user_id")
                if not self.user_id:
                    messagebox.showerror("Error", "Login failed: No user ID returned.", parent=self.login_window)
                    return
                self.login_window.destroy()  # Close login window
                self.setup_main_gui()  # Open main GUI
            else:
                messagebox.showerror("Error", "Invalid username or password. Try again.", parent=self.login_window)
        except requests.RequestException:
            messagebox.showerror(
                "Error",
                "Cannot connect to the app. Make sure the app is running (start_app.py).",
                parent=self.login_window
            )

    def register(self):
        """Register a new user by calling /auth/register."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password.", parent=self.login_window)
            return
        try:
            response = requests.post(
                f"{self.api_url}/auth/register",
                json={"username": username, "password": password},
                timeout=5
            )
            if response.status_code == 201:
                messagebox.showinfo(
                    "Success",
                    "Account created! Log in with your new username and password.",
                    parent=self.login_window
                )
            else:
                error = response.json().get("detail", "Registration failed.")
                messagebox.showerror("Error", f"Failed to register: {error}", parent=self.login_window)
        except requests.RequestException:
            messagebox.showerror(
                "Error",
                "Cannot connect to the app. Make sure it’s running.",
                parent=self.login_window
            )

    def setup_main_gui(self):
        """Create the main GUI with tabs for Trading, Portfolio, Market Data, and Settings."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, fill="both", expand=True)  # Fill window

        # Create frames for each tab
        self.trading_frame = ttk.Frame(self.notebook)
        self.portfolio_frame = ttk.Frame(self.notebook)
        self.market_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.trading_frame, text="Trading")
        self.notebook.add(self.portfolio_frame, text="Portfolio")
        self.notebook.add(self.market_frame, text="Market Data")
        self.notebook.add(self.settings_frame, text="Settings")

        # Initialize each tab
        self.setup_trading_tab()
        self.setup_portfolio_tab()
        self.setup_market_tab()
        self.setup_settings_tab()

        # Start WebSocket for live market updates
        self.start_websocket()

    def setup_trading_tab(self):
        """Set up the Trading tab for buying/selling assets and training models."""
        tk.Label(self.trading_frame, text="Trading Dashboard", font=("Arial", 14)).pack(pady=10)
        
        # Symbol input
        tk.Label(self.trading_frame, text="Asset (e.g., BTC for Bitcoin):").pack()
        self.symbol_entry = tk.Entry(self.trading_frame, width=20)
        self.symbol_entry.pack(pady=5)
        self.symbol_entry.insert(0, "BTC")
        
        # Amount input
        tk.Label(self.trading_frame, text="Amount (e.g., 0.01 for 0.01 BTC):").pack()
        self.amount_entry = tk.Entry(self.trading_frame, width=20)
        self.amount_entry.pack(pady=5)
        self.amount_entry.insert(0, "0.01")
        
        # Buy/Sell buttons
        tk.Button(self.trading_frame, text="Buy", command=lambda: self.make_trade("buy"), width=10).pack(pady=5)
        tk.Button(self.trading_frame, text="Sell", command=lambda: self.make_trade("sell"), width=10).pack(pady=5)
        
        # Train Model button
        tk.Button(
            self.trading_frame,
            text="Train Trading Model",
            command=self.train_model,
            width=15
        ).pack(pady=10)
        
        # Status message
        self.trade_status = tk.Label(self.trading_frame, text="Ready to trade", fg="blue")
        self.trade_status.pack(pady=10)

    def setup_portfolio_tab(self):
        """Set up the Portfolio tab to show cash and assets."""
        tk.Label(self.portfolio_frame, text="Your Portfolio", font=("Arial", 14)).pack(pady=10)
        self.portfolio_text = tk.Text(self.portfolio_frame, height=10, width=50)
        self.portfolio_text.pack(pady=5)
        tk.Button(self.portfolio_frame, text="Refresh", command=self.update_portfolio, width=10).pack(pady=5)
        self.update_portfolio()  # Load portfolio initially

    def setup_market_tab(self):
        """Set up the Market Data tab for live updates."""
        tk.Label(self.market_frame, text="Live Market Data", font=("Arial", 14)).pack(pady=10)
        self.market_text = tk.Text(self.market_frame, height=10, width=50)
        self.market_text.pack(pady=5)
        self.market_text.insert(tk.END, "Waiting for market updates...\n")

    def setup_settings_tab(self):
        """Set up the Settings tab for entering API keys."""
        tk.Label(self.settings_frame, text="Your API Keys", font=("Arial", 14)).pack(pady=10)
        
        # Alpha Vantage API key
        tk.Label(self.settings_frame, text="Alpha Vantage API Key (for market data):").pack()
        self.market_api_entry = tk.Entry(self.settings_frame, width=40)
        self.market_api_entry.pack(pady=5)
        
        # Exchange API key
        tk.Label(self.settings_frame, text="Exchange API Key (Binance or Coinbase):").pack()
        self.exchange_api_entry = tk.Entry(self.settings_frame, width=40)
        self.exchange_api_entry.pack(pady=5)
        
        # Exchange secret
        tk.Label(self.settings_frame, text="Exchange Secret (Binance or Coinbase):").pack()
        self.exchange_secret_entry = tk.Entry(self.settings_frame, width=40)
        self.exchange_secret_entry.pack(pady=5)
        
        # Save button
        tk.Button(self.settings_frame, text="Save Keys", command=self.save_settings, width=15).pack(pady=10)
        
        # Load existing keys
        self.load_settings()

    def load_settings(self):
        """Load user-specific API keys from the backend."""
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(f"{self.api_url}/users/api-keys", headers=headers, timeout=5)
            if response.status_code == 200:
                keys = response.json()
                self.market_api_entry.delete(0, tk.END)
                self.market_api_entry.insert(0, keys.get("market_api_key", ""))
                self.exchange_api_entry.delete(0, tk.END)
                self.exchange_api_entry.insert(0, keys.get("exchange_api_key", ""))
                self.exchange_secret_entry.delete(0, tk.END)
                self.exchange_secret_entry.insert(0, keys.get("exchange_secret", ""))
            else:
                messagebox.showwarning("Warning", "Could not load API keys. Enter and save new keys.")
        except requests.RequestException:
            messagebox.showerror("Error", "Cannot connect to the app. Make sure it’s running.")

    def save_settings(self):
        """Save API keys to the backend."""
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "market_api_key": self.market_api_entry.get().strip(),
            "exchange_api_key": self.exchange_api_entry.get().strip(),
            "exchange_secret": self.exchange_secret_entry.get().strip()
        }
        if not any(payload.values()):
            messagebox.showerror("Error", "Please enter at least one API key.")
            return
        try:
            response = requests.post(f"{self.api_url}/users/api-keys", json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                messagebox.showinfo("Success", "API keys saved successfully!")
            else:
                error = response.json().get("detail", "Failed to save keys.")
                messagebox.showerror("Error", f"Failed to save keys: {error}")
        except requests.RequestException:
            messagebox.showerror("Error", "Cannot connect to the app. Make sure it’s running.")

    def make_trade(self, trade_type):
        """Send a buy or sell trade request to the backend."""
        symbol = self.symbol_entry.get().strip().upper()
        amount = self.amount_entry.get().strip()
        if not symbol or not amount:
            self.trade_status.config(text="Error: Enter both asset and amount.", fg="red")
            return
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError:
            self.trade_status.config(text="Error: Amount must be a number (e.g., 0.01).", fg="red")
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"symbol": symbol, "amount": amount, "type": trade_type}
        try:
            response = requests.post(f"{self.api_url}/trading/trade", json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                trade_id = response.json().get("trade_id", "Unknown")
                self.trade_status.config(text=f"{trade_type.capitalize()} successful: Trade ID {trade_id}", fg="green")
            else:
                error = response.json().get("detail", "Trade failed.")
                self.trade_status.config(text=f"Error: {error}", fg="red")
        except requests.RequestException:
            self.trade_status.config(text="Error: Cannot connect to the app.", fg="red")

    def update_portfolio(self):
        """Fetch and display portfolio data from the backend."""
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(f"{self.api_url}/portfolio", headers=headers, timeout=5)
            if response.status_code == 200:
                portfolio = response.json()
                self.portfolio_text.delete(1.0, tk.END)
                self.portfolio_text.insert(tk.END, f"Cash: ${portfolio.get('cash', 0):.2f}\n\n")
                assets = portfolio.get('assets', [])
                if not assets:
                    self.portfolio_text.insert(tk.END, "No assets owned.\n")
                for asset in assets:
                    self.portfolio_text.insert(tk.END, f"{asset.get('name', 'Unknown')}: ${asset.get('value', 0):.2f}\n")
            else:
                self.portfolio_text.delete(1.0, tk.END)
                self.portfolio_text.insert(tk.END, "Error: Could not load portfolio.\n")
        except requests.RequestException:
            self.portfolio_text.delete(1.0, tk.END)
            self.portfolio_text.insert(tk.END, "Error: Cannot connect to the app.\n")

    def train_model(self):
        """Run the model training script."""
        try:
            self.trade_status.config(text="Training model, please wait...", fg="blue")
            self.root.update()  # Refresh GUI
            result = subprocess.run(
                ["python", "modeltrainer/EnhancedModelTrainer", "--config", "config/ml_config.yaml"],
                check=True,
                capture_output=True,
                text=True
            )
            self.trade_status.config(text="Model trained successfully! Check models/ folder.", fg="green")
        except subprocess.CalledProcessError as e:
            error = e.stderr or "Unknown error."
            self.trade_status.config(text=f"Error: Training failed. {error}", fg="red")
        except FileNotFoundError:
            self.trade_status.config(text="Error: Training script not found. Check modeltrainer/ folder.", fg="red")

    def on_websocket_message(self, ws, message):
        """Handle live market data updates from WebSocket."""
        try:
            data = json.loads(message)
            if data.get("type") == "market_update":
                self.market_text.delete(1.0, tk.END)
                self.market_text.insert(
                    tk.END,
                    f"{data['data'].get('symbol', 'Unknown')}: ${data['data'].get('price', 0):.2f} "
                    f"({data['data'].get('change', 0):+.2f}%)\n"
                )
        except json.JSONDecodeError:
            self.market_text.delete(1.0, tk.END)
            self.market_text.insert(tk.END, "Error: Invalid market data received.\n")

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
