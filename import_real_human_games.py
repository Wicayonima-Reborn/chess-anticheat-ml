import argparse
import zstandard as zstd
import chess.pgn
import chess.engine
import sqlite3
import json
import io
from config import STOCKFISH_PATH, DATABASE_PATH
from data_collector import extract_features


def import_with_features(zst_file, max_games=500, label="Human", agent_type="RealHuman"):
    """Import games from a Lichess PGN .zst file, computing features on the fly."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    game_count = 0

    dctx = zstd.ZstdDecompressor()
    try:
        with open(zst_file, 'rb') as fh:
            reader = dctx.stream_reader(fh)
            text_stream = io.TextIOWrapper(reader, encoding='utf-8', errors='ignore')

            while game_count < max_games:
                game = chess.pgn.read_game(text_stream)
                if game is None:
                    break

                board = game.board()
                moves = list(game.mainline_moves())
                if not moves:
                    continue

                moves_log = []
                skip_game = False
                for move in moves:
                    try:
                        feat = extract_features(board.copy(), move, engine)
                    except Exception as e:
                        print(f"Feature extraction failed for {move.uci()}: {e}, using zeros.")
                        feat = (0.0, 0.0, 0.0, 0.0)
                    moves_log.append({
                        "move": move.uci(),
                        "side": "white" if board.turn == chess.WHITE else "black",
                        "move_number": board.fullmove_number,
                        "features": list(feat)
                    })
                    board.push(move)

                result = game.headers.get("Result", "*")
                exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
                pgn_string = game.accept(exporter)

                c.execute(
                    "INSERT INTO games (pgn, white_label, black_label, white_agent, black_agent, result, moves_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (pgn_string, label, label, agent_type, agent_type, result, json.dumps(moves_log))
                )
                game_id = c.lastrowid
                for m in moves_log:
                    cpl, sim, ent, spike = m["features"]
                    c.execute(
                        "INSERT INTO move_features "
                        "(game_id, move_number, side, move_san, centipawn_loss, engine_similarity, move_entropy, tactical_spike) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (game_id, m["move_number"], m["side"], m["move"], cpl, sim, ent, spike)
                    )
                conn.commit()

                game_count += 1
                print(f"Imported game {game_count}/{max_games}")
    finally:
        engine.quit()
        conn.close()

    print(f"Done. {game_count} games imported with features.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import games from a Lichess PGN .zst file with feature extraction"
    )
    parser.add_argument(
        "zst_file",
        help="Path to the .pgn.zst file"
    )
    parser.add_argument(
        "--games", type=int, default=500,
        help="Maximum number of games to import (default: 500)"
    )
    args = parser.parse_args()
    import_with_features(args.zst_file, max_games=args.games)