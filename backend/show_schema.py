"""Print the current database tables and row counts.

A small helper for demonstrating that migrations drop/recreate the schema cleanly:
    python show_schema.py
"""
import sqlite3

conn = sqlite3.connect("financeos.db")
tables = sorted(
    r[0]
    for r in conn.execute(
        "select name from sqlite_master where type='table' and name not like 'sqlite_%'"
    )
)

if not tables:
    print("(no tables)")
else:
    for t in tables:
        try:
            n = conn.execute(f"select count(*) from {t}").fetchone()[0]
            print(f"  {t:<18} {n} rows")
        except sqlite3.Error:
            print(f"  {t}")
conn.close()
