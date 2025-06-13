# Building the Neural-net Executable

This guide helps you create a single executable file for the Neural-net trading app using PyInstaller. Follow these steps on your computer when you have console access.

## What You Need
1. **A Computer**: Windows, Mac, or Linux with at least 8GB RAM and 20GB free space.
2. **Python 3.11**: Download from [python.org](https://www.python.org/downloads/) and install it. Check "Add Python to PATH" on Windows.
3. **PyInstaller**: A tool to make the executable. Install it with:
4. 4. **Internet Connection**: To download the repository and install dependencies.
5. **The Repository**: Download the latest ZIP from GitHub (click 'Code' > 'Download ZIP') and unzip it to a folder (e.g., `C:\Neural-net` on Windows).

## Steps to Build the Executable
1. **Open a Terminal**:
- Windows: Press Win+R, type `cmd`, press Enter.
- Mac: Search for "Terminal" in Spotlight.
- Linux: Open your terminal app.
2. **Navigate to the Folder**:
- Type: `cd C:\Neural-net` (replace with your folder path, e.g., `~/Documents/Neural-net` on Mac/Linux).
3. **Install Dependencies**:
- Type: `pip install -r Requirements.txt`
- This installs all needed libraries (e.g., FastAPI, pandas).
4. **Run PyInstaller**:
- Type the following command and press Enter:
  ```
  pyinstaller --onefile --add-data "api;api" --add-data "backend;backend" --add-data "core;core" --add-data "gui;gui" --add-data "ml;ml" --add-data "modeltrainer;modeltrainer" --add-data "trading;trading" --add-data "scripts;scripts" --add-data "config;config" --add-data "models;models" --name NeuralNet start_app.py
  ```
- **Explanation**:
  - `--onefile`: Creates one executable file.
  - `--add-data`: Includes all project folders (use `;` for Windows, `:` for macOS/Linux).
  - `--name NeuralNet`: Names the output file.
  - `start_app.py`: The entry point to start the app.
- Wait for the command to finish (it may take a few minutes).
5. **Find the Executable**:
- Look in the `dist/` folder inside your `Neural-net` folder.
- You’ll see `NeuralNet` (e.g., `NeuralNet.exe` on Windows).
6. **Test the App**:
- Double-click `NeuralNet` to run it.
- A login window should appear. Use `testuser:testpass` or register a new user.
- Enter API keys in the Settings tab (get them from Alpha Vantage and Binance/Coinbase).

## Troubleshooting
- **PyInstaller not found**: Reinstall with `pip install pyinstaller`.
- **Command fails**: Check the terminal for errors. Ensure all folders (api, backend, etc.) exist and `Requirements.txt` is correct.
- **Executable crashes**: Open `start_app.py` in a text editor (e.g., Notepad++) and ensure it matches the GitHub version. Test the backend separately with `uvicorn api.app:app --host 0.0.0.0 --port 8000` if possible.
- **No `dist/` folder**: Rerun the command and ensure no typos.
- **Need help?**: Contact the person who shared this app or revisit this guide.

## Notes
- The first run will create `neuralnet.db` based on `scripts/init_database.sql`.
- If `models/central_model.pkl` is a placeholder, the app will train a new model when you click "Train Model" in the Trading tab (this may take time).
- Keep your API keys secret and store them safely.
