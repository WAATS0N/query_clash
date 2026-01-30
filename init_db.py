import sqlite3
import os
import datetime

DB_PATH = 'database.db'
SOURCE_DB_PATH = 'sql-murder-mystery.db'

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Core Application Tables
    c.execute('''
        CREATE TABLE participants (
            name TEXT PRIMARY KEY,
            password TEXT,
            current_round INTEGER DEFAULT 1,
            round_start_time DATETIME,
            elapsed_time INTEGER DEFAULT 0,
            solved INTEGER DEFAULT 0,
            query_count INTEGER DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE investigations (
            id INTEGER PRIMARY KEY,
            round INTEGER,
            prompt TEXT,
            correct_answer TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE investigation_progress (
            name TEXT,
            investigation_id INTEGER,
            solved INTEGER DEFAULT 0,
            solved_at DATETIME,
            PRIMARY KEY (name, investigation_id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE submissions (
            name TEXT PRIMARY KEY,
            round INTEGER,
            final_answer TEXT,
            submission_time DATETIME,
            time_taken INTEGER
        )
    ''')

    # Migrate Mystery Data from Source DB
    if os.path.exists(SOURCE_DB_PATH):
        print(f"Migrating data from {SOURCE_DB_PATH}...")
        source_conn = sqlite3.connect(SOURCE_DB_PATH)
        source_cursor = source_conn.cursor()

        # Get all table names from source (excluding internal ones if any)
        source_cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name != 'solution'")
        tables = source_cursor.fetchall()

        for table_name, create_sql in tables:
            print(f"  Creating and migrating table: {table_name}")
            c.execute(create_sql)
            
            # Copy data
            source_cursor.execute(f"SELECT * FROM {table_name}")
            rows = source_cursor.fetchall()
            if rows:
                placeholders = ', '.join(['?' for _ in range(len(rows[0]))])
                c.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", rows)
        
        source_conn.close()
    else:
        print(f"Warning: Source database not found at {SOURCE_DB_PATH}. Mystery tables will be empty.")

    # Populate Investigations (SQL Murder Mystery Flow)
    # Round 1: Finding the murderer
    c.execute("INSERT INTO investigations (round, prompt, correct_answer) VALUES (1, 'Who committed the murder on Jan 15, 2018 in SQL City?', 'Jeremy Bowers')")
    
    # Round 2: Finding the mastermind
    c.execute("INSERT INTO investigations (round, prompt, correct_answer) VALUES (2, 'Who hired the murderer? (Check the killer''s interview for clues)', 'Miranda Priestly')")

    # Production User
    c.execute("INSERT INTO participants (name, password, round_start_time) VALUES (?, ?, ?)", 
              ('Query_clash', '8888', datetime.datetime.now()))
    
    conn.commit()
    conn.close()
    print("Database initialized successfully with SQL Murder Mystery data.")

if __name__ == '__main__':
    # Adjust path if running from within query_clash directory
    if not os.path.exists(SOURCE_DB_PATH) and os.path.exists(os.path.join('sql-mysteries-master', 'sql-murder-mystery.db')):
        SOURCE_DB_PATH = os.path.join('sql-mysteries-master', 'sql-murder-mystery.db')
    
    init_db()
