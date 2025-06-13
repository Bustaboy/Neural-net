import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import websocket
import threading
import subprocess
from datetime import datetime
import time

class NeuralNetApp:
    def __init__(self, root):
        """Initialize the cyberpunk trading interface with central server."""
        self.root = root
        self.root.title("Neural-net: Night City Trader")
        self.root.geometry("800x600")
        self.root.configure(bg='black')
        self.api_url = "http://<central-vps-ip>:80"  # Replace with central VPS IP
        self.ws_url = "ws://<central-vps-ip>:8765/trade_log"  # Replace with central VPS IP
        self.token = None
        self.user_id = None
        self.trade_log = []
        self.ws = None
        self.show_login_window()

    def show_login_window(self):
        """Display a cyberpunk login portal."""
        self.login_window = tk.Toplevel(self.root)
        self.login_window.title("Enter Night City")
        self.login_window.geometry("300x250")
        self.login_window.resizable(False, False)
        self.login_window.configure(bg='black')

        tk.Label(self.login_window, text="Welcome, Choombas! Log in or jack into a new profile", font=("Courier New", 12, "bold"), fg="cyan", bg="black").pack(pady=10)
        tk.Label(self.login_window, text="Handle:", fg="cyan", bg="black").pack(pady=5)
        self.username_entry = tk.Entry(self.login_window, width=20, bg="black", fg="cyan", insertbackground="cyan")
        self.username_entry.pack()
        tk.Label(self.login_window, text="Passcode:", fg="cyan", bg="black").pack(pady=5)
        self.password_entry = tk.Entry(self.login_window, show="*", width=20, bg="black", fg="cyan", insertbackground="cyan")
        self.password_entry.pack()
        tk.Button(self.login_window, text="Jack In", command=self.login, width=10, bg="black", fg="cyan").pack(pady=10)
        tk.Button(self.login_window, text="New Profile", command=self.register, width=10, bg="black", fg="cyan").pack(pady=5)

    def login(self):
        """Log into the net with credentials."""
        handle = self.username_entry.get().strip()
        passcode = self.password_entry.get().strip()
        if not handle or not passcode:
            messagebox.showerror("Error", "Enter your handle and passcode, choom!", parent=self.login_window)
            return
        try:
            response = requests.post(f"{self.api_url}/auth/login", json={"username": handle, "password": passcode}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.user_id = data.get("user_id")
                if not self.user_id:
                    messagebox.showerror("Error", "Login failed: No grid access granted.", parent=self.login_window)
                    return
                self.login_window.destroy()
                self.setup_main_gui()
                self.start_websocket()
            else:
                messagebox.showerror("Error", "Invalid handle or passcode. Try again, nova!", parent=self.login_window)
        except requests.RequestException:
            messagebox.showerror("Error", "Net connection lost. Ensure central server is online.", parent=self.login_window)

    def register(self):
        """Register a new profile in the system."""
        handle = self.username_entry.get().strip()
        passcode = self.password_entry.get().strip()
        if not handle or not passcode:
            messagebox.showerror("Error", "Enter your handle and passcode, choom!", parent=self.login_window)
            return
        try:
            response = requests.post(f"{self.api_url}/auth/register", json={"username": handle, "password": passcode}, timeout=5)
            if response.status_code == 201:
                messagebox.showinfo("Success", "New profile jacked in! Log in with your handle.", parent=self.login_window)
            else:
                error = response.json().get("detail", "Registration glitch.")
                messagebox.showerror("Error", f"Failed to jack in: {error}", parent=self.login_window)
        except requests.RequestException:
            messagebox.showerror("Error", "Net connection lost. Ensure central server is online.", parent=self.login_window)

    def setup_main_gui(self):
        """Create the cyberpunk main interface with tabs."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, fill="both", expand=True)
        style = ttk.Style()
        style.configure("TNotebook", background="black", foreground="cyan")
        style.configure("TButton", background="black", foreground="cyan")
        style.configure("TLabel", background="black", foreground="cyan")

        self.trading_frame = ttk.Frame(self.notebook)
        self.portfolio_frame = ttk.Frame(self.notebook)
        self.market_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        self.help_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.trading_frame, text="Trade Hub")
        self.notebook.add(self.portfolio_frame, text="Asset Vault")
        self.notebook.add(self.market_frame, text="Data Net")
        self.notebook.add(self.settings_frame, text="Cyberdeck Config")
        self.notebook.add(self.help_frame, text="Netrunner’s Guide")

        self.setup_trading_tab()
        self.setup_portfolio_tab()
        self.setup_market_tab()
        self.setup_settings_tab()
        self.setup_help_tab()

        tk.Button(self.root, text="Help", command=self.show_help_popup, fg="cyan", bg="black").pack(side=tk.TOP, pady=5)

    def setup_trading_tab(self):
        """Set up the Trade Hub for netrunning trades and model upgrades."""
        tk.Label(self.trading_frame, text="Trade Hub: Netrun the Markets", font=("Courier New", 14, "bold"), fg="cyan").pack(pady=10)
        
        self.trade_log_text = tk.Text(self.trading_frame, height=10, width=70, bg="black", fg="cyan")
        self.trade_log_text.pack(pady=5)
        self.update_trade_log()

        tk.Label(self.trading_frame, text="Target Asset (e.g., BTC/USDT):", fg="cyan").pack()
        self.symbol_entry = tk.Entry(self.trading_frame, width=20, bg="black", fg="cyan", insertbackground="cyan")
        self.symbol_entry.pack(pady=5)
        self.symbol_entry.insert(0, "BTC/USDT")
        tk.Label(self.trading_frame, text="Trade Amount (e.g., 0.01):", fg="cyan").pack()
        self.amount_entry = tk.Entry(self.trading_frame, width=20, bg="black", fg="cyan", insertbackground="cyan")
        self.amount_entry.pack(pady=5)
        self.amount_entry.insert(0, "0.01")
        tk.Button(self.trading_frame, text="Netrun Buy", command=lambda: self.make_trade("buy"), width=10).pack(pady=5)
        tk.Button(self.trading_frame, text="Netrun Sell", command=lambda: self.make_trade("sell"), width=10).pack(pady=5)
        
        tk.Button(self.trading_frame, text="Install Chrome Upgrade", command=self.train_model, width=15).pack(pady=10)
        
        self.trade_status = tk.Label(self.trading_frame, text="Ready to Netrun", fg="cyan")
        self.trade_status.pack(pady=10)

    def setup_portfolio_tab(self):
        """Set up the Asset Vault with profitability dashboard."""
        tk.Label(self.portfolio_frame, text="Asset Vault: Your Loot", font=("Courier New", 14, "bold"), fg="cyan").pack(pady=10)
        self.portfolio_text = tk.Text(self.portfolio_frame, height=5, width=50, bg="black", fg="cyan")
        self.portfolio_text.pack(pady=5)
        self.profit_label = tk.Label(self.portfolio_frame, text="Total Eddies: $0.00", fg="magenta")
        self.profit_label.pack(pady=5)
        tk.Button(self.portfolio_frame, text="Scan Vault", command=self.update_portfolio, width=10).pack(pady=5)
        self.update_portfolio()

    def setup_market_tab(self):
        """Set up the Data Net for live market feeds."""
        tk.Label(self.market_frame, text="Data Net: Live Feeds", font=("Courier New", 14, "bold"), fg="cyan").pack(pady=10)
        self.market_text = tk.Text(self.market_frame, height=10, width=50, bg="black", fg="cyan")
        self.market_text.pack(pady=5)
        self.market_text.insert(tk.END, "Awaiting Data Stream...\n")

    def setup_settings_tab(self):
        """Set up the Cyberdeck Config for API and environment settings."""
        tk.Label(self.settings_frame, text="Cyberdeck Config: Access Codes", font=("Courier New", 14, "bold"), fg="cyan").pack(pady=10)
        tk.Label(self.settings_frame, text="Alpha Vantage Access Code (Market Data):", fg="cyan").pack()
        self.market_api_entry = tk.Entry(self.settings_frame, width=40, bg="black", fg="cyan", insertbackground="cyan")
        self.market_api_entry.pack(pady=5)
        tk.Label(self.settings_frame, text="Binance Access Key:", fg="cyan").pack()
        self.exchange_api_entry = tk.Entry(self.settings_frame, width=40, bg="black", fg="cyan", insertbackground="cyan")
        self.exchange_api_entry.pack(pady=5)
        tk.Label(self.settings_frame, text="Binance Secret Key:", fg="cyan").pack()
        self.exchange_secret_entry = tk.Entry(self.settings_frame, width=40, bg="black", fg="cyan", insertbackground="cyan")
        self.exchange_secret_entry.pack(pady=5)
        self.testnet_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.settings_frame, text="Testnet Mode (Safe Zone)", variable=self.testnet_var, fg="cyan", bg="black").pack(pady=5)
        tk.Button(self.settings_frame, text="Upload Codes", command=self.save_settings, width=15).pack(pady=10)
        self.load_settings()

    def setup_help_tab(self):
        """Set up the Netrunner’s Guide tab."""
        tk.Label(self.help_frame, text="Netrunner’s Guide: Survive the Sprawl", font=("Courier New", 14, "bold"), fg="cyan").pack(pady=10)
        help_text = """
        Welcome to Night City, choom! Here’s your guide:
        - Trade Hub: Netrun markets with Buy/Sell commands.
        - Asset Vault: Track your Eddies and loot.
        - Data Net: Monitor live feeds from the grid.
        - Cyberdeck Config: Upload access codes and toggle Testnet.
        - Install Chrome Upgrade: Train your AI brain.
        Stay chromed and keep your codes safe!
        """
        tk.Text(self.help_frame, height=15, width=60, bg="black", fg="cyan", wrap=tk.WORD).insert(tk.END, help_text).pack(pady=10)

    def show_help_popup(self):
        """Display a pop-up with the Netrunner’s Guide."""
        messagebox.showinfo("Netrunner’s Guide", "Welcome to Night City, choom! Use Trade Hub to netrun markets, Asset Vault to track eddies, Data Net for feeds, and Cyberdeck Config to upload codes. Toggle Testnet for safe runs! Stay chromed!")

    def load_settings(self):
        """Load user-specific API keys and testnet setting from backend."""
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
                self.testnet_var.set(keys.get("testnet", False))
            else:
                messagebox.showwarning("Warning", "Failed to decrypt access codes. Enter and upload new ones.")
        except requests.RequestException:
            messagebox.showerror("Error", "Net connection lost. Ensure central server is online.")

    def save_settings(self):
        """Save API keys and testnet setting to backend."""
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "market_api_key": self.market_api_entry.get().strip(),
            "exchange_api_key": self.exchange_api_entry.get().strip(),
            "exchange_secret": self.exchange_secret_entry.get().strip(),
            "testnet": self.testnet_var.get()
        }
        if not any(payload.values()):
            messagebox.showerror("Error", "Enter at least one access code, choom!")
            return
        try:
            response = requests.post(f"{self.api_url}/users/api-keys", json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                messagebox.showinfo("Success", "Access codes uploaded to the grid!")
            else:
                error = response.json().get("detail", "Upload failed.")
                messagebox.showerror("Error", f"Failed to upload codes: {error}")
        except requests.RequestException:
            messagebox.showerror("Error", "Net connection lost. Ensure central server is online.")

    def make_trade(self, trade_type):
        """Send a netrun trade request to the backend."""
        target = self.symbol_entry.get().strip().upper()
        amount = self.amount_entry.get().strip()
        if not target or not amount:
            self.trade_status.config(text="Error: Target and amount required, nova!", fg="red")
            return
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive, choom!")
        except ValueError:
            self.trade_status.config(text="Error: Amount must be a number (e.g., 0.01).", fg="red")
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"symbol": target, "amount": amount, "type": trade_type}
        try:
            response = requests.post(f"{self.api_url}/trading/trade", json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                trade_id = response.json().get("trade_id", "Unknown")
                self.trade_status.config(text=f"Netrun {trade_type.capitalize()} Complete: ID {trade_id}", fg="green")
                self.update_trade_log(f"{datetime.now()}: Netrun {trade_type.capitalize()} {amount} {target} - ID {trade_id}")
            else:
                error = response.json().get("detail", "Trade glitch.")
                self.trade_status.config(text=f"Error: {error}", fg="red")
        except requests.RequestException:
            self.trade_status.config(text="Error: Net connection lost.", fg="red")

    def train_model(self):
        """Install a chrome upgrade (train the model)."""
        try:
            self.trade_status.config(text="Upgrading Chrome, hold tight...", fg="cyan")
            self.root.update()
            result = subprocess.run(
                ["python", "modeltrainer/EnhancedModelTrainer.py", "--user-id", str(self.user_id), "--config", "config/ml_config.yaml"],
                check=True,
                capture_output=True,
                text=True
            )
            self.trade_status.config(text="Chrome Upgrade Installed!", fg="green")
            self.update_trade_log(f"{datetime.now()}: Chrome Upgrade Installed")
        except subprocess.CalledProcessError as e:
            error = e.stderr or "Unknown glitch."
            self.trade_status.config(text=f"Error: Upgrade failed - {error}", fg="red")
        except FileNotFoundError:
            self.trade_status.config(text="Error: Upgrade script not found.", fg="red")

    def update_portfolio(self):
        """Scan the asset vault for eddies and holdings."""
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(f"{self.api_url}/portfolio", headers=headers, timeout=5)
            if response.status_code == 200:
                portfolio = response.json()
                self.portfolio_text.delete(1.0, tk.END)
                self.portfolio_text.insert(tk.END, f"Eddies: ${portfolio.get('cash', 0):.2f}\n\n")
                assets = portfolio.get('assets', [])
                if not assets:
                    self.portfolio_text.insert(tk.END, "Vault Empty...\n")
                for asset in assets:
                    self.portfolio_text.insert(tk.END, f"{asset.get('name', 'Unknown')}: ${asset.get('value', 0):.2f}\n")
                total_value = sum([a['value'] for a in assets] + [portfolio.get('cash', 0)])
                self.profit_label.config(text=f"Total Eddies: ${total_value:.2f}")
                top_pairs = sorted(assets, key=lambda x: x.get('value', 0), reverse=True)[:3]
                self.portfolio_text.insert(tk.END, f"\nTop Targets: {', '.join([p['name'] for p in top_pairs]) if top_pairs else 'None'}")
            else:
                self.portfolio_text.delete(1.0, tk.END)
                self.portfolio_text.insert(tk.END, "Error: Vault scan failed.\n")
        except requests.RequestException:
            self.portfolio_text.delete(1.0, tk.END)
            self.portfolio_text.insert(tk.END, "Error: Net connection lost.\n")

    def update_trade_log(self, message):
        """Update the cyberlog with new netrun actions."""
        if message:
            self.trade_log.append(message)
        self.trade_log_text.delete(1.0, tk.END)
        for log_entry in self.trade_log[-10:]:
            self.trade_log_text.insert(tk.END, f"{log_entry}\n")

    def on_websocket_message(self, ws, message):
        """Handle live data streams and trading updates from the net."""
        try:
            data = json.loads(message)
            if data.get("type") == "market_update":
                self.market_text.delete(1.0, tk.END)
                self.market_text.insert(
                    tk.END,
                    f"Data Net Feed: {data['data'].get('symbol', 'Unknown')} - Eddies: ${data['data'].get('price', 0):.2f} "
                    f"({data['data'].get('change', 0):+.2f}%) - RSI: {data['data'].get('rsi', 0.0)}\n"
                )
            elif data.get("type") == "trade_update":
                self.trade_log.append(data["message"])
                self.update_trade_log("")
            elif data.get("type") == "portfolio_update":
                self.update_portfolio()
        except json.JSONDecodeError:
            self.market_text.delete(1.0, tk.END)
            self.market_text.insert(tk.END, "Error: Corrupted Data Stream...\n")

    def start_websocket(self):
        """Start the data stream in a separate thread."""
        def run_websocket():
            self.ws = websocket.WebSocketApp(self.ws_url, on_message=self.on_websocket_message)
            self.ws.run_forever()
        threading.Thread(target=run_websocket, daemon=True).start()

    def show_help_popup(self):
        """Display a pop-up with the Netrunner’s Guide."""
        messagebox.showinfo("Netrunner’s Guide", "Welcome to Night City, choom! Use Trade Hub to netrun markets, Asset Vault to track eddies, Data Net for feeds, and Cyberdeck Config to upload codes. Toggle Testnet for safe runs! Stay chromed!")

if __name__ == "__main__":
    root = tk.Tk()
    app = NeuralNetApp(root)
    root.mainloop()
