import os

# Set the STOCKFISH_PATH environment variable to point to your binary,
# otherwise the default "stockfish" (from PATH) will be used.
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "stockfish")

DATABASE_PATH = os.path.join("data", "games.db")
MODEL_PATH = os.path.join("models", "cheat_detector.joblib")
DATASET_CSV = os.path.join("data", "training_data.csv")
ENGINE_TIME_LIMIT = 0.2      # seconds per engine move
DEFAULT_DEPTH = 10
