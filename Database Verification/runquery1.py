import sqlite3
from pathlib import Path

import pandas as pd


DB_PATH = Path(__file__).resolve().parent / "app.db"

query = """
SELECT
	r.Region_Name,
	COUNT(*) AS observation_count,
	ROUND(AVG(w.Mean_Temp_oC), 2) AS average_temperature,
	ROUND(AVG(w.RH_Percent), 2) AS average_humidity,
	ROUND(SUM(w.Rainfall_mm), 2) AS total_rainfall
FROM Weekly_Weather AS w
JOIN Region_Province_Master AS r ON r.Region_ID = w.Region_ID
GROUP BY r.Region_ID, r.Region_Name
ORDER BY total_rainfall DESC;
"""


if not DB_PATH.exists():
	raise FileNotFoundError(
		f"Database not found: {DB_PATH}. Run load_database.py first."
	)

with sqlite3.connect(DB_PATH) as connection:
	result = pd.read_sql_query(query, connection)

if result.empty:
	print("The query returned no rows.")
else:
	print(result.to_string(index=False))
