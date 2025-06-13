# Distributing the Neural-net Executable

This guide helps you package and share the Neural-net trading app with others. Follow these steps when you have console access after building the executable with `BUILD.md`.

## What You Need
1. **A Computer**: Windows, Mac, or Linux with at least 8GB RAM and 20GB free space.
2. **Python 3.11**: Already installed from `BUILD.md`.
3. **The Repository**: Use the unzipped folder from the GitHub ZIP (e.g., `C:\Neural-net`).
4. **Built Executable**: Ensure `dist/NeuralNet` exists from `BUILD.md`.
5. **Compression Tools** (optional for advanced formats):
   - Windows: 7-Zip (free from [7-zip.org](https://www.7-zip.org/)).
   - Mac: Built-in or [create-dmg](https://github.com/create-dmg/create-dmg) (`pip install create-dmg`).
   - Linux: Built-in or [appimage-builder](https://appimage.github.io/) (`pip install appimage-builder`).

## Steps to Distribute the Executable
1. **Open a Terminal**:
   - Windows: Press Win+R, type `cmd`, press Enter.
   - Mac: Search for "Terminal" in Spotlight.
   - Linux: Open your terminal app.
2. **Navigate to the Folder**:
   - Type: `cd C:\Neural-net` (replace with your folder path, e.g., `~/Documents/Neural-net`).
3. **Create a Distribution Package**:
   - **Windows (ZIP)**:
     - Type: `cd dist`
     - Type: `7z a NeuralNet.zip NeuralNet.exe README.txt TROUBLESHOOTING.txt`
       - If 7-Zip isn’t installed, download it and add to PATH, or use Windows’ built-in zip by right-clicking `dist/`, selecting "Send to" > "Compressed (zipped) folder", and renaming to `NeuralNet.zip`.
     - Add `README.txt` and `TROUBLESHOOTING.txt` (create manually or copy from Step 5 suggestions).
   - **Mac (DMG)**:
     - Type: `pip install create-dmg`
     - Type: `create-dmg --app-drop-link  dist/NeuralNet.app NeuralNet.dmg`
     - Add `README.txt` and `TROUBLESHOOTING.txt` to the DMG manually via Finder.
   - **Linux (AppImage)**:
     - Type: `pip install appimage-builder`
     - Create a file named `appimage-recipe.yml` in `dist/` with:
       ```yaml
       !AppImage
       app:
         name: NeuralNet
         exec: NeuralNet
       files:
         include:
           - api
           - backend
           - core
           - gui
           - ml
           - modeltrainer
           - trading
           - scripts
           - config
           - models
       ```
     - Type: `appimage-builder --recipe appimage-recipe.yml`
     - The output will be `NeuralNet.AppImage`.
     - Add `README.txt` and `TROUBLESHOOTING.txt` to the AppImage folder.
4. **Create Support Files**:
   - **README.txt**:
     ```
     Neural-net Trading App

     1. Double-click NeuralNet (or NeuralNet.exe on Windows) to start.
     2. Register a new account or log in (e.g., username: testuser, password: testpass).
     3. Go to Settings and enter your API keys (get from Alpha Vantage and Binance/Coinbase).
     4. Use Trading to buy/sell assets (e.g., BTC).
     5. Check Portfolio for your money.
     6. See Market Data for live updates.
     7. Train Model if needed (may take time).

     See TROUBLESHOOTING.txt for help.
     ```
   - **TROUBLESHOOTING.txt**:
     ```
     - App won’t start: Ensure 8GB RAM and 1GB free space. Restart computer.
     - Login fails: Check username/password or register.
     - Trading fails: Verify API keys in Settings.
     - No market data: Check internet and Alpha Vantage key.
     - Training slow: Use a computer with a graphics card or wait.
     - Contact support: Email the app creator.
     ```
   - Add these files to your distribution package manually when building.
5. **Share the App**:
   - Upload `NeuralNet.zip`, `NeuralNet.dmg`, or `NeuralNet.AppImage` to a file-sharing service (e.g., Google Drive, Dropbox).
   - Share the link with users, along with `README.txt` and `TROUBLESHOOTING.txt`.

## Troubleshooting
- **ZIP/DMG/AppImage fails**: Ensure tools are installed. Check terminal for errors.
- **File too large**: Compress with 7-Zip or split into parts if needed.
- **Sharing issues**: Verify upload permissions and link access.
- **Need help?**: Revisit `BUILD.md` or contact the app creator.

## Notes
- Test the executable with `TESTING.md` before sharing.
- Users need internet for market data and API calls.
- Keep API keys secret and advise users to do the same.
