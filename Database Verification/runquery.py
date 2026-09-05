"""Query app.db and print results.

Examples:
   python runquery.py
   python runquery.py "SELECT * FROM station LIMIT 10"
   python runquery.py --tables
   python runquery.py --counts
   python runquery.py --foreign-keys
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "app.db"

DEFAULT_QUERY = """
SELECT r.Region_Name, w.SD_Week_Num, w.Mean_Temp_oC, w.Rainfall_mm, w.RH_Percent
FROM Weekly_Weather AS w
JOIN Region_Province_Master AS r ON r.Region_ID = w.Region_ID
ORDER BY r.Region_Name, w.SD_Week_Num
LIMIT 20;
"""


def open_database() -> sqlite3.Connection:
   if not DB_PATH.exists():
      raise FileNotFoundError(
         f"Database not found: {DB_PATH}\nRun 'python load_database.py' first."
      )
   connection = sqlite3.connect(DB_PATH)
   connection.execute("PRAGMA foreign_keys = ON")
   return connection


def print_query(connection: sqlite3.Connection, query: str) -> None:
   try:
      result = pd.read_sql_query(query, connection)
   except Exception as error:
      raise RuntimeError(f"Query failed: {error}\n\nSQL:\n{query}") from error
   if result.empty:
      print("Query ran successfully, but returned no rows.")
   else:
      print(result.to_string(index=False))
      print(f"\nRows returned: {len(result)}")


def print_tables(connection: sqlite3.Connection) -> None:
   print_query(connection, """
      SELECT name AS table_name
      FROM sqlite_master
      WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
      ORDER BY name;
   """)


def print_counts(connection: sqlite3.Connection) -> None:
   tables = [row[0] for row in connection.execute(
      "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
   )]
   rows = []
   for table in tables:
      quoted_table = '"' + table.replace('"', '""') + '"'
      count = connection.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0]
      rows.append((table, count))
   print(pd.DataFrame(rows, columns=["table_name", "row_count"]).to_string(index=False))


def print_foreign_keys(connection: sqlite3.Connection) -> None:
   violations = connection.execute("PRAGMA foreign_key_check").fetchall()
   if violations:
      print("Foreign-key violations:")
      for violation in violations:
         print(violation)
   else:
      print("No foreign-key violations found.")


def main() -> None:
   parser = argparse.ArgumentParser(description="Run SQL queries against app.db")
   parser.add_argument("query", nargs="?", help="SQL SELECT query to execute")
   parser.add_argument("--tables", action="store_true", help="List database tables")
   parser.add_argument("--counts", action="store_true", help="Show row counts for every table")
   parser.add_argument("--foreign-keys", action="store_true", help="Check foreign-key violations")
   args = parser.parse_args()
   try:
      connection = open_database()
      try:
         if args.tables:
            print_tables(connection)
         elif args.counts:
            print_counts(connection)
         elif args.foreign_keys:
            print_foreign_keys(connection)
         else:
            print_query(connection, args.query or DEFAULT_QUERY)
      finally:
         connection.close()
   except Exception as error:
      print(f"ERROR: {error}")
      raise SystemExit(1) from error


if __name__ == "__main__":
   main()
