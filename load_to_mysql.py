"""Step 5: create the MySQL database and load the three cleaned CSV files."""
import getpass

import mysql.connector
import pandas as pd

BATCH_SIZE = 20000


def run_schema(cursor):
    """Run every statement in schema.sql (it has no triggers, so splitting on ; is safe)."""
    with open("schema.sql", encoding="utf-8") as f:
        script = f.read()
    # drop comment lines first so a ';' inside a comment cannot split a statement
    lines = [ln for ln in script.splitlines() if not ln.strip().startswith("--")]
    for statement in "\n".join(lines).split(";"):
        if statement.strip():
            cursor.execute(statement)


def insert_in_batches(conn, cursor, sql, rows, label):
    """Insert rows in batches so a big table does not need one giant statement."""
    total = len(rows)
    for start in range(0, total, BATCH_SIZE):
        cursor.executemany(sql, rows[start:start + BATCH_SIZE])
        conn.commit()
        done = min(start + BATCH_SIZE, total)
        print(f"   {label}: {done:,} / {total:,}", end="\r")
    print(f"   {label}: {total:,} rows loaded            ")


def main():
    password = getpass.getpass("MySQL password: ")
    conn = mysql.connector.connect(host="localhost", user="root", password=password)
    cursor = conn.cursor()

    print("Creating database and tables from schema.sql ...")
    run_schema(cursor)
    conn.database = "international_debt"

    countries = pd.read_csv("countries_clean.csv")
    indicators = pd.read_csv("indicators_clean.csv")
    debt = pd.read_csv("debt_data_clean.csv")

    print("Loading data (parents first, so the foreign keys are satisfied) ...")
    insert_in_batches(
        conn, cursor,
        "INSERT INTO countries (country_code, country_name, region, income_group, is_aggregate) "
        "VALUES (%s, %s, %s, %s, %s)",
        [(r.country_code, r.country_name, r.region, r.income_group, int(r.is_aggregate))
         for r in countries.itertuples()],
        "countries",
    )
    insert_in_batches(
        conn, cursor,
        "INSERT INTO indicators (indicator_code, indicator_name, topic, unit) VALUES (%s, %s, %s, %s)",
        [tuple(r) for r in indicators.itertuples(index=False)],
        "indicators",
    )
    insert_in_batches(
        conn, cursor,
        "INSERT INTO debt_data (country_code, indicator_code, year, value) VALUES (%s, %s, %s, %s)",
        [(r.country_code, r.indicator_code, int(r.year), float(r.value))
         for r in debt.itertuples()],
        "debt_data",
    )

    print("\nChecks (database vs CSV):")
    for table, expected in [("countries", len(countries)), ("indicators", len(indicators)), ("debt_data", len(debt))]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        found = cursor.fetchone()[0]
        print(f"   {table:<11} rows: {found:>9,}  (CSV {expected:,})  {'OK' if found == expected else 'MISMATCH'}")
    cursor.execute("SELECT SUM(value) FROM debt_data WHERE indicator_code = 'DT.DOD.DECT.CD' AND year = 2024")
    print("   Sum of total external debt in 2024 (all rows, incl. groups):", f"{float(cursor.fetchone()[0]):,.0f}")
    expected = debt[(debt.indicator_code == "DT.DOD.DECT.CD") & (debt.year == 2024)].value.sum()
    print("   Same sum from the CSV:                                    ", f"{expected:,.0f}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
