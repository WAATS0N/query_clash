import sqlite3
import json

db_path = 'query_clash/database.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Get all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [row[0] for row in c.fetchall()]

schema = {}
hidden_tables = ['participants', 'investigations', 'investigation_progress', 'submissions']

for table in tables:
    if table in hidden_tables:
        continue
        
    c.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in c.fetchall()]
    schema[table] = columns

print(json.dumps(schema, indent=2))
conn.close()
