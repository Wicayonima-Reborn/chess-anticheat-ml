import sqlite3
import pandas as pd
import numpy as np
import chess
import chess.engine
import chess.pgn
import io
from config import DATABASE_PATH, STOCKFISH_PATH, ENGINE_TIME_LIMIT

def init_db():
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
    Hitung fitur per move. Jika terjadi error (timeout, dll), kembalikan nilai nol.
    """
    try:
        # Evaluasi sebelum move
        info_before = engine.analyse(board_before, chess.engine.Limit(time=time_limit))
        score_before = info_before["score"].relative.score(mate_score=10000) or 0

        # Dapatkan top-5 moves beserta skor
        multipv_info = engine.analyse(board_before, chess.engine.Limit(time=time_limit), multipv=5)
        top_moves = []
        for pv in multipv_info:
            if "pv" in pv and len(pv["pv"]) > 0:
                move_obj = pv["pv"][0]
                score = pv["score"].relative.score(mate_score=10000) or 0
                top_moves.append((move_obj, score))

        if not top_moves:
            return 0.0, 0.0, 0.0, 0.0

        best_move = top_moves[0][0]
        best_score = top_moves[0][1]
        chosen_score = None
        for m, s in top_moves:
            if m == move:
                chosen_score = s
                break
        if chosen_score is None:
            # Move tidak di top-5, estimasi dari evaluasi setelah move
            board_after = board_before.copy()
            board_after.push(move)
            info_after = engine.analyse(board_after, chess.engine.Limit(time=time_limit))
            chosen_score = info_after["score"].relative.score(mate_score=10000) or 0

        centipawn_loss = best_score - chosen_score
        engine_similarity = 1.0 if move == best_move else 0.0

        # Entropi dari distribusi skor top-5
        scores = np.array([s for _, s in top_moves])
        probs = np.exp(scores - np.max(scores))
        probs /= probs.sum()
        entropy = -np.sum(probs * np.log(probs + 1e-10))

        # Tactical spike: perubahan evaluasi setelah move
        board_after = board_before.copy()
        board_after.push(move)
        info_after = engine.analyse(board_after, chess.engine.Limit(time=time_limit))
        score_after = info_after["score"].relative.score(mate_score=10000) or 0
        tactical_spike = abs(score_after - score_before)

        return centipawn_loss, engine_similarity, entropy, tactical_spike

    except Exception as e:
        # Catching any exception, termasuk TimeoutError, EngineTerminatedError, dll.
        print(f"Feature extraction error: {e}. Returning zeros.")
        return 0.0, 0.0, 0.0, 0.0