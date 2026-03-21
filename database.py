import sqlite3
from datetime import datetime

DB_NAME = 'scam_detector.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Table to store prediction logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            result TEXT NOT NULL,
            confidence REAL NOT NULL,
            timestamp TEXT NOT NULL,
            user_id INTEGER DEFAULT NULL
        )
    ''')

    # Table for admin login
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Insert default admin if not exists
    cursor.execute("SELECT * FROM admin WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO admin (username, password) VALUES (?, ?)",
            ('admin', 'admin123')
        )

    conn.commit()
    conn.close()
    print("Database initialized successfully!")


def save_prediction(message, result, confidence):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO predictions (message, result, confidence, timestamp) VALUES (?, ?, ?, ?)",
        (message, result, confidence, timestamp)
    )
    conn.commit()
    conn.close()


def get_all_predictions(limit=50):
    conn = sqlite3.connect('scam_detector.db')
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM predictions 
    ORDER BY id DESC
    LIMIT ?
""", (limit,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM predictions")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE result = 'SCAM'")
    scam_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE result = 'LEGITIMATE'")
    legit_count = cursor.fetchone()[0]

    conn.close()
    return {
        "total": total,
        "scam": scam_count,
        "legitimate": legit_count
    }


def verify_admin(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM admin WHERE username = ? AND password = ?",
        (username, password)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_daily_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DATE(timestamp) as date,
               COUNT(*) as total,
               SUM(CASE WHEN result = 'SCAM' THEN 1 ELSE 0 END) as scams,
               SUM(CASE WHEN result = 'LEGITIMATE' THEN 1 ELSE 0 END) as legit
        FROM predictions
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
        LIMIT 7
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows
def get_trend_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            DATE(timestamp) as date,
            SUM(CASE WHEN result = 'SCAM' THEN 1 ELSE 0 END) as scams,
            SUM(CASE WHEN result = 'LEGITIMATE' THEN 1 ELSE 0 END) as legit,
            COUNT(*) as total
        FROM predictions
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
        LIMIT 30
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows
def create_user(username, email, password_hash):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create users table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, timestamp)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def get_user_by_username(username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    )
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_email(email):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    )
    user = cursor.fetchone()
    conn.close()
    return user


def save_user_prediction(user_id, message, result, confidence):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO predictions (message, result, confidence, timestamp, user_id) VALUES (?, ?, ?, ?, ?)",
        (message, result, confidence, timestamp, user_id)
    )
    conn.commit()
    conn.close()


def get_user_predictions(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, message, result, confidence, timestamp 
        FROM predictions 
        WHERE user_id = ? 
        ORDER BY id DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows

def get_user_stats(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM predictions WHERE user_id = ?", (user_id,)
    )
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM predictions WHERE user_id = ? AND result = 'SCAM'",
        (user_id,)
    )
    scam_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM predictions WHERE user_id = ? AND result = 'LEGITIMATE'",
        (user_id,)
    )
    legit_count = cursor.fetchone()[0]

    conn.close()
    return {
        "total": total,
        "scam": scam_count,
        "legitimate": legit_count
    }
def update_schema():
    conn = get_db_connection()
    try:
        # Example: adding a confidence column if it doesn't exist
        conn.execute('ALTER TABLE predictions ADD COLUMN confidence REAL')
        conn.commit()
    except sqlite3.OperationalError:
        # This catches the "duplicate column" error and lets the app continue
        pass 
    conn.close()