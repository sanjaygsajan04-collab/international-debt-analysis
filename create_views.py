"""Step 6a: create the views used by the 30 queries (runs views.sql)."""
from sql_utils import connect, read_statements


def main():
    conn = connect()
    cursor = conn.cursor()
    for _, sql in read_statements("views.sql"):
        cursor.execute(sql)
    conn.commit()
    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
    views = [row[0] for row in cursor.fetchall()]
    print("Views created:", ", ".join(views))
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
