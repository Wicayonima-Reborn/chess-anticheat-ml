import argparse
import zstandard as zstd
import chess.pgn
import sqlite3
import json
import io
from config import DATABASE_PATH


def import_fast(zst_file, max_games=500, label="Human", agent_type="RealHuman"):
    """Import games from a Lichess PGN .zst file without calculating features."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    dctx = zstd.ZstdDecompressor()
    game_count = 0

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
            for move in moves:
                moves_log.append({
                    "move": move.uci(),
                    "side": "white" if board.turn == chess.WHITE else "black",
                    "move_number": board.fullmove_number,
                    "features": [0.0, 0.0, 0.0, 0.0]
                })
                board.push(move)

            result = game.headers.get("Result", "*")
            exporter = chess.pgn.StringExporter(
                headers=True, variations=False, comments=False
            )
            pgn_string = game.accept(exporter)

            c.execute(
                "INSERT INTO games (pgn, white_label, black_label, white_agent, black_agent, result, moves_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pgn_string, label, label, agent_type, agent_type, result, json.dumps(moves_log))
            )
            game_id = c.lastrowid
            for m in moves_log:
                c.execute(
                    "INSERT INTO move_features "
                    "(game_id, move_number, side, move_san, centipawn_loss, engine_similarity, move_entropy, tactical_spike) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (game_id, m["move_number"], m["side"], m["move"], 0.0, 0.0, 0.0, 0.0)
                )
            conn.commit()

            game_count += 1
            if game_count % 50 == 0:
                print(f"Imported {game_count}/{max_games} games...")

    conn.close()
    print(f"Imported {game_count} games (features not computed).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import games from a Lichess PGN .zst file"
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
    import_fast(args.zst_file, max_games=args.games)