import sqlite3
import chess
import chess.engine
import chess.pgn
import io
from config import DATABASE_PATH, STOCKFISH_PATH, ENGINE_TIME_LIMIT
from data_collector import extract_features

def fill_missing_features(limit_games=50):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Ambil game_id unik yang punya move dengan fitur 0
    cursor.execute("""
        SELECT DISTINCT game_id
        FROM move_features
        WHERE centipawn_loss = 0
          AND engine_similarity = 0
          AND move_entropy = 0
          AND tactical_spike = 0
        ORDER BY game_id
        LIMIT ?
    """, (limit_games,))
    game_ids = [row[0] for row in cursor.fetchall()]

    if not game_ids:
        print("Tidak ada game yang perlu diisi fiturnya.")
        conn.close()
        return

    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    try:
        for gid in game_ids:
            cursor.execute("SELECT pgn FROM games WHERE id = ?", (gid,))
            pgn_row = cursor.fetchone()
            if not pgn_row:
                continue
            game = chess.pgn.read_game(io.StringIO(pgn_row[0]))
            if game is None:
                continue

            board = game.board()
            moves = list(game.mainline_moves())
            cursor.execute("SELECT id, move_san FROM move_features WHERE game_id = ? ORDER BY move_number", (gid,))
            move_rows = cursor.fetchall()

            if len(moves) != len(move_rows):
                continue

            for idx, move_obj in enumerate(moves):
                move_id, move_san = move_rows[idx]
                try:
                    feat = extract_features(board.copy(), move_obj, engine)
                    cpl, sim, ent, spike = feat
                    cursor.execute("""
                        UPDATE move_features
                        SET centipawn_loss = ?,
                            engine_similarity = ?,
                            move_entropy = ?,
                            tactical_spike = ?
                        WHERE id = ?
                    """, (cpl, sim, ent, spike, move_id))
                except Exception as e:
                    print(f"Error game {gid} move {move_san}: {e}")
                board.push(move_obj)
            conn.commit()
            print(f"Game {gid} selesai.")
    finally:
        engine.quit()
        conn.close()
    print("✅ Selesai mengisi fitur.")

if __name__ == "__main__":
    fill_missing_features(limit_games=50)