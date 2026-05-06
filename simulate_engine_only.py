import argparse
import random
import time
import chess.engine
from engine_arena import ChessArena
from attacker_simulation import FullEngineAgent, TacticalAssistAgent, NoiseInjectionAgent
from data_collector import init_db
import config


def run_engine_only(total_games, time_limit=0.2):
    """Generate engine‑vs‑engine games to collect engine‑labeled moves."""
    try:
        test_engine = chess.engine.SimpleEngine.popen_uci(config.STOCKFISH_PATH)
        test_engine.quit()
    except Exception as e:
        print(f"Stockfish unavailable: {e}")
        return

    init_db()
    agents = [FullEngineAgent, TacticalAssistAgent, NoiseInjectionAgent]
    original_limit = config.ENGINE_TIME_LIMIT
    config.ENGINE_TIME_LIMIT = time_limit

    for i in range(total_games):
        cls_w = random.choice(agents)
        cls_b = random.choice(agents)
        white = cls_w()
        black = cls_b()

        arena = ChessArena(white, black)
        try:
            result, _, _ = arena.play_game(human_move_callback=None)
            arena.save_game_to_db("Engine", "Engine",
                                  white.__class__.__name__, black.__class__.__name__,
                                  result)
            print(f"Game {i+1}/{total_games} complete: {result}", flush=True)
        except Exception as e:
            print(f"Game {i+1} failed: {e}", flush=True)
        finally:
            white.close()
            black.close()
        time.sleep(0.01)

    config.ENGINE_TIME_LIMIT = original_limit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect engine vs engine game data")
    parser.add_argument("--games", type=int, default=50, help="Number of games to play")
    parser.add_argument("--fast", action="store_true", help="Use 0.05s engine time limit")
    args = parser.parse_args()
    time_limit = 0.05 if args.fast else 0.2
    print(f"ENGINE_TIME_LIMIT = {time_limit}")
    run_engine_only(args.games, time_limit)