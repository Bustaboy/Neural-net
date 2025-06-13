# Testing the Neural-net Executable

This guide helps you test the Neural-net trading app executable on your computer. Follow these steps when you have console access to make sure everything works.

## What You Need
1. **A Computer**: Windows, Mac, or Linux with at least 8GB RAM and 20GB free space.
2. **Python 3.11**: Download from [python.org](https://www.python.org/downloads/) and install it. Check "Add Python to PATH" on Windows.
3. **The Repository**: Download the latest ZIP from GitHub (click 'Code' > 'Download ZIP') and unzip it to a folder (e.g., `C:\Neural-net` on Windows).
4. **Built Executable**: Follow the steps in `BUILD.md` to create the `NeuralNet` executable in the `dist/` folder.

## Steps to Test the Executable
1. **Open a Terminal**:
   - Windows: Press Win+R, type `cmd`, press Enter.
   - Mac: Search for "Terminal" in Spotlight.
   - Linux: Open your terminal app.
2. **Navigate to the Folder**:
   - Type: `cd C:\Neural-net` (replace with your folder path, e.g., `~/Documents/Neural-net` on Mac/Linux).
3. **Run the Executable**:
   - Type: `dist\NeuralNet` (Windows) or `./dist/NeuralNet` (Mac/Linux), then press Enter.
   - **What to Expect**: A login window should appear.
4. **Test Login and Registration**:
   - **Login**: Enter `testuser` as username and `testpass` as password, then click Login.
     - Expected: Main window with tabs (Trading, Portfolio, Market Data, Settings).
     - If it fails, try registering a new user.
   - **Register**: Enter a new username (e.g., `newuser`) and password (e.g., `newpass`), click Register, then log in with those credentials.
     - Expected: Success message, then login works.
5. **Test Settings**:
   - Go to the Settings tab.
   - Enter dummy API keys (e.g., `alpha_key` for Alpha Vantage, `binance_key` and `binance_secret` for Binance), then click Save Keys.
     - Expected: "API keys saved successfully!" message.
6. **Test Trading**:
   - Go to the Trading tab.
   - Enter `BTC` as the asset and `0.01` as the amount, then click Buy.
     - Expected: "Buy successful: Trade ID ..." or an error if keys are invalid.
   - Click Sell with the same settings.
     - Expected: Similar success or error.
   - Click Train Model.
     - Expected: "Model trained successfully!" or an error if no market data.
7. **Test Portfolio**:
   - Go to the Portfolio tab.
   - Click Refresh.
     - Expected: Displays "Cash: $1000.00" and asset values (e.g., "BTC: $600.75") based on dummy trades.
8. **Test Market Data**:
   - Go to the Market Data tab.
     - Expected: Shows live updates like "BTC: $60000.75 (+2.5%)" if WebSocket works, or "Waiting for market updates..." if not.
9. **Stop the App**:
   - Close the window by clicking the X button.
     - Expected: App closes without errors.

## Troubleshooting
- **Executable won’t start**: Ensure Python 3.11 is installed and the `dist/` folder contains `NeuralNet`. Rerun the `BUILD.md` steps.
- **Login fails**: Check username/password. If registering fails, ensure the backend initialized `neuralnet.db`.
- **Trading fails**: Verify API keys in Settings. Dummy keys may not work with real exchanges; use test keys from Binance.
- **No market data**: Ensure internet is on and `market_data` table is populated (may require manual data or Step 4 updates).
- **Crashes**: Open `start_app.py` in a text editor (e.g., Notepad++) and ensure it matches GitHub. Check the terminal for errors if running separately.
- **Need help?**: Contact the person who shared this app or revisit `BUILD.md` and this guide.

## Notes
- The first run creates `neuralnet.db` based on `scripts/init_database.sql`. If it fails, rerun the schema with `sqlite3 neuralnet.db < scripts/init_database.sql`.
- `models/central_model.pkl` trains on first "Train Model" click if no data exists, which may take time.
- Keep API keys secret and test with small amounts first.
