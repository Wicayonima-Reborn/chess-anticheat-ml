import chess
import chess.pgn
import io
import json
import sqlite3
from data_collector import extract_features, DATABASE_PATH, init_db
from config import ENGINE_TIME_LIMIT, STOCKFISH_PATH
from attacker_simulation import HumanProxyAgent

class ChessArena:
    def __init__(self, white_agent, black_agent):
        self.white = white_agent
        self.black = black_agent
        self.board = chess.Board()
        self.moves_log = []

    def play_game(self, human_move_callback=None):
        engine_analysis = None
        try:
            engine_analysis = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
            while not self.board.is_game_over(claim_draw=True):
                agent = self.white if self.board.turn == chess.WHITE else self.black
                move = None
                if isinstance(agent, HumanProxyAgent) and human_move_callback:
                    uci = human_move_callback(self.board)
                    move = agent.get_move(self.board, move_uci=uci)
                else:
                    move = agent.get_move(self.board)

                if move is None:
                    break  # tidak ada langkah

                features = extract_features(self.board.copy(), move, engine_analysis)
                self.moves_log.append({
                    "move": move.uci(),
                    "side": "white" if self.board.turn == chess.WHITE else "black",
                    "move_number": self.board.fullmove_number,
                    "features": list(features)
                })
                self.board.push(move)

            result = self.board.result()
            return result, self.moves_log, self.board
        except Exception as e:
            print(f"Error during play_game: {e}")
            raise
        finally:
            if engine_analysis:
                try:
                    engine_analysis.quit()
                except:
                    pass

    def save_game_to_db(self, white_label, black_label, white_agent_type, black_agent_type, result):
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        game = chess.pgn.Game.from_board(self.board)
        pgn_string = game.accept(exporter)

        c.execute("INSERT INTO games (pgn, white_label, black_label, white_agent, black_agent, result, moves_json) VALUES (?,?,?,?,?,?,?)",
                  (pgn_string, white_label, black_label, white_agent_type, black_agent_type, result, json.dumps(self.moves_log)))
        game_id = c.lastrowid

        for move_data in self.moves_log:
            cpl, sim, ent, spike = move_data["features"]
            c.execute("INSERT INTO move_features (game_id, move_number, side, move_san, centipawn_loss, engine_similarity, move_entropy, tactical_spike) VALUES (?,?,?,?,?,?,?,?)",
                      (game_id, move_data["move_number"], move_data["side"], move_data["move"], cpl, sim, ent, spike))
        conn.commit()
        conn.close()