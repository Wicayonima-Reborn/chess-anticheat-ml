import chess
import chess.pgn
import chess.engine
import sqlite3
import json
from data_collector import extract_features, DATABASE_PATH
from config import STOCKFISH_PATH
from attacker_simulation import HumanProxyAgent


class ChessArena:
    def __init__(self, white_agent, black_agent):
        self.white = white_agent
        self.black = black_agent
        self.board = chess.Board()
        self.moves_log = []

    def play_game(self, human_move_callback=None):
        """Run a full game, return (result, moves_log, final_board)."""
        engine_analysis = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        try:
            while not self.board.is_game_over(claim_draw=True):
                agent = self.white if self.board.turn == chess.WHITE else self.black

                if isinstance(agent, HumanProxyAgent) and human_move_callback:
                    uci = human_move_callback(self.board)
                    move = agent.get_move(self.board, move_uci=uci)
                else:
                    move = agent.get_move(self.board)

                if move is None:
                    break

                features = extract_features(self.board.copy(), move, engine_analysis)
                self.moves_log.append({
                    "move": move.uci(),
                    "side": "white" if self.board.turn == chess.WHITE else "black",
                    "move_number": self.board.fullmove_number,
                    "features": list(features)
                })
                self.board.push(move)

            return self.board.result(), self.moves_log, self.board
        finally:
            try:
                engine_analysis.quit()
            except Exception:
                pass

    def save_game_to_db(self, white_label, black_label,
                        white_agent_type, black_agent_type, result):
        """Persist the played game and its move features to the database."""
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        game = chess.pgn.Game.from_board(self.board)
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        pgn_string = game.accept(exporter)

        c.execute(
            "INSERT INTO games (pgn, white_label, black_label, white_agent, black_agent, result, moves_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (pgn_string, white_label, black_label,
             white_agent_type, black_agent_type, result,
             json.dumps(self.moves_log))
        )
        game_id = c.lastrowid

        for move_data in self.moves_log:
            cpl, sim, ent, spike = move_data["features"]
            c.execute(
                "INSERT INTO move_features "
                "(game_id, move_number, side, move_san, centipawn_loss, engine_similarity, move_entropy, tactical_spike) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (game_id, move_data["move_number"], move_data["side"], move_data["move"],
                 cpl, sim, ent, spike)
            )
        conn.commit()
        conn.close()