import sys
import chess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QGroupBox, QGridLayout,
    QSplitter, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QFont

from data_collector import extract_features, init_db
from attacker_simulation import (
    FullEngineAgent, TacticalAssistAgent, NoiseInjectionAgent, HumanProxyAgent
)
from anti_cheat_detector import load_model, predict_move
from config import STOCKFISH_PATH

init_db()


# ======================= Dialog Promosi =======================
class PromotionDialog(QDialog):
    """Dialog kecil untuk memilih buah promosi."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Promotion")
        self.selected_piece = chess.QUEEN  # default

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose promotion piece:"))

        # Tombol dengan simbol Unicode
        pieces = [
            ("Queen ♕", chess.QUEEN),
            ("Rook ♖", chess.ROOK),
            ("Bishop ♗", chess.BISHOP),
            ("Knight ♘", chess.KNIGHT),
        ]
        for text, piece in pieces:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, p=piece: self._select(p))
            layout.addWidget(btn)

    def _select(self, piece):
        self.selected_piece = piece
        self.accept()


# ======================= Papan Catur =======================
class ChessBoardWidget(QWidget):
    piece_selected = Signal(int, int)
    move_made = Signal(str)             # UCI

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.board = chess.Board()
        self.flipped = False
        self.selected_square = None
        self.highlight_squares = []
        self.hover_square = None
        self.setMouseTracking(True)

    def set_board(self, fen):
        self.board.set_fen(fen)
        self.selected_square = None
        self.highlight_squares = []
        self.hover_square = None
        self.update()

    def set_flipped(self, flipped):
        self.flipped = flipped
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        size = min(self.width(), self.height())
        sq_size = size / 8.0

        light = QColor("#F0D9B5")
        dark = QColor("#B58863")
        hl = QColor(255, 255, 0, 100)
        sel = QColor(0, 255, 0, 120)
        hov = QColor(100, 150, 255, 80)

        for row_vis in range(8):
            for col_vis in range(8):
                x = col_vis * sq_size
                y = row_vis * sq_size
                rect = (x, y, sq_size, sq_size)
                if (row_vis + col_vis) % 2 == 0:
                    painter.fillRect(*rect, light)
                else:
                    painter.fillRect(*rect, dark)

                # Konversi visual → square sesungguhnya
                if not self.flipped:
                    file = col_vis
                    rank = 7 - row_vis
                else:
                    file = 7 - col_vis
                    rank = row_vis
                square = chess.square(file, rank)

                if square == self.selected_square:
                    painter.fillRect(*rect, sel)
                elif square in self.highlight_squares:
                    painter.fillRect(*rect, hl)
                elif square == self.hover_square:
                    painter.fillRect(*rect, hov)

        # Gambar bidak
        painter.setFont(QFont("Arial", int(sq_size * 0.75), QFont.Bold))
        piece_map = self.board.piece_map()
        for square, piece in piece_map.items():
            file = chess.square_file(square)
            rank = chess.square_rank(square)   # 0 = rank 1
            if not self.flipped:
                col_vis = file
                row_vis = 7 - rank
            else:
                col_vis = 7 - file
                row_vis = rank
            x = col_vis * sq_size + sq_size * 0.15
            y = row_vis * sq_size + sq_size * 0.85
            painter.drawText(QPointF(x, y), piece.unicode_symbol())

        painter.end()

    def _pos_to_square(self, pos: QPointF):
        size = min(self.width(), self.height())
        sq_size = size / 8.0
        if pos.x() < 0 or pos.y() < 0 or pos.x() >= size or pos.y() >= size:
            return None
        col_vis = int(pos.x() // sq_size)
        row_vis = int(pos.y() // sq_size)
        if not self.flipped:
            file = col_vis
            rank = 7 - row_vis
        else:
            file = 7 - col_vis
            rank = row_vis
        if not (0 <= file <= 7 and 0 <= rank <= 7):
            return None
        return chess.square(file, rank)

    def mousePressEvent(self, event):
        if self.board.is_game_over():
            return
        square = self._pos_to_square(event.position())
        if square is None:
            return

        if self.selected_square is not None:
            # Coba langkah biasa dulu
            move = chess.Move(self.selected_square, square)
            if move in self.board.legal_moves:
                self.move_made.emit(move.uci())
                self.selected_square = None
                self.highlight_squares = []
                self.update()
                return

            # Cek apakah ini langkah promosi (pion ke baris terakhir)
            promotion_moves = [
                chess.Move(self.selected_square, square, promotion=p)
                for p in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
            ]
            legal_promotions = [m for m in promotion_moves if m in self.board.legal_moves]

            if legal_promotions:
                # Tampilkan dialog pilihan
                dlg = PromotionDialog(self)
                if dlg.exec() == QDialog.Accepted:
                    chosen_piece = dlg.selected_piece
                    move = chess.Move(self.selected_square, square, promotion=chosen_piece)
                    if move in self.board.legal_moves:
                        self.move_made.emit(move.uci())
                        self.selected_square = None
                        self.highlight_squares = []
                        self.update()
                        return

            # Tidak legal, hapus seleksi
            self.selected_square = None
            self.highlight_squares = []
            self.update()
        else:
            # Pilih bidak sendiri
            piece = self.board.piece_at(square)
            if piece and piece.color == self.board.turn:
                self.selected_square = square
                self.highlight_squares = [
                    move.to_square for move in self.board.legal_moves
                    if move.from_square == square
                ]
                self.update()
                self.piece_selected.emit(chess.square_file(square),
                                         chess.square_rank(square))

    def mouseMoveEvent(self, event):
        square = self._pos_to_square(event.position())
        if square != self.hover_square:
            self.hover_square = square
            self.update()

    def leaveEvent(self, event):
        self.hover_square = None
        self.update()


# ======================= Panel Kontrol =======================
class ControlPanel(QWidget):
    new_game_clicked = Signal()
    next_move_clicked = Signal()
    flip_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        agent_group = QGroupBox("Agent Selection")
        agent_layout = QGridLayout()
        agent_layout.addWidget(QLabel("White:"), 0, 0)
        self.white_agent = QComboBox()
        self.white_agent.addItems(["Human", "Full Engine", "Tactical Assist", "Noise Agent"])
        agent_layout.addWidget(self.white_agent, 0, 1)
        agent_layout.addWidget(QLabel("Black:"), 1, 0)
        self.black_agent = QComboBox()
        self.black_agent.addItems(["Human", "Full Engine", "Tactical Assist", "Noise Agent"])
        agent_layout.addWidget(self.black_agent, 1, 1)
        agent_group.setLayout(agent_layout)
        layout.addWidget(agent_group)

        btn_layout = QHBoxLayout()
        self.new_game_btn = QPushButton("New Game")
        self.new_game_btn.clicked.connect(self.new_game_clicked.emit)
        btn_layout.addWidget(self.new_game_btn)

        self.flip_btn = QPushButton("Flip Board")
        self.flip_btn.clicked.connect(self.flip_clicked.emit)
        btn_layout.addWidget(self.flip_btn)

        self.next_move_btn = QPushButton("Next Move")
        self.next_move_btn.clicked.connect(self.next_move_clicked.emit)
        btn_layout.addWidget(self.next_move_btn)
        layout.addLayout(btn_layout)

        self.status_label = QLabel("White to move")
        layout.addWidget(self.status_label)

        detect_group = QGroupBox("Move Detection")
        detect_layout = QVBoxLayout()
        self.detect_label = QLabel("None")
        self.detect_label.setAlignment(Qt.AlignCenter)
        self.detect_label.setStyleSheet("font-weight: bold; padding: 4px;")
        detect_layout.addWidget(self.detect_label)
        self.detect_conf = QLabel("")
        detect_layout.addWidget(self.detect_conf)
        detect_group.setLayout(detect_layout)
        layout.addWidget(detect_group)

        layout.addStretch()

    def set_status(self, text):
        self.status_label.setText(text)

    def set_detection(self, label, confidence):
        self.detect_label.setText(label)
        if "Engine" in label:
            self.detect_label.setStyleSheet("background-color: #ffcccc; font-weight: bold;")
        elif "Suspicious" in label:
            self.detect_label.setStyleSheet("background-color: #ffffcc; font-weight: bold;")
        else:
            self.detect_label.setStyleSheet("background-color: #ccffcc; font-weight: bold;")
        self.detect_conf.setText(f"Confidence: {confidence:.2f}")

    def get_agent_selection(self):
        return self.white_agent.currentText(), self.black_agent.currentText()


# ======================= Jendela Utama =======================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chess Adversarial Lab")
        self.resize(1000, 600)

        self.board = chess.Board()
        self.white_agent = None
        self.black_agent = None
        self.game_active = False
        self.model = load_model()

        self.board_widget = ChessBoardWidget()
        self.control_panel = ControlPanel()
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.board_widget)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.control_panel)
        right_layout.addWidget(QLabel("Move Log:"))
        right_layout.addWidget(self.log_widget)
        splitter.addWidget(right)
        splitter.setSizes([600, 400])

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.addWidget(splitter)
        self.setCentralWidget(central)

        self.control_panel.new_game_clicked.connect(self.new_game)
        self.control_panel.next_move_clicked.connect(self.next_move)
        self.control_panel.flip_clicked.connect(self.flip_board)
        self.board_widget.move_made.connect(self.handle_human_move)

        self.new_game()

    def new_game(self):
        white_choice, black_choice = self.control_panel.get_agent_selection()
        self.white_agent = self._create_agent(white_choice, "white")
        self.black_agent = self._create_agent(black_choice, "black")
        self.board.reset()
        self.board_widget.set_board(self.board.fen())
        self.game_active = True
        self.log_widget.clear()
        self.log(f"New game: {white_choice} vs {black_choice}")
        self.update_status()
        self.control_panel.set_detection("None", 0.0)

    def _create_agent(self, name, color):
        if name == "Human":
            return HumanProxyAgent(name=f"Human_{color}")
        elif name == "Full Engine":
            return FullEngineAgent(name=f"FullEngine_{color}")
        elif name == "Tactical Assist":
            return TacticalAssistAgent(name=f"Tactical_{color}")
        elif name == "Noise Agent":
            return NoiseInjectionAgent(name=f"Noise_{color}")
        else:
            return HumanProxyAgent()

    def next_move(self):
        if not self.game_active or self.board.is_game_over():
            return
        agent = self.white_agent if self.board.turn == chess.WHITE else self.black_agent
        if isinstance(agent, HumanProxyAgent):
            return

        try:
            move = agent.get_move(self.board)
            if move is None:
                self.log("Bot returned no move (None). Check engine.")
                return
            if move not in self.board.legal_moves:
                self.log(f"Bot returned illegal move: {move.uci()}. Skipping.")
                return
            self.apply_move(move)
        except Exception as e:
            self.log(f"Bot error: {e}")
            # Opsional: ganti ke random legal move agar game tetap jalan
            # move = random.choice(list(self.board.legal_moves))
            # self.apply_move(move)

        if self.board.is_game_over():
            self.end_game()

    def handle_human_move(self, uci):
        if not self.game_active or self.board.is_game_over():
            return
        agent = self.white_agent if self.board.turn == chess.WHITE else self.black_agent
        if not isinstance(agent, HumanProxyAgent):
            return
        try:
            move = chess.Move.from_uci(uci)
            if move in self.board.legal_moves:
                self.apply_move(move)
            else:
                self.log("Illegal move.")
        except:
            pass

    def apply_move(self, move):
        try:
            import chess.engine as ce
            with ce.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
                features = extract_features(self.board.copy(), move, engine)
        except Exception as e:
            self.log(f"Feature engine error: {e}")
            features = (0, 0, 0, 0)

        cpl, sim, entropy, spike = features
        uci = move.uci()
        self.board.push(move)
        self.board_widget.set_board(self.board.fen())
        self.log(f"{self.board.fullmove_number}.{'...' if self.board.turn == chess.WHITE else '.'} {uci}  (CPL={cpl:.1f})")

        if self.model:
            label, proba = predict_move([cpl, sim, entropy, spike], self.model)
            self.control_panel.set_detection(label, max(proba))
        else:
            self.control_panel.set_detection("No model", 0.0)

        self.update_status()
        if self.board.is_game_over():
            self.end_game()

    def update_status(self):
        if self.board.is_game_over():
            self.control_panel.set_status(f"Game Over: {self.board.result()}")
        else:
            turn = "White" if self.board.turn == chess.WHITE else "Black"
            self.control_panel.set_status(f"{turn} to move")

    def end_game(self):
        result = self.board.result()
        self.log(f"Game ended: {result}")
        self.game_active = False
        self.control_panel.set_status(f"Game Over: {result}")

    def flip_board(self):
        self.board_widget.set_flipped(not self.board_widget.flipped)

    def log(self, msg):
        self.log_widget.append(msg)

    def closeEvent(self, event):
        for agent in (self.white_agent, self.black_agent):
            if agent and hasattr(agent, 'close'):
                agent.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())