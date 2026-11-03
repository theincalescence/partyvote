import sqlite3
from flask import g, current_app

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DB_PATH'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    with app.app_context():
        conn = get_db()
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY, 
                name TEXT, 
                category TEXT, 
                image_path TEXT
            );
            CREATE TABLE IF NOT EXISTS votes (
                voter_uuid TEXT, 
                category TEXT, 
                entry_id INTEGER, 
                fingerprint TEXT DEFAULT 'unknown',
                PRIMARY KEY(voter_uuid, category)
            );
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY, 
                value TEXT
            );
            INSERT OR IGNORE INTO state (key, value) VALUES ('submissions_open', 'true');
            INSERT OR IGNORE INTO state (key, value) VALUES ('voting_open', 'false');
            INSERT OR IGNORE INTO state (key, value) VALUES ('reveal_individual', '0');
            INSERT OR IGNORE INTO state (key, value) VALUES ('reveal_couples', '0');
            INSERT OR IGNORE INTO state (key, value) VALUES ('reveal_pumpkins', '0');
        ''')
        
        # Verify schema column migration
        cols = [col[1] for col in conn.execute("PRAGMA table_info(votes)").fetchall()]
        if 'fingerprint' not in cols:
            try:
                conn.execute("ALTER TABLE votes ADD COLUMN fingerprint TEXT DEFAULT 'unknown'")
            except sqlite3.OperationalError:
                pass
                
        conn.commit()

def init_app(app):
    app.teardown_appcontext(close_db)
    init_db(app)