"""Create app.db from the entities and relationships in the ER diagram."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "Data"
DB_PATH = ROOT / "app.db"

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE Soil_Acidity_Master (Acidity_Class_ID INTEGER PRIMARY KEY, Acidity_Class TEXT NOT NULL UNIQUE, pH_Range TEXT);
CREATE TABLE Land_Category_Master (Land_Category_ID INTEGER PRIMARY KEY, Category_Name TEXT NOT NULL UNIQUE);
CREATE TABLE Livestock_Species (Species_ID INTEGER PRIMARY KEY, Species_Name TEXT NOT NULL UNIQUE);
CREATE TABLE Livestock_Product_Master (Product_ID INTEGER PRIMARY KEY, Product_Name TEXT NOT NULL UNIQUE, Unit TEXT NOT NULL);
CREATE TABLE Region_Province_Master (Region_ID INTEGER PRIMARY KEY, Region_Name TEXT NOT NULL UNIQUE);
CREATE TABLE Vaccination_Protocol (Vaccine_ID INTEGER PRIMARY KEY, Disease_Antigen TEXT NOT NULL, Vaccine_Type TEXT NOT NULL, Route TEXT NOT NULL);
CREATE TABLE Vendor_Master (Vendor_ID INTEGER PRIMARY KEY, Vendor_Name TEXT NOT NULL, Focal_Point TEXT, Contact TEXT);
CREATE TABLE GP_Farm_Master (
    Farm_ID INTEGER PRIMARY KEY, Farm_Name TEXT NOT NULL, Species_ID INTEGER NOT NULL,
    Type_of_Breed TEXT, Imported_From TEXT, Province_ID INTEGER NOT NULL,
    FOREIGN KEY (Species_ID) REFERENCES Livestock_Species(Species_ID),
    FOREIGN KEY (Province_ID) REFERENCES Region_Province_Master(Region_ID)
);
CREATE TABLE General_Soil_Master (
    Soil_Type_ID INTEGER PRIMARY KEY, General_Soil TEXT NOT NULL, Category_ID INTEGER, Taxonomy_ID INTEGER,
    FOREIGN KEY (Category_ID) REFERENCES Land_Category_Master(Land_Category_ID)
);
CREATE TABLE Soil_Acidity_Mapping (
    Soil_Type_ID INTEGER NOT NULL, Season_Dependency TEXT NOT NULL, Topsoil_or_Subsoil TEXT NOT NULL,
    Acidity_Class_ID INTEGER NOT NULL, PRIMARY KEY (Soil_Type_ID, Season_Dependency, Topsoil_or_Subsoil),
    FOREIGN KEY (Soil_Type_ID) REFERENCES General_Soil_Master(Soil_Type_ID),
    FOREIGN KEY (Acidity_Class_ID) REFERENCES Soil_Acidity_Master(Acidity_Class_ID)
);
CREATE TABLE Soil_Area_Distribution (
    Soil_Type_ID INTEGER NOT NULL, Region_ID INTEGER NOT NULL, Area_ha REAL NOT NULL,
    PRIMARY KEY (Soil_Type_ID, Region_ID),
    FOREIGN KEY (Soil_Type_ID) REFERENCES General_Soil_Master(Soil_Type_ID),
    FOREIGN KEY (Region_ID) REFERENCES Region_Province_Master(Region_ID)
);
CREATE TABLE Weekly_Weather (
    Region_ID INTEGER NOT NULL, SD_Week_Num INTEGER NOT NULL, Month TEXT,
    Mean_Temp_oC REAL, Max_Temp_oC REAL, Min_Temp_oC REAL, Rainfall_mm REAL,
    RH_Percent REAL, SSH_Wind_Info TEXT, PRIMARY KEY (Region_ID, SD_Week_Num),
    FOREIGN KEY (Region_ID) REFERENCES Region_Province_Master(Region_ID)
);
CREATE TABLE Soil_Fertility_Status (
    Land_Category_ID INTEGER NOT NULL, Assessment_Year INTEGER NOT NULL, pH_Value REAL,
    pH_Class TEXT, Organic_Matter REAL, PRIMARY KEY (Land_Category_ID, Assessment_Year),
    FOREIGN KEY (Land_Category_ID) REFERENCES Land_Category_Master(Land_Category_ID)
);
CREATE TABLE Farm_Statistics_By_Province (
    Province_ID INTEGER NOT NULL, Year INTEGER NOT NULL, Num_Broiler_Farms INTEGER,
    Num_Layer_Farms INTEGER, Num_Duck_Farms INTEGER, PRIMARY KEY (Province_ID, Year),
    FOREIGN KEY (Province_ID) REFERENCES Region_Province_Master(Region_ID)
);
CREATE TABLE Farm_Vaccination_Log (
    Farm_ID INTEGER NOT NULL, Vaccine_ID INTEGER NOT NULL, Days_Age INTEGER NOT NULL, Comments TEXT,
    PRIMARY KEY (Farm_ID, Vaccine_ID, Days_Age),
    FOREIGN KEY (Farm_ID) REFERENCES GP_Farm_Master(Farm_ID),
    FOREIGN KEY (Vaccine_ID) REFERENCES Vaccination_Protocol(Vaccine_ID)
);
CREATE TABLE Vendor_Farm_Transaction (
    Vendor_ID INTEGER NOT NULL, Farm_ID INTEGER NOT NULL, Transaction_Date TEXT NOT NULL,
    Product_Equip_Bought TEXT NOT NULL, PRIMARY KEY (Vendor_ID, Farm_ID, Transaction_Date),
    FOREIGN KEY (Vendor_ID) REFERENCES Vendor_Master(Vendor_ID),
    FOREIGN KEY (Farm_ID) REFERENCES GP_Farm_Master(Farm_ID)
);
CREATE TABLE Livestock_Economy_Log (
    Fiscal_Year INTEGER PRIMARY KEY, GDP_Volume_Cr_Taka REAL, GDP_Growth_Rate_Pct REAL,
    Agri_GDP_Share_Pct REAL, Employment_Direct REAL
);
CREATE TABLE Livestock_Population (
    Species_ID INTEGER NOT NULL, Fiscal_Year INTEGER NOT NULL, Region_ID INTEGER NOT NULL,
    Population_Lakh REAL, PRIMARY KEY (Species_ID, Fiscal_Year),
    FOREIGN KEY (Species_ID) REFERENCES Livestock_Species(Species_ID),
    FOREIGN KEY (Fiscal_Year) REFERENCES Livestock_Economy_Log(Fiscal_Year),
    FOREIGN KEY (Region_ID) REFERENCES Region_Province_Master(Region_ID)
);
CREATE TABLE Meat_Egg_Production_Log (
    Product_ID INTEGER NOT NULL, Fiscal_Year INTEGER NOT NULL, Production_Amount REAL,
    Demand REAL, Availability REAL, PRIMARY KEY (Product_ID, Fiscal_Year),
    FOREIGN KEY (Product_ID) REFERENCES Livestock_Product_Master(Product_ID),
    FOREIGN KEY (Fiscal_Year) REFERENCES Livestock_Economy_Log(Fiscal_Year)
);
"""


def normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def load_weekly_weather(connection: sqlite3.Connection) -> None:
    path = DATA_DIR / "Potato_Crop_Weather_Calendar_BD.csv"
    if not path.exists():
        return
    frame = pd.read_csv(path)
    frame.columns = [normalize(column) for column in frame.columns]
    for region_name in frame["region"].dropna().unique():
        connection.execute("INSERT OR IGNORE INTO Region_Province_Master (Region_Name) VALUES (?)", (str(region_name),))
    for row in frame.itertuples(index=False):
        region_id = connection.execute(
            "SELECT Region_ID FROM Region_Province_Master WHERE Region_Name = ?", (row.region,)
        ).fetchone()[0]
        connection.execute(
            """INSERT OR IGNORE INTO Weekly_Weather
            (Region_ID, SD_Week_Num, Month, Mean_Temp_oC, Max_Temp_oC, Min_Temp_oC,
             Rainfall_mm, RH_Percent, SSH_Wind_Info) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (region_id, int(row.order), None, row.mean_temp_c, row.max_temp_c, row.min_temp_c,
            row.rainfall_mm, row.rhmean, f"SSH={row.sshr_hrs}; WD={row.wd_deg}; WS={row.ws_km_hr}"),
        )


def write_mermaid(connection: sqlite3.Connection) -> None:
    lines = ["# ER Diagram Database", "", "```mermaid", "erDiagram"]
    tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for table in tables:
        lines.append(f"    {table} {{")
        foreign_columns = {row[3] for row in connection.execute(f'PRAGMA foreign_key_list("{table}")')}
        for _, name, data_type, _, _, primary_key in connection.execute(f'PRAGMA table_info("{table}")'):
            tags = " PK" if primary_key else ""
            if name in foreign_columns:
                tags += " FK"
            lines.append(f"        {data_type.lower()} {name}{tags}")
        lines.append("    }")
    for table in tables:
        for foreign_key in connection.execute(f'PRAGMA foreign_key_list("{table}")'):
            lines.append(f'    {foreign_key[2]} ||--o{{ {table} : "references"')
    lines.extend(["```", ""])
    (ROOT / "bcnf_er_diagram.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.executescript(SCHEMA)
        load_weekly_weather(connection)
        connection.commit()
        write_mermaid(connection)
        table_count = connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        weather_count = connection.execute("SELECT COUNT(*) FROM Weekly_Weather").fetchone()[0]
        print(json.dumps({"database": str(DB_PATH), "tables": table_count, "weekly_weather_rows": weather_count}, indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()