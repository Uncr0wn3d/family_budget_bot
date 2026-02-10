import psycopg2
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    category TEXT,
                    amount REAL,
                    description TEXT,
                    date TIMESTAMP
                )
            ''')
        conn.commit()

def add_expense(user_id, username, category, amount, description):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO expenses (user_id, username, category, amount, description, date) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id',
                (user_id, username, category, amount, description, datetime.now())
            )
            return cursor.fetchone()[0]
        conn.commit()

def delete_expense(expense_id):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM expenses WHERE id = %s', (expense_id,))
        conn.commit()

def get_detailed_report(start_date, end_date):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            query = '''
                SELECT username, category, SUM(amount) FROM expenses 
                WHERE date >= %s AND date <= %s GROUP BY username, category
            '''
            cursor.execute(query, (start_date, end_date))
            return cursor.fetchall()

def get_total_by_category(start_date, end_date):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            query = 'SELECT category, SUM(amount) FROM expenses WHERE date >= %s AND date <= %s GROUP BY category'
            cursor.execute(query, (start_date, end_date))
            return cursor.fetchall()

def get_last_history(limit=10):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, username, category, amount, description FROM expenses ORDER BY id DESC LIMIT %s', (limit,))
            return cursor.fetchall()
