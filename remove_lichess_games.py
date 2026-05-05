import sqlite3
import sys

def remove_n_lichess_games(n=25):
    conn = sqlite3.connect("data/games.db")
    c = conn.cursor()
    c.execute("SELECT id FROM games WHERE white_agent='RealHuman' ORDER BY id LIMIT ?", (n,))
    ids = [row[0] for row in c.fetchall()]
    if not ids:
        print("Tidak ada game Lichess untuk dihapus.")
        conn.close()
        return
    c.executemany("DELETE FROM move_features WHERE game_id=?", [(i,) for i in ids])
    c.executemany("DELETE FROM games WHERE id=?", [(i,) for i in ids])
    conn.commit()
    conn.close()
    print(f"Berhasil menghapus {len(ids)} game Lichess.")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    remove_n_lichess_games(n)