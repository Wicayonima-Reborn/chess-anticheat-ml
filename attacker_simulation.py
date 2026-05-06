import chess
import chess.engine
import random
from config import STOCKFISH_PATH, ENGINE_TIME_LIMIT


class BaseAgent:
    def __init__(self, name="Agent", engine_path=STOCKFISH_PATH):
        self.name = name
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)

    def get_move(self, board, *args, **kwargs):
        raise NotImplementedError

    def close(self):
        try:
            self.engine.quit()
        except Exception:
            pass


class FullEngineAgent(BaseAgent):
    """Always picks the engine's top move."""
    def get_move(self, board):
        result = self.engine.play(board, chess.engine.Limit(time=ENGINE_TIME_LIMIT))
        return result.move


class TacticalAssistAgent(BaseAgent):
    """Uses the engine only when the position has a large eval gap among top moves."""
    def __init__(self, name="TacticalAssist", engine_path=STOCKFISH_PATH, threshold=150):
        super().__init__(name, engine_path)
        self.threshold = threshold

    def get_move(self, board):
        try:
            multipv = self.engine.analyse(board, chess.engine.Limit(time=ENGINE_TIME_LIMIT), multipv=5)
            scores = [
                pv["score"].relative.score(mate_score=10000) or 0
                for pv in multipv if "pv" in pv and pv["pv"]
            ]
            if scores and (max(scores) - min(scores) > self.threshold):
                return self.engine.play(board, chess.engine.Limit(time=ENGINE_TIME_LIMIT)).move
            return random.choice(list(board.legal_moves))
        except Exception:
            return random.choice(list(board.legal_moves))


class NoiseInjectionAgent(BaseAgent):
    """Occasionally plays a suboptimal move to mimic human inconsistency."""
    def __init__(self, name="NoiseAgent", engine_path=STOCKFISH_PATH, noise_prob=0.3):
        super().__init__(name, engine_path)
        self.noise_prob = noise_prob

    def get_move(self, board):
        try:
            if random.random() < self.noise_prob:
                info = self.engine.analyse(board, chess.engine.Limit(time=ENGINE_TIME_LIMIT), multipv=10)
                suboptimal = [pv["pv"][0] for pv in info[1:] if "pv" in pv and pv["pv"]]
                if suboptimal:
                    return random.choice(suboptimal)
            return self.engine.play(board, chess.engine.Limit(time=ENGINE_TIME_LIMIT)).move
        except Exception:
            return random.choice(list(board.legal_moves))


class HumanProxyAgent(BaseAgent):
    """Takes a move from an external source (GUI/console). Falls back to random."""
    def get_move(self, board, move_uci=None):
        if move_uci:
            return chess.Move.from_uci(move_uci)
        return random.choice(list(board.legal_moves))


class MixedHumanAgent(BaseAgent):
    """Simulates a casual player using simple material counting with occasional blunders."""
    def __init__(self, name="MixedHuman", engine_path=STOCKFISH_PATH, random_prob=0.3):
        super().__init__(name, engine_path)
        self.random_prob = random_prob

    def _material_score(self, board):
        piece_values = {
            chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
            chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0
        }
        score = 0
        for piece, value in piece_values.items():
            score += len(board.pieces(piece, chess.WHITE)) * value
            score -= len(board.pieces(piece, chess.BLACK)) * value
        return score

    def get_move(self, board):
        if random.random() < self.random_prob:
            return random.choice(list(board.legal_moves))

        legal_moves = list(board.legal_moves)
        best_move = None
        best_score = None
        player = board.turn

        for move in legal_moves:
            board.push(move)
            score = self._material_score(board)  # positive means white advantage
            board.pop()
            if player == chess.WHITE:
                if best_score is None or score > best_score:
                    best_score = score
                    best_move = move
            else:
                if best_score is None or score < best_score:
                    best_score = score
                    best_move = move

        return best_move if best_move else random.choice(legal_moves)
