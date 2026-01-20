import unittest
import json
from app import app, get_db

class QueryClashTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Reset DB for test
        db = get_db()
        db.execute('DELETE FROM participants WHERE name = "TestAgent"')
        db.execute('DELETE FROM investigation_progress WHERE name = "TestAgent"')
        db.execute('DELETE FROM submissions WHERE name = "TestAgent"')
        # Create test user
        db.execute('INSERT INTO participants (name, password, round_start_time) VALUES (?, ?, ?)',
                   ('TestAgent', 'testpass', '2026-01-20 00:00:00'))
        db.commit()

    def tearDown(self):
        self.app_context.pop()

    def login(self):
        return self.app.post('/login', data={'name': 'TestAgent', 'password': 'testpass'}, follow_redirects=True)

    def test_login_and_persistence(self):
        rv = self.login()
        self.assertEqual(rv.status_code, 200)
        
        # Check if session persists (access game)
        rv = self.app.get('/game')
        self.assertIn(b'QUERY_CLASH', rv.data)
        self.assertIn(b'TestAgent', rv.data)

    def test_sql_security(self):
        self.login()
        
        # 1. Allowed Query
        rv = self.app.post('/api/query', json={'sql': 'SELECT * FROM person LIMIT 4'})
        data = json.loads(rv.data)
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 4)
        
        # 2. Blocked Query (DROP - caught by start check)
        rv = self.app.post('/api/query', json={'sql': 'DROP TABLE suspects'})
        data = json.loads(rv.data)
        self.assertIn('error', data)
        # It might be caught by "Only SELECT" or "Forbidden"
        self.assertTrue('only select' in data['error'].lower() or 'forbidden' in data['error'].lower())

        # 2b. Blocked Query (Injection attempt)
        rv = self.app.post('/api/query', json={'sql': 'SELECT * FROM suspects; DROP TABLE suspects'})
        data = json.loads(rv.data)
        self.assertIn('error', data)
        self.assertIn('forbidden', data['error'].lower())

        # 3. Blocked Query (INSERT)
        rv = self.app.post('/api/query', json={'sql': 'INSERT INTO suspects VALUES (1, "Hack", "Hack", "Hack")'})
        data = json.loads(rv.data)
        self.assertIn('error', data)
        
    def test_round_progression(self):
        self.login()
        
        # Verify Initial State
        rv = self.app.get('/api/state')
        data = json.loads(rv.data)
        self.assertEqual(data['round'], 1)
        
        # Solve Round 1
        rv = self.app.get('/api/investigations')
        invs = json.loads(rv.data)
        self.assertEqual(len(invs), 1) # Now 1 investigation in R1
        
        # Find ID for "Who committed the murder..."
        q1 = next(i for i in invs if "committed the murder" in i['prompt'])
        
        # Answer Q1
        self.app.post('/api/verify', json={'id': q1['id'], 'answer': 'Jeremy Bowers'})
        
        # Check State (Should be R2 now since R1 only has 1 investigation)
        rv = self.app.get('/api/state')
        self.assertEqual(json.loads(rv.data)['round'], 2)
        
    def test_final_submission(self):
        self.login()
        # Fast forward to submission
        
        # Let's just submit 'Miranda Priestly'.
        rv = self.app.post('/submit', data={'final_answer': 'Miranda Priestly'})
        self.assertIn(b'COMPLETED', rv.data) # Check for success message
        
        # Check DB
        db = get_db()
        sub = db.execute('SELECT * FROM submissions WHERE name = "TestAgent"').fetchone()
        self.assertIsNotNone(sub)
        self.assertEqual(sub['final_answer'], 'Miranda Priestly')

if __name__ == '__main__':
    with open('test_output.txt', 'w') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner, exit=False)
