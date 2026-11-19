"""Step 6b: run all 30 queries from queries.sql, print a preview and save each result as a CSV."""
import os

import pandas as pd

from sql_utils import connect, read_statements

pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 60)


def main():
    os.makedirs("query_results", exist_ok=True)
    conn = connect()
    cursor = conn.cursor()
    ran = 0
    for query_id, sql in read_statements("queries.sql"):
        cursor.execute(sql)
        if cursor.description is None:          # CREATE / DROP statements return no rows
            continue
        columns = [col[0] for col in cursor.description]
        result = pd.DataFrame(cursor.fetchall(), columns=columns)
        result.to_csv(f"query_results/{query_id}.csv", index=False)
        ran += 1
        print(f"\n=== {query_id}: {len(result):,} rows ===")
        print(result.head(5).to_string(index=False))
    conn.commit()
    print(f"\nDone: {ran} queries run, results saved in the query_results folder.")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
