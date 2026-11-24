import sqlite3
import os

for path in ["../shoi.db", "shoi.db"]:
    if os.path.exists(path):
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if "role" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'patient'")
            conn.commit()
            print(f"Added role to {path}")
        else:
            print(f"Role already exists in {path}")
        conn.close()
