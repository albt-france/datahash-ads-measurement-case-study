"""Run sql/02..05 on the SIMULATED parquet tables with DuckDB and save the results to data/output/.

File 01 (Criteo, PUBLIC DATA) is run by src/extract_criteo.py on the raw file.
A file may hold several named queries separated by '-- @name'.
    python src/run_sql.py
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
PROC, OUT = ROOT / "data" / "processed", ROOT / "data" / "output"
TABLES = ["ads_daily", "signals_daily", "business_daily", "geo_daily", "ga4_daily", "use_cases", "calendar"]


def queries(path: Path):
    text = path.read_text(encoding="utf-8")
    if "-- @" not in text:
        return [(path.stem, text)]
    out = []
    for block in text.split("-- @")[1:]:
        name, q = block.split("\n", 1)
        out.append((f"{path.stem}__{name.strip()}", q))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for t in TABLES:
        con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{(PROC / f'{t}.parquet').as_posix()}')")
    for f in sorted((ROOT / "sql").glob("0[2-9]_*.sql")):
        for name, q in queries(f):
            df = con.execute(q.strip().rstrip(";")).df()
            df.to_csv(OUT / f"sql_{name}.csv", index=False)
            print(f"sql_{name}: {df.shape}")


if __name__ == "__main__":
    main()
