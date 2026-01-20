import sqlite3
import json
import os

db_path = os.path.join('sql-mysteries-master', 'sql-murder-mystery.db')
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]

schema = {}
for table in tables:
    cursor.execute(f"PRAGMA table_info({table});")
    schema[table] = [row[1] for row in cursor.fetchall()]

# Get initial clue
cursor.execute("SELECT * FROM crime_scene_report WHERE date = 20180115 AND city = 'SQL City' AND type = 'murder';")
clues = cursor.fetchall()

# Get solution check logic (if possible)
cursor.execute("SELECT * FROM solution;")
solution_rows = cursor.fetchall()

print(json.dumps({'tables': tables, 'schema': schema, 'clues': clues, 'solution_rows': solution_rows}, indent=2))
conn.close()
