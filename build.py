import os
import sys

def build_executable():
    # Path to the project directory (adjust if needed)
    project_dir = os.path.dirname(os.path.abspath(__file__))

    # PyInstaller command
    pyinstaller_command = [
        "pyinstaller",
        "--onefile",  # Single executable file
        "--add-data", f"{os.path.join(project_dir, 'api')};api",
        "--add-data", f"{os.path.join(project_dir, 'backend')};backend",
        "--add-data", f"{os.path.join(project_dir, 'core')};core",
        "--add-data", f"{os.path.join(project_dir, 'gui')};gui",
        "--add-data", f"{os.path.join(project_dir, 'ml')};ml",
        "--add-data", f"{os.path.join(project_dir, 'modeltrainer')};modeltrainer",
        "--add-data", f"{os.path.join(project_dir, 'trading')};trading",
        "--add-data", f"{os.path.join(project_dir, 'scripts')};scripts",
        "--add-data", f"{os.path.join(project_dir, 'config')};config",
        "--add-data", f"{os.path.join(project_dir, 'models')};models",
        "--name", "NeuralNet",
        "start_app.py"
    ]

    # Join command into a single string for execution
    command = " ".join(pyinstaller_command)
    print(f"Running: {command}")
    os.system(command)

if __name__ == "__main__":
    build_executable()
