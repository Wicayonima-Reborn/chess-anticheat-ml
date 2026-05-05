import sqlite3

conn = sqlite3.connect("data/games.db")
c = conn.cursor()

# --------- Games ---------
c.execute("SELECT COUNT(*) FROM games WHERE white_label='Human' OR black_label='Human'")
human_games = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM games WHERE white_label='Engine' AND black_label='Engine'")
engine_games = c.fetchone()[0]

# --------- Moves ---------
c.execute("""
    SELECT COUNT(*) FROM move_features mf
    JOIN games g ON mf.game_id = g.id
    WHERE (mf.side='white' AND g.white_label='Human')
       OR (mf.side='black' AND g.black_label='Human')
""")
human_moves = c.fetchone()[0]

c.execute("""
    SELECT COUNT(*) FROM move_features mf
    JOIN games g ON mf.game_id = g.id
    WHERE (mf.side='white' AND g.white_label='Engine')
       OR (mf.side='black' AND g.black_label='Engine')
""")
engine_moves = c.fetchone()[0]

conn.close()

total_games = human_games + engine_games
total_moves = human_moves + engine_moves
ratio = human_moves / engine_moves if engine_moves > 0 else float('inf')

print(f"Games with Human player(s) : {human_games}")
print(f"Engine vs Engine games     : {engine_games}")
print(f"Total games                : {total_games}")
print()
print(f"Total Human moves          : {human_moves}")
print(f"Total Engine moves         : {engine_moves}")
print(f"Total moves                : {total_moves}")
print(f"Human:Engine ratio         : {ratio:.1f} : 1")