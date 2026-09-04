# Multi-Domain Agricultural Database

A normalized relational database that consolidates agricultural data from multiple, previously disconnected domains — crop production, livestock, soil, weather, and vaccination — into a single integrated schema, enabling cross-domain analysis that isolated datasets cannot support.

This repository contains the entity relationship design, the normalization process (1NF → BCNF), the SQLite implementation, and the extract-transform-load (ETL) pipeline used to populate it.

## Table of Contents

- [Problem Statement](#problem-statement)
- [Objectives](#objectives)
- [Repository Structure](#repository-structure)
- [Database Schema](#database-schema)
- [Getting Started](#getting-started)
- [ETL Workflow](#etl-workflow)
- [Verifying the Database](#verifying-the-database)
- [Data Sources](#data-sources)
- [Project Methodology](#project-methodology)
- [Current Status and Limitations](#current-status-and-limitations)
- [Future Work](#future-work)
- [Tools Used](#tools-used)
- [Team](#team)
- [Documentation](#documentation)

## Problem Statement

Existing agricultural datasets and platforms typically address only one domain at a time — a weather monitoring service here, a standalone soil database there — with no relational structure connecting them. This makes it difficult to answer questions that span domains, such as correlating soil fertility with livestock population, or examining how vaccination protocols relate to production outcomes.

## Objectives

1. Identify and collect authoritative agricultural data sources across multiple sub-domains (crop production, livestock, soil, weather, vaccination).
2. Design an integrated entity relationship diagram linking these sub-domains through shared entities such as region and farm.
3. Normalize the integrated schema through successive normal forms, from 1NF through Boyce-Codd Normal Form (BCNF), to eliminate redundancy and anomalies.
4. Implement the normalized schema as a working relational database, and populate and verify at least one sub-domain end-to-end as a proof of concept.

## Repository Structure

```
.
├── Data/
│   └── Potato_Crop_Weather_Calendar_BD.csv   # Source data for the Weekly Weather sub-domain
├── load_database.py                           # Creates the schema and loads data into app.db
├── runquery1.py                                # Query-based verification script
├── app.db                                      # Implemented SQLite database
├── bcnf_er_diagram.md                          # Auto-generated Mermaid ER diagram (from the live schema)
└── README.md
```

## Database Schema

The normalized schema consists of **19 tables** spanning eight functional areas:

| Area | Tables |
|---|---|
| Soil | `Soil_Acidity_Master`, `Soil_Acidity_Mapping`, `General_Soil_Master`, `Soil_Area_Distribution`, `Soil_Fertility_Status` |
| Land | `Land_Category_Master` |
| Region / Province | `Region_Province_Master` |
| Weather | `Weekly_Weather` |
| Livestock & Farm Management | `Livestock_Species`, `GP_Farm_Master`, `Livestock_Population` |
| Vaccination | `Vaccination_Protocol`, `Farm_Vaccination_Log` |
| Production | `Livestock_Product_Master`, `Meat_Egg_Production_Log`, `Livestock_Economy_Log`, `Farm_Statistics_By_Province` |
| Vendor | `Vendor_Master`, `Vendor_Farm_Transaction` |

All tables are connected through primary and foreign key relationships, with `Region_ID` and `Farm_ID` acting as the main shared keys linking domains together. The schema was normalized through 1NF, 2NF, 3NF, and BCNF to eliminate repeating groups, partial dependencies, and transitive dependencies.

The full entity relationship diagram (created with [Graphviz Online](https://dreampuf.github.io/GraphvizOnline/)) and the complete normalization walkthrough are documented in the project report.

## Getting Started

### Prerequisites

- Python 3.9+
- [pandas](https://pandas.pydata.org/)

```bash
pip install pandas
```

### Build the database

Run the loader script from the project root:

```bash
python load_database.py
```

This will:
1. Delete any existing `app.db` and create a fresh one.
2. Create all 19 tables according to the normalized schema, with foreign keys enforced (`PRAGMA foreign_keys = ON`).
3. Load the Weekly Weather sub-domain from `Data/Potato_Crop_Weather_Calendar_BD.csv`.
4. Generate `bcnf_er_diagram.md`, a Mermaid diagram reflecting the schema as actually implemented in the database.

On success, it prints a summary:

```json
{
  "database": "app.db",
  "tables": 19,
  "weekly_weather_rows": 150
}
```

## ETL Workflow

The extract-transform-load pipeline for the Weekly Weather sub-domain works as follows:

1. **Extract** — `load_database.py` reads `Potato_Crop_Weather_Calendar_BD.csv` into a pandas DataFrame and normalizes column names (lowercased, non-alphanumeric characters collapsed to underscores).
2. **Transform** — distinct region names are deduplicated and inserted into `Region_Province_Master`; each row's region name is resolved to its surrogate `Region_ID` via a lookup; sunshine hours, wind direction, and wind speed are consolidated into a single `SSH_Wind_Info` field.
3. **Load** — transformed records are inserted into `Weekly_Weather` using `INSERT OR IGNORE`, with the composite primary key `(Region_ID, SD_Week_Num)` preventing duplicates.

The same schema is already in place for the remaining sub-domains (soil, livestock, vaccination, production, vendor); extending the loader to populate them follows the same pattern.

## Verifying the Database

`runquery1.py` runs an aggregate query joining `Weekly_Weather` to `Region_Province_Master`, confirming referential integrity and summarizing observations by region:

```bash
python runquery1.py
```

Example output:

```
Region_Name  observation_count  average_temperature  average_humidity  total_rainfall
 Chattogram                 15                23.91             74.38           232.4
    Cumilla                 15                22.95             75.55           144.5
      Dhaka                 15                21.97             72.29           113.0
        ...
```

This confirms: (1) referential integrity between `Weekly_Weather` and `Region_Province_Master`, (2) completeness — all 10 regions have exactly 15 weekly observations each, and (3) plausibility of the aggregated values against known regional climate patterns.

## Data Sources

Data was collected from authorized government, institutional, and academic sources across each sub-domain, including the Bangladesh Bureau of Statistics, the Soil Resource Development Institute (SRDI), the Bangladesh Agro-Meteorological Information Service (BAMIS), and the Bangladesh National Veterinary Formulary, among others. PDF-sourced reports were converted to CSV using [iLovePDF](https://www.ilovepdf.com/) and manually verified against the originals. The full source-tracking record (sub-domain, source, URL, file location, and validity flag for all 107 collected files) is maintained separately — see [Documentation](#documentation).

## Project Methodology

This project was developed using **Scrum**, organized into two sprints:

- **Sprint 1** — data discovery, data acquisition, entity relationship diagram design.
- **Sprint 2** — database implementation, extract-transform workflow, query-based verification.

## Current Status and Limitations

- The full 19-table schema is implemented in SQLite with all constraints enforced.
- Only the **Weekly Weather** sub-domain has been populated and verified end-to-end, as a proof of concept for the pipeline.
- Data does not yet cover all regions comprehensively; availability varied across domains.
- No automated pipeline exists yet for continuously updating the database with new data.
- The database has not yet been tested against complex cross-domain queries at scale.

## Future Work

- **Pipeline automation** — extend the extract-transform workflow to support scheduled updates.
- **Cross-domain querying** — develop and test queries spanning multiple domains (e.g., soil fertility vs. livestock population).
- **Expanded data coverage** — extend collection to additional regions and time periods.
- **Analytics and prediction** — use the database as a foundation for production forecasting and resource optimization models.

## Tools Used

- **Python** & **pandas** — extract-transform-load workflow and verification queries
- **SQLite** — relational database engine
- **Graphviz Online** — entity relationship diagram design
- **Google Drive** — shared repository for data, code, and documentation
- **Trello** — Scrum board and sprint tracking
- **Excel** — data source tracking and organization
- **iLovePDF** — PDF-to-CSV/Excel conversion

## Team

| Name | Role |
|---|---|
| Mohammad Farhan Hasan | Team Manager |
| Rahnuma Tarannum | Contributor |
| Ritu Mallick | Contributor |
| Rafid Hasan | Contributor |

**Mentors:** Aung Cho, Arafat Sheikh

## Documentation

The full project report — covering the problem statement, objectives, sprint-by-sprint development, complete normalization walkthrough (1NF through BCNF), ETL workflow, deployment, and team retrospective — is included in this repository / linked here: `[add report link or filename]`.
