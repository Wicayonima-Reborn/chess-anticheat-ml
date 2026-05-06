# Chess Anti-Cheat ML

A supervised machine learning project to detect engine-like behavior in chess games.
Built for defensive research, educational purposes, and portfolio demonstration.

## Overview

This system uses a Random Forest classifier trained on behavioral features extracted from chess moves.
It can differentiate between human play and engine-assisted play by analyzing:

- **Centipawn loss** – how much a move deviates from the best engine move
- **Engine similarity** – whether the move matches the engine's top choice
- **Move entropy** – uncertainty across top candidate moves
- **Tactical spike** – sudden evaluation swings after a move

The project includes simulated adversarial agents, real human game data from Lichess, a balancing engine‑vs‑engine generator, and a real‑time detection GUI.

## Features

- Simulate multiple agent behaviors: Full Engine, Tactical Assist, Noise Injection, Mixed Human
- Import real human games from the Lichess Open Database (PGN `.zst`)
- Balance datasets with fast engine‑only simulations
- Train a Random Forest model and evaluate with precision/recall
- GUI to play against bots and see live move predictions
- Statistics script to monitor dataset composition

## Tech Stack

- Python 3.10+
- Stockfish chess engine
- scikit-learn, pandas, numpy
- PySide6 (GUI)
- python-chess

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/chess-anticheat-ml.git
cd chess-anticheat-ml
```

### 2. Set up a virtual environment (recommended)

```bash
python -m venv env
source env/bin/activate        # Linux/macOS
env\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download and configure Stockfish

- Download the Stockfish engine from [stockfishchess.org/download](https://stockfishchess.org/download/)
- Place the executable in a known location
- Set the `STOCKFISH_PATH` environment variable, or edit `config.py` to point to your binary:

```python
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "stockfish")
```

If you don't set the environment variable, the code will look for `stockfish` in your system PATH.

### 5. Prepare folders

```bash
mkdir data models
```

## Usage

### Generate training data (simulated human vs engine)

```bash
python main.py simulate --games 100
```

This creates 100 games (90% Human vs Engine) and saves them to the database.

### Import real human games from Lichess (optional)

1. Download a PGN `.zst` file from [database.lichess.org](https://database.lichess.org/) (choose a standard chess month, e.g., November 2015).
2. Import games without computing features (fast):

```bash
python import_fast.py path/to/file.pgn.zst --games 500
```

3. Compute features for the imported games (can take time):

```bash
python fill_features.py
```

### Add more engine-only data

```bash
python simulate_engine_only.py --games 200 --fast
```

This runs engine‑vs‑engine matches quickly to increase engine sample count.

### Train the model

```bash
python main.py train
```

### Launch the GUI

```bash
python gui.py
```

Play as Human against any agent and watch live detection results.

### Check dataset statistics

```bash
python stats.py
```

Shows game counts, move counts, and Human:Engine ratio.

## Customization for Your Machine

- **Stockfish path**: Either set the environment variable `STOCKFISH_PATH` to your binary, or edit `config.py` directly.
- **Database location**: Default is `data/games.db`. Change `DATABASE_PATH` in `config.py` if needed.
- **Engine time limit**: Adjust `ENGINE_TIME_LIMIT` in `config.py` to trade off speed vs. accuracy (default 0.2 seconds).
- **Model class weights**: Edit `anti_cheat_detector.py` if you want to bias the model toward detecting engines.

## Important Notes

- This project is for **defensive research and education only**. It is not intended to cheat or bypass fair‑play systems.
- The model's predictions are probabilistic estimates, not absolute judgments.
- Data imported from Lichess is under CC0 license.

## License

This project is licensed under the [MIT License](./LICENSE).
