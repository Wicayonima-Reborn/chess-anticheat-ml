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
    """Selalu ambil best move engine."""
    def get_move(self, board):
        result = self.engine.play(board, chess.engine.Limit(time=ENGINE_TIME_LIMIT))
        return result.move

class TacticalAssistAgent(BaseAgent):
    """Hanya pakai engine saat posisi dianggap rumit (tactical spike besar)."""
    def __init__(self, name="TacticalAssist", engine_path=STOCKFISH_PATH, threshold=150):
        super().__init__(name, engine_path)
        self.threshold = threshold

    def get_move(self, board):
        # Evaluasi posisi untuk menentukan komplesitas
        info = self.engine.analyse(board, chess.engine.Limit(time=ENGINE_TIME_LIMIT))
        score = info["score"].relative.score(mate_score=10000) or 0
        # Simulasi tactical spike dengan cek apakah ada banyak kandidat move dengan variasi skor
        multipv = self.engine.analyse(board, chess.engine.Limit(time=ENGINE_TIME_LIMIT), multipv=5)
        scores = []
        for pv in multipv:
            if "pv" in pv and len(pv["pv"]) > 0:
                s = pv["score"].relative.score(mate_score=10000) or 0
                scores.append(s)
        if scores:
            score_range = max(scores) - min(scores)
        else:
            score_range = 0

        if score_range > self.threshold:
            # Posisi rumit, gunakan engine
            return self.engine.play(board, chess.engine.Limit(time=ENGINE_TIME_LIMIT)).move
        else:
            # Posisi tenang, random legal move (manusia simulasi)
            legal_moves = list(board.legal_moves)
            return random.choice(legal_moves)

class NoiseInjectionAgent(BaseAgent):
    """Sengaja beri move suboptimal dengan probabilitas tertentu."""
    def __init__(self, name="NoiseAgent", engine_path=STOCKFISH_PATH, noise_prob=0.3):
        super().__init__(name, engine_path)
        self.noise_prob = noise_prob

    def get_move(self, board):
        if random.random() < self.noise_prob:
            # Pilih move suboptimal dari legal moves, bukan yang terbaik
            info = self.engine.analyse(board, chess.engine.Limit(time=ENGINE_TIME_LIMIT), multipv=10)
            # Ambil move ke-2 sampai terburuk (skip best)
            suboptimal = [pv["pv"][0] for pv in info[1:] if "pv" in pv and len(pv["pv"])>0]
            if suboptimal:
                return random.choice(suboptimal)
        # Fallback ke best move
        return self.engine.play(board, chess.engine.Limit(time=ENGINE_TIME_LIMIT)).move

class HumanProxyAgent(BaseAgent):
    """Agent yang menerima input dari luar (console/GUI)."""
    def get_move(self, board, move_uci=None):
        if move_uci:
            return chess.Move.from_uci(move_uci)
        # Fallback random legal move (hanya untuk simulasi)
        return random.choice(list(board.legal_moves))

class MixedHumanAgent(BaseAgent):
    """Simulasi manusia amatir: 70% langkah berdasarkan hitung material sederhana, 30% random."""
    def __init__(self, name="MixedHuman", engine_path=STOCKFISH_PATH, random_prob=0.3):
        super().__init__(name, engine_path)
        self.random_prob = random_prob

    def _material_score(self, board):
        """Evaluasi sederhana: hitung total material (pawn=1, knight/bishop=3, rook=5, queen=9)."""
        values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                  chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
        score = 0
        for piece_type in values:
            score += len(board.pieces(piece_type, chess.WHITE)) * values[piece_type]
            score -= len(board.pieces(piece_type, chess.BLACK)) * values[piece_type]
        return score

    def get_move(self, board):
        if random.random() < self.random_prob:
            # Langkah random (blunder)
            return random.choice(list(board.legal_moves))
        else:
            # Langkah berdasarkan evaluasi material sederhana
            legal_moves = list(board.legal_moves)
            best_move = None
            best_score = -float('inf') if board.turn == chess.WHITE else float('inf')
            for move in legal_moves:
                board.push(move)
                score = self._material_score(board)
                board.pop()
                if board.turn == chess.WHITE:   # board.turn sekarang adalah warna yang baru bergerak? 
                    # Setelah push, sekarang giliran lawan. board.turn adalah lawan.
                    # Kita evaluasi dari sisi pemain awal.
                    # Jika pemain awal putih: kita ingin memaksimalkan skor setelah langkah.
                    # board.turn setelah push adalah hitam, artinya giliran hitam.
                    # Skor positif berarti putih unggul material.
                    # Jadi untuk putih, kita cari skor tertinggi; untuk hitam, terendah.
                    pass  # akan ditangani oleh if di luar loop.

            # Perbaikan logika maks/min
            best_move = None
            best_score = None
            for move in legal_moves:
                board.push(move)
                score = self._material_score(board)
                board.pop()
                if board.turn == chess.WHITE:  # setelah push, sekarang giliran white? Tidak, setelah push, giliran lawan.
                    # Biar sederhana: _material_score sudah memberikan nilai dari sudut putih.
                    # Jika pemain yang melangkah adalah putih, dia ingin skor setinggi mungkin.
                    # Jika hitam, dia ingin skor serendah mungkin.
                    if best_score is None or (board.turn == chess.BLACK and score > best_score) or (board.turn == chess.WHITE and score < best_score):
                        # Koreksi: board.turn setelah push adalah warna lawan. Jadi pemain yang baru bergerak adalah warna sebaliknya.
                        # Misal pemain putih: setelah push, board.turn = BLACK. Maka pemain putih menginginkan skor tinggi (dari sudut putih). Jadi pada saat evaluasi sebagai putih, kita cari score tertinggi.
                        # Kita perlu tahu warna pemain. Gunakan board_before.turn.
                        pass
            # Implementasi yang lebih bersih:
            best_move = None
            best_score = None
            turn = board.turn
            for move in legal_moves:
                board.push(move)
                score = self._material_score(board)  # selalu dari sudut putih: + berarti putih unggul
                board.pop()
                if turn == chess.WHITE:
                    # putih mencari skor tertinggi
                    if best_score is None or score > best_score:
                        best_score = score
                        best_move = move
                else:
                    # hitam mencari skor terendah
                    if best_score is None or score < best_score:
                        best_score = score
                        best_move = move
            return best_move if best_move else random.choice(legal_moves)