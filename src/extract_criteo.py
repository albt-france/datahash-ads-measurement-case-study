"""Download the Criteo Uplift Prediction Dataset v2.1 once and keep only aggregates.

Source: https://huggingface.co/datasets/criteo/criteo-uplift (licence CC BY-NC-SA 4.0).
The 311 MB .csv.gz stays in data/raw/criteo/ (never pushed); DuckDB streams it and writes small aggregate tables to
data/processed/ (no raw row is ever published).

    python src/extract_criteo.py
"""
from pathlib import Path

import duckdb
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "criteo"
OUT = ROOT / "data" / "processed"
URL = "https://huggingface.co/datasets/criteo/criteo-uplift/resolve/main/criteo-research-uplift-v2.1.csv.gz"
FILE = RAW / "criteo-research-uplift-v2.1.csv.gz"


def download():
    if FILE.exists() and FILE.stat().st_size > 300e6:
        return
    RAW.mkdir(parents=True, exist_ok=True)
    with requests.get(URL, headers={"User-Agent": "measurement-case-study/1.0"}, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(FILE.with_suffix(".part"), "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    FILE.with_suffix(".part").rename(FILE)


def main():
    download()
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE VIEW criteo AS SELECT * FROM read_csv_auto('{FILE.as_posix()}')")
    sql = (ROOT / "sql" / "01_criteo_lift.sql").read_text(encoding="utf-8")
    # the SQL file defines named result blocks separated by '-- @name'
    for block in sql.split("-- @")[1:]:
        name, query = block.split("\n", 1)
        name = name.strip()
        con.execute(f"COPY ({query.strip().rstrip(';')}) TO '{(OUT / f'criteo_{name}.parquet').as_posix()}' (FORMAT PARQUET)")
        print("written criteo_" + name, con.execute(f"SELECT count(*) FROM '{(OUT / f'criteo_{name}.parquet').as_posix()}'").fetchone()[0], "rows")


if __name__ == "__main__":
    main()
