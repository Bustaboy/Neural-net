import subprocess
import time
import os
from gui.main import NeuralNetApp
import tkinter as tk

def start_backend():
    """Start FastAPI backend in a subprocess."""
    env = os.environ.copy()
    # Set dummy environment variables (overridden by user-specific keys)
    env["MARKET_API_KEY"] = env.get("MARKET_API_KEY", "dummy_key")
    env["EXCHANGE_API_KEY"] = env.get("EXCHANGE_API_KEY", "dummy_key")
    env["EXCHANGE_SECRET"] = env.get("EXCHANGE_SECRET", "dummy_secret")
    subprocess.Popen(["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"], env=env)

if __name__ == "__main__":
    start_backend()
    time.sleep(5)  # Wait for backend to start
    root = tk.Tk()
    app = NeuralNetApp(root)
    root.mainloop()
