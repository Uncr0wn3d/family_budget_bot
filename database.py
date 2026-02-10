import sqlite3
from datetime import datetime

def init_db():
    with sqlite3.connect('budget.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                category TEXT,
                amount REAL,
                date TEXT
            )
        ''')
        conn.commit()

def add_expense(user_id, username, category, amount):
    with sqlite3.connect('budget.db') as conn:
        cursor = conn.cursor()
        date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        cursor.execute('INSERT INTO expenses (user_id, username, category, amount, date) VALUES (?, ?, ?, ?, ?)',
                       (user_id, username, category, amount, date_str))
        conn.commit()

def get_total():
    with sqlite3.connect('budget.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT category, SUM(amount) FROM expenses GROUP BY category')
        return cursor.fetchall()

def get_history(limit=5):
    with sqlite3.connect('budget.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT username, category, amount, date FROM expenses ORDER BY id DESC LIMIT ?', (limit,))
        return cursor.fetchall()