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
        # Сохраняем дату в формате YYYY-MM-DD для легкой фильтрации
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO expenses (user_id, username, category, amount, date) VALUES (?, ?, ?, ?, ?)',
                       (user_id, username, category, amount, date_str))
        conn.commit()

def get_detailed_report(start_date, end_date):
    """Возвращает траты, сгруппированные по пользователю и категории за период"""
    with sqlite3.connect('budget.db') as conn:
        cursor = conn.cursor()
        query = '''
            SELECT username, category, SUM(amount) 
            FROM expenses 
            WHERE date >= ? AND date <= ?
            GROUP BY username, category
        '''
        cursor.execute(query, (start_date, end_date))
        return cursor.fetchall()

def get_total_by_category(start_date, end_date):
    """Возвращает общие суммы по категориям за период"""
    with sqlite3.connect('budget.db') as conn:
        cursor = conn.cursor()
        query = '''
            SELECT category, SUM(amount) 
            FROM expenses 
            WHERE date >= ? AND date <= ?
            GROUP BY category
        '''
        cursor.execute(query, (start_date, end_date))
        return cursor.fetchall()
