import sqlite3
import sys

def remove_n_lichess_games(n=25):
    """Remove the first n Lichess games (RealHuman agent) from the database."""
    conn = sqlite3.connect("data/games.db")
    c = conn.cursor()
    c.execute("SELECT id FROM games WHERE white_agent='RealHuman' ORDER BY id LIMIT ?", (n,))
    ids = [row[0] for row in c.fetchall()]
    if not ids:
        print("No Lichess games to remove.")
        conn.close()
        return
    c.executemany("DELETE FROM move_features WHERE game_id=?", [(i,) for i in ids])
    c.executemany("DELETE FROM games WHERE id=?", [(i,) for i in ids])
    conn.commit()
    conn.close()
    print(f"Removed {len(ids)} Lichess games.")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    remove_n_lichess_games(n)