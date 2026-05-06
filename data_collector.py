import sqlite3
import pandas as pd
import numpy as np
import chess
import chess.engine
from config import DATABASE_PATH, STOCKFISH_PATH, ENGINE_TIME_LIMIT


def init_db():
    """Create tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pgn TEXT,
                    white_label TEXT,
                    black_label TEXT,
                    white_agent TEXT,
                    black_agent TEXT,
                    result TEXT,
                    moves_json TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS move_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER,
                    move_number INTEGER,
                    side TEXT,
                    move_san TEXT,
                    centipawn_loss REAL,
                    engine_similarity REAL,
                    move_entropy REAL,
                    tactical_spike REAL,
                    FOREIGN KEY(game_id) REFERENCES games(id)
                )''')
    conn.commit()
    conn.close()


def extract_features(board_before, move, engine, time_limit=ENGINE_TIME_LIMIT):
    """
    Compute centipawn loss, engine similarity, move entropy, and tactical spike.
    Returns (0.0, 0.0, 0.0, 0.0) on any error.
    """
    try:
        info_before = engine.analyse(board_before, chess.engine.Limit(time=time_limit))
        score_before = info_before["score"].relative.score(mate_score=10000) or 0

        multipv_info = engine.analyse(
            board_before, chess.engine.Limit(time=time_limit), multipv=5
        )
        top_moves = []
        for pv in multipv_info:
            if "pv" in pv and pv["pv"]:
                move_obj = pv["pv"][0]
                score = pv["score"].relative.score(mate_score=10000) or 0
                top_moves.append((move_obj, score))

        if not top_moves:
            return 0.0, 0.0, 0.0, 0.0

        best_move, best_score = top_moves[0]
        chosen_score = next(
            (s for m, s in top_moves if m == move), None
        )
        if chosen_score is None:
            board_after = board_before.copy()
            board_after.push(move)
            info_after = engine.analyse(board_after, chess.engine.Limit(time=time_limit))
            chosen_score = info_after["score"].relative.score(mate_score=10000) or 0

        centipawn_loss = best_score - chosen_score
        engine_similarity = 1.0 if move == best_move else 0.0

        scores = np.array([s for _, s in top_moves])
        probs = np.exp(scores - scores.max())
        probs /= probs.sum()
        entropy = -np.sum(probs * np.log(probs + 1e-10))

        board_after = board_before.copy()
        board_after.push(move)
        info_after = engine.analyse(board_after, chess.engine.Limit(time=time_limit))
        score_after = info_after["score"].relative.score(mate_score=10000) or 0
        tactical_spike = abs(score_after - score_before)

        return centipawn_loss, engine_similarity, entropy, tactical_spike

    except Exception:
        return 0.0, 0.0, 0.0, 0.0
