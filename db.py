"""Database helper for the Streamlit app. Put your MySQL password below (do not upload it to GitHub)."""
import warnings

warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")

import mysql.connector
import pandas as pd

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_MYSQL_PASSWORD",
    "database": "international_debt",
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def run_query(sql, params=None):
    """Run a SELECT and return a DataFrame. Parameters (%s) keep user input out of the SQL text."""
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()
