# app.py
import subprocess
import sys

def install_requirements():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit", "requests"])

if __name__ == "__main__":
    try:
        import streamlit
    except ImportError:
        print("Installing required packages...")
        install_requirements()
    
    subprocess.run([sys.executable, "-m", "streamlit", "run", "ui.py"])