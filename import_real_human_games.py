import zstandard as zstd
import chess.pgn
import chess.engine
import sqlite3
import json
import io
from config import STOCKFISH_PATH, DATABASE_PATH
from data_collector import extract_features

def import_first_n_games(zst_file, max_games=500, label="Human", agent_type="RealHuman"):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

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
            if len(moves) == 0:
                continue

            moves_log = []
            try:
                for move in moves:
                    feat = extract_features(board.copy(), move, engine)
                    moves_log.append({
                        "move": move.uci(),
                        "side": "white" if board.turn == chess.WHITE else "black",
                        "move_number": board.fullmove_number,
                        "features": list(feat)
                    })
                    board.push(move)
            except Exception as e:
                print(f"Game {game_count+1}: error fitur -> {e}, skip.")
                continue

            result = game.headers.get("Result", "*")
            exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
            pgn_string = game.accept(exporter)

            c.execute("INSERT INTO games (pgn, white_label, black_label, white_agent, black_agent, result, moves_json) VALUES (?,?,?,?,?,?,?)",
                      (pgn_string, label, label, agent_type, agent_type, result, json.dumps(moves_log)))
            game_id = c.lastrowid
            for m in moves_log:
                cpl, sim, ent, spike = m["features"]
                c.execute("INSERT INTO move_features (game_id, move_number, side, move_san, centipawn_loss, engine_similarity, move_entropy, tactical_spike) VALUES (?,?,?,?,?,?,?,?)",
                          (game_id, m["move_number"], m["side"], m["move"], cpl, sim, ent, spike))
            conn.commit()

            game_count += 1
            print(f"Imported game {game_count}/{max_games}")

    engine.quit()
    conn.close()
    print(f"Selesai. {game_count} game diimpor.")

if __name__ == "__main__":
    import_first_n_games("lichess_db_standard_rated_2015-11.pgn.zst", max_games=500)