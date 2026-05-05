import argparse
from engine_arena import ChessArena
from attacker_simulation import (FullEngineAgent, TacticalAssistAgent,
                                 NoiseInjectionAgent, HumanProxyAgent,
                                 MixedHumanAgent)
from data_collector import init_db
from anti_cheat_detector import train_model, predict_move, load_model
import random

def run_simulation(num_games, mode="train"):
    init_db()

    if mode == "interactive":
        print("=== Interactive Mode ===")
        print("Pilih lawan: 1. Full Engine, 2. Tactical Assist, 3. Noisy Bot")
        choice = input("> ")
        if choice == "1":
            opponent = FullEngineAgent()
            opp_label = "FullEngine"
        elif choice == "2":
            opponent = TacticalAssistAgent()
            opp_label = "TacticalAssist"
        else:
            opponent = NoiseInjectionAgent()
            opp_label = "NoiseAgent"

        human = HumanProxyAgent()
        arena = ChessArena(white_agent=human, black_agent=opponent) if random.choice([True, False]) else ChessArena(white_agent=opponent, black_agent=human)

        def human_move(board):
            print(board)
            print("Legal moves:", [move.uci() for move in board.legal_moves])
            uci = input("Your move (UCI): ").strip()
            return uci

        result, log, board = arena.play_game(human_move_callback=human_move)
        print("Result:", result)
        arena.save_game_to_db("Human", opp_label, "HumanProxy", opp_label, result)
        return

    agents = {
        "FullEngine": FullEngineAgent,
        "TacticalAssist": TacticalAssistAgent,
        "NoiseAgent": NoiseInjectionAgent,
    }

    print(f"Running {num_games} games for data collection...")
    for i in range(num_games):
        try:
            if random.random() < 0.9:
                white = MixedHumanAgent(name="Human_white")
                white_label = "Human"
                black_cls = random.choice(list(agents.values()))
                black = black_cls()
                black_label = "Engine"
            else:
                cls_w = random.choice(list(agents.values()))
                cls_b = random.choice(list(agents.values()))
                white = cls_w()
                black = cls_b()
                white_label = "Engine"
                black_label = "Engine"

            arena = ChessArena(white, black)
            result, log, board = arena.play_game(human_move_callback=None)
            arena.save_game_to_db(white_label, black_label,
                                  white.__class__.__name__, black.__class__.__name__,
                                  result)
            print(f"Game {i+1}/{num_games} complete: {result}")
        except Exception as e:
            print(f"Game {i+1} failed with error: {e}. Skipping.")
        finally:
            # Pastikan engine agent ditutup
            if white:
                white.close()
            if black:
                black.close()

    print("Data collection selesai. Melatih model...")
    train_model()

def detect_cheating(move_features):
    model = load_model()
    if model:
        label, proba = predict_move(move_features, model)
        print(f"Prediksi: {label}, Confidence: {max(proba):.2f}")
    else:
        print("Model belum dilatih. Jalankan training dulu.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chess Adversarial Lab")
    subparsers = parser.add_subparsers(dest="command")

    parser_sim = subparsers.add_parser("simulate", help="Kumpulkan data game")
    parser_sim.add_argument("--games", type=int, default=10, help="Jumlah game simulasi")
    parser_sim.add_argument("--interactive", action="store_true", help="Main manual vs bot")

    parser_detect = subparsers.add_parser("detect", help="Deteksi satu move (beri fitur manual)")
    parser_detect.add_argument("--cpl", type=float, required=True)
    parser_detect.add_argument("--sim", type=float, required=True)
    parser_detect.add_argument("--entropy", type=float, required=True)
    parser_detect.add_argument("--spike", type=float, required=True)

    parser_train = subparsers.add_parser("train", help="Latih model dari data yang ada")

    args = parser.parse_args()

    if args.command == "simulate":
        run_simulation(args.games, mode="interactive" if args.interactive else "train")
    elif args.command == "detect":
        detect_cheating([args.cpl, args.sim, args.entropy, args.spike])
    elif args.command == "train":
        train_model()
    else:   
        print("Gunakan: simulate, detect, atau train")