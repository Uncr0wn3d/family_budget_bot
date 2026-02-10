import psycopg2
import os
from datetime import datetime

# Берем ссылку на базу из настроек
DATABASE_URL = os.getenv("DATABASE_URL")

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
                    date TIMESTAMP
                )
            ''')
        conn.commit()

def add_expense(user_id, username, category, amount):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # В PostgreSQL используем %s
            cursor.execute(
                'INSERT INTO expenses (user_id, username, category, amount, date) VALUES (%s, %s, %s, %s, %s)',
                (user_id, username, category, amount, datetime.now())
            )
        conn.commit()

def get_detailed_report(start_date, end_date):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            query = '''
                SELECT username, category, SUM(amount) 
                FROM expenses 
                WHERE date >= %s AND date <= %s
                GROUP BY username, category
            '''
            cursor.execute(query, (start_date, end_date))
            return cursor.fetchall()

def get_total_by_category(start_date, end_date):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            query = '''
                SELECT category, SUM(amount) 
                FROM expenses 
                WHERE date >= %s AND date <= %s
                GROUP BY category
            '''
            cursor.execute(query, (start_date, end_date))
            return cursor.fetchall()
