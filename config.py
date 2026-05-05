import os

STOCKFISH_PATH = r"D:\FILE DOWNLOAD\stockfish-windows-x86-64\stockfish\stockfish-windows-x86-64.exe"
DATABASE_PATH = os.path.join("data", "games.db")
MODEL_PATH = os.path.join("models", "cheat_detector.joblib")
DATASET_CSV = os.path.join("data", "training_data.csv")
ENGINE_TIME_LIMIT = 0.2      # detik per move (engine)
DEFAULT_DEPTH = 10