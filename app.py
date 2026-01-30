from flask import Flask, render_template, request, session, jsonify, g, redirect, url_for
import sqlite3
import datetime
import re
import os
import logging
import sys

app = Flask(__name__)

# --- Production Configuration ---
# Use a strong secret key from environment variables in production
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_change_this_for_prod')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'database.db'))
print(f" * Using database: {DB_PATH}")
IS_PROD = os.environ.get('FLASK_ENV') == 'production'

# Admin Configuration
ADMIN_USER = os.environ.get('ADMIN_USER', 'QCA')
ADMIN_PASS = os.environ.get('ADMIN_PASS', '8888')

# Session Security
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=IS_PROD,  # Only send cookie over HTTPS in production
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600 # 1 hour
)

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- Database Helper ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        logger.debug(f"Connecting to database: {DB_PATH}")
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Helper Functions ---
def format_time(seconds):
    """Format seconds into HH:MM:SS string"""
    if seconds is None:
        return "00:00:00"
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h:02}:{m:02}:{s:02}"

def format_datetime(dt_str):
    """Format datetime string into HH:MM:SS for display"""
    if not dt_str:
        return "-"
    try:
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
            try:
                dt = datetime.datetime.strptime(dt_str.split('+')[0], fmt)
                return dt.strftime('%H:%M:%S')
            except ValueError:
                continue
        return dt_str
    except:
        return "-"

# --- Health Check ---
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.datetime.now().isoformat()}), 200

# --- Error Handlers ---
@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not Found'}), 404
    return render_template('index.html'), 404 # Redirect to home or show clean page

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Server Error: {error}")
    db = getattr(g, '_database', None)
    if db is not None:
        db.rollback()
    
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal Server Error'}), 500
    return "An unexpected error occurred. Please try again later.", 500

# --- Security Headers ---
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Content Security Policy (Basic)
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
    return response

# --- Routes ---
@app.route('/')
def index():
    if 'user' in session:
        return render_template('game.html', user=session['user'])
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    name = request.form.get('name')
    password = request.form.get('password')
    
    if not name or not password:
        return 'Credentials required', 400
    
    # Check for admin login
    if name == ADMIN_USER and password == ADMIN_PASS:
        session.permanent = False
        session['user'] = name
        session['is_admin'] = True
        logger.info(f"Admin logged in: {name}")
        return 'ADMIN', 200
        
    if name.lower() == password.lower():
        return 'Username and password cannot be the same', 400
    
    db = get_db()
    cursor = db.cursor()
    
    # Check if user exists
    user = cursor.execute('SELECT * FROM participants WHERE name = ?', (name,)).fetchone()
    
    if not user:
        # Auto-register new user
        try:
            db.execute('INSERT INTO participants (name, password, round_start_time) VALUES (?, ?, ?)', 
                       (name, password, datetime.datetime.now()))
            db.commit()
            logger.info(f"New user registered: {name}")
        except sqlite3.IntegrityError:
            # Race condition check just in case
            return 'User already exists', 400
    else:
        # Verify password for existing user
        if user['password'] != password:
            logger.warning(f"Failed login attempt for {name}")
            return 'Incorrect password', 401
    
    session.permanent = False
    session['user'] = name
    session['is_admin'] = False
    return 'OK', 200

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/game')
def game():
    if 'user' not in session:
        return render_template('index.html')
    return render_template('game.html', user=session['user'])

# Timer Sync
@app.route('/api/state')
def get_state():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db = get_db()
    name = session['user']
    user = db.execute('SELECT * FROM participants WHERE name = ?', (name,)).fetchone()
    
    if not user:
        session.pop('user', None)
        return jsonify({'error': 'User not found'}), 404

    # Calculate remaining time (Example: 60 minutes limit)
    ROUND_LIMIT_SECONDS = 3600 
    
    try:
        ts_str = user['round_start_time']
        # Try multiple formats for sqlite DATETIME
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
            try:
                start_time = datetime.datetime.strptime(ts_str.split('+')[0], fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Unknown date format: {ts_str}")
            
        elapsed_now = (datetime.datetime.now() - start_time).total_seconds()
    except Exception as e:
        logger.error(f"Timer calculation error for {name}: {e}")
        elapsed_now = user['elapsed_time'] or 0
    
    # Update elapsed time
    db.execute('UPDATE participants SET elapsed_time = ? WHERE name = ?', (int(elapsed_now), name))
    db.commit()

    return jsonify({
        'name': user['name'],
        'round': user['current_round'],
        'remaining_time': max(0, ROUND_LIMIT_SECONDS - elapsed_now)
    })

# Investigation
@app.route('/api/investigations')
def get_investigations():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db = get_db()
    name = session['user']
    user = db.execute('SELECT * FROM participants WHERE name = ?', (name,)).fetchone()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    current_round = user['current_round']
    
    investigations = db.execute('SELECT id, prompt, round FROM investigations WHERE round = ?', (current_round,)).fetchall()
    
    # Check solved status
    progress = db.execute('SELECT investigation_id, solved FROM investigation_progress WHERE name = ?', (name,)).fetchall()
    solved_map = {p['investigation_id']: p['solved'] for p in progress}
    
    result = []
    for inv in investigations:
        result.append({
            'id': inv['id'],
            'prompt': inv['prompt'],
            'solved': bool(solved_map.get(inv['id'], 0))
        })
    return jsonify(result)

@app.route('/api/verify', methods=['POST'])
def verify_answer():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    inv_id = data.get('id')
    answer = data.get('answer', '').strip()
    
    db = get_db()
    inv = db.execute('SELECT * FROM investigations WHERE id = ?', (inv_id,)).fetchone()
    
    if not inv:
        return jsonify({'error': 'Invalid ID'}), 400
        
    is_correct = inv['correct_answer'].lower() == answer.lower()
    
    if is_correct:
        # Try to insert with solved_at, fall back to without if column doesn't exist
        try:
            db.execute('INSERT OR IGNORE INTO investigation_progress (name, investigation_id, solved, solved_at) VALUES (?, ?, 1, ?)', 
                       (session['user'], inv_id, datetime.datetime.now()))
        except Exception:
            # Fallback for legacy database without solved_at column
            db.execute('INSERT OR IGNORE INTO investigation_progress (name, investigation_id, solved) VALUES (?, ?, 1)', 
                       (session['user'], inv_id))
        
        # Check round progress
        name = session['user']
        user = db.execute('SELECT * FROM participants WHERE name = ?', (name,)).fetchone()
        
        if not user:
            db.commit()
            return jsonify({'correct': True, 'error': 'User not found'}), 200
            
        current_round = user['current_round']
        
        total_in_round = db.execute('SELECT COUNT(*) FROM investigations WHERE round = ?', (current_round,)).fetchone()[0]
        solved_in_round = db.execute('''
            SELECT COUNT(*) FROM investigation_progress p 
            JOIN investigations i ON p.investigation_id = i.id 
            WHERE p.name = ? AND i.round = ? AND p.solved = 1
        ''', (name, current_round)).fetchone()[0]
        
        if solved_in_round >= total_in_round and current_round < 2:
            db.execute('UPDATE participants SET current_round = current_round + 1 WHERE name = ?', (name,))
            
        db.commit()
    
    return jsonify({'correct': is_correct})

@app.route('/submit', methods=['POST'])
def submit():
    if 'user' not in session:
        return 'Unauthorized', 401
        
    name = session['user']
    final_answer = request.form.get('final_answer', '').strip()
    
    db = get_db()
    
    # Check if already submitted
    existing = db.execute('SELECT * FROM submissions WHERE name = ?', (name,)).fetchone()
    if existing:
        return 'Already submitted', 400
        
    user = db.execute('SELECT * FROM participants WHERE name = ?', (name,)).fetchone()
    
    # Record submission
    # Verify correctness (Hardcoded mystery solution check for now as per init_db)
    # Mystery solution: "Marvin" (based on init_db investigation but also implicit final answer)
    # The prompt says: "Round 2 ... Determines mystery solution".
    # And "Correct final mystery solution". 
    # Let's check against a 'MASTER_SOLUTION' or just store it for manual review if unsure.
    # But strictly, the system should determine winner. 
    # Let's assume the correct answer is 'Marvin' as per my init_db for R2.
    
    is_correct = (final_answer.lower() == 'miranda priestly')
    
    submission_time = datetime.datetime.now()
    time_taken = user['elapsed_time'] # Approximate, simpler than recalculating exactly right now
    
    db.execute('''
        INSERT INTO submissions (name, round, final_answer, submission_time, time_taken)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, user['current_round'], final_answer, submission_time, time_taken))
    
    # Update solved status if correct? Or just use submissions table.
    if is_correct:
        db.execute('UPDATE participants SET solved = 1 WHERE name = ?', (name,))
        
    db.commit()
        
    return render_template('submit.html', success=is_correct, time_taken=format_time(time_taken))

# SQL Execution
@app.route('/api/query', methods=['POST'])
def execute_query():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    sql = request.json.get('sql', '').strip()
    
    # Security check: Read-only enforcement
    # Strengthened regex to catch more edge cases
    sql_clean = sql.strip().upper()
    
    if not sql_clean.startswith('SELECT'):
         return jsonify({'error': 'Only SELECT queries are allowed.', 'results': []})
         
    forbidden = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'PRAGMA', 'ATTACH', 'TRANSACTION', 'REPLACE', 'CREATE']
    for word in forbidden:
        if re.search(r'\b' + word + r'\b', sql_clean):
            logger.warning(f"Forbidden command '{word}' attempted by user: {session.get('user')}")
            return jsonify({'error': f'Command {word} is forbidden.', 'results': []})

    try:
        db = get_db()
        # Increment query count
        db.execute('UPDATE participants SET query_count = query_count + 1 WHERE name = ?', (session['user'],))
        db.commit()

        # Set a timeout for long-running queries if possible (sqlite3 connection timeout is for locks)
        cursor = db.execute(sql)
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        results = [dict(zip(columns, row)) for row in rows]
        return jsonify({'results': results[:50], 'columns': columns}) # Limit results
    except Exception as e:
        return jsonify({'error': str(e), 'results': []})


@app.route('/api/schema', methods=['GET'])
def get_schema():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db()
    c = conn.cursor()
    
    # Get all tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in c.fetchall()]
    print(f"DEBUG: Found tables in {DB_PATH}: {tables}")
    
    schema = {}
    hidden_tables = ['participants', 'investigations', 'investigation_progress', 'submissions']
    
    for table in tables:
        if table in hidden_tables:
            continue
            
        c.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in c.fetchall()]
        schema[table] = columns
        
    return jsonify(schema)

# --- Admin Routes ---
def admin_required(f):
    """Decorator to require admin access"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session.get('is_admin'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Admin access required'}), 403
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    
    # Get all participants
    participants = db.execute('''
        SELECT name, current_round, elapsed_time, solved, query_count, round_start_time
        FROM participants 
        ORDER BY solved DESC, current_round DESC, elapsed_time ASC
    ''').fetchall()
    
    # Get investigations
    investigations = db.execute('SELECT * FROM investigations ORDER BY round, id').fetchall()
    
    # Get submissions
    submissions = db.execute('''
        SELECT s.*, p.solved as is_correct
        FROM submissions s
        JOIN participants p ON s.name = p.name
        ORDER BY s.submission_time DESC
    ''').fetchall()
    
    # Get round solve times for all participants (graceful fallback if column doesn't exist)
    solve_times = {}
    try:
        round_times = db.execute('''
            SELECT ip.name, i.round, ip.solved_at
            FROM investigation_progress ip
            JOIN investigations i ON ip.investigation_id = i.id
            WHERE ip.solved = 1
        ''').fetchall()
        
        # Build a map of participant -> round -> solve time
        for rt in round_times:
            if rt['name'] not in solve_times:
                solve_times[rt['name']] = {}
            solve_times[rt['name']][rt['round']] = rt['solved_at']
    except Exception as e:
        # Column doesn't exist in legacy database - just use empty solve times
        logger.warning(f"Could not fetch solve times (run init_db.py to add solved_at column): {e}")
    
    stats = []
    for p in participants:
        name = p['name']
        participant_solves = solve_times.get(name, {})
        stats.append({
            'name': name,
            'round': p['current_round'],
            'time': format_time(p['elapsed_time']),
            'solved': p['solved'],
            'queries': p['query_count'],
            'round1_time': format_datetime(participant_solves.get(1)),
            'round2_time': format_datetime(participant_solves.get(2)),
            'start_time': p['round_start_time']
        })
    
    inv_list = []
    for inv in investigations:
        inv_list.append({
            'id': inv['id'],
            'round': inv['round'],
            'prompt': inv['prompt'],
            'answer': inv['correct_answer']
        })
    
    sub_list = []
    for sub in submissions:
        sub_list.append({
            'name': sub['name'],
            'round': sub['round'],
            'answer': sub['final_answer'],
            'time': sub['submission_time'],
            'correct': sub['is_correct']
        })
        
    return render_template('admin.html', 
                           stats=stats, 
                           investigations=inv_list,
                           submissions=sub_list,
                           admin_user=session['user'])

@app.route('/api/admin/stats')
@admin_required
def admin_stats_api():
    """API endpoint for live admin dashboard updates"""
    db = get_db()
    
    # Get all participants
    participants = db.execute('''
        SELECT name, current_round, elapsed_time, solved, query_count, round_start_time
        FROM participants 
        ORDER BY solved DESC, current_round DESC, elapsed_time ASC
    ''').fetchall()
    
    # Get submissions
    submissions = db.execute('''
        SELECT s.*, p.solved as is_correct
        FROM submissions s
        JOIN participants p ON s.name = p.name
        ORDER BY s.submission_time DESC
    ''').fetchall()
    
    # Get round solve times for all participants (graceful fallback if column doesn't exist)
    solve_times = {}
    try:
        round_times = db.execute('''
            SELECT ip.name, i.round, ip.solved_at
            FROM investigation_progress ip
            JOIN investigations i ON ip.investigation_id = i.id
            WHERE ip.solved = 1
        ''').fetchall()
        
        # Build a map of participant -> round -> solve time
        for rt in round_times:
            if rt['name'] not in solve_times:
                solve_times[rt['name']] = {}
            solve_times[rt['name']][rt['round']] = rt['solved_at']
    except Exception as e:
        # Column doesn't exist in legacy database
        logger.warning(f"Could not fetch solve times: {e}")
    
    stats = []
    for p in participants:
        name = p['name']
        participant_solves = solve_times.get(name, {})
        stats.append({
            'name': name,
            'round': p['current_round'],
            'time': format_time(p['elapsed_time']),
            'solved': bool(p['solved']),
            'queries': p['query_count'],
            'round1_time': format_datetime(participant_solves.get(1)),
            'round2_time': format_datetime(participant_solves.get(2))
        })
    
    sub_list = []
    for sub in submissions:
        sub_list.append({
            'name': sub['name'],
            'answer': sub['final_answer'],
            'correct': bool(sub['is_correct'])
        })
    
    return jsonify({
        'stats': stats,
        'submissions': sub_list
    })

@app.route('/admin/reset-user/<name>', methods=['POST'])
@admin_required
def reset_user(name):
    db = get_db()
    
    # Reset user's progress
    db.execute('''
        UPDATE participants 
        SET current_round = 1, elapsed_time = 0, solved = 0, query_count = 0,
            round_start_time = ?
        WHERE name = ?
    ''', (datetime.datetime.now(), name))
    
    # Clear their investigation progress
    db.execute('DELETE FROM investigation_progress WHERE name = ?', (name,))
    
    # Clear their submission
    db.execute('DELETE FROM submissions WHERE name = ?', (name,))
    
    db.commit()
    logger.info(f"Admin reset user: {name}")
    
    return jsonify({'success': True, 'message': f'User {name} has been reset'})

@app.route('/admin/delete-user/<name>', methods=['POST'])
@admin_required
def delete_user(name):
    db = get_db()
    
    db.execute('DELETE FROM investigation_progress WHERE name = ?', (name,))
    db.execute('DELETE FROM submissions WHERE name = ?', (name,))
    db.execute('DELETE FROM participants WHERE name = ?', (name,))
    
    db.commit()
    logger.info(f"Admin deleted user: {name}")
    
    return jsonify({'success': True, 'message': f'User {name} has been deleted'})

@app.route('/analytics')
def analytics():
    db = get_db()
    participants = db.execute('''
        SELECT name, current_round, elapsed_time, solved, query_count 
        FROM participants 
        ORDER BY query_count DESC, elapsed_time ASC
    ''').fetchall()
    
    stats = []
    for p in participants:
        stats.append({
            'name': p['name'],
            'round': p['current_round'],
            'time': format_time(p['elapsed_time']),
            'solved': "YES" if p['solved'] else "NO",
            'queries': p['query_count']
        })
        
    return render_template('analytics.html', stats=stats)

if __name__ == '__main__':
    app.run(debug=True)
