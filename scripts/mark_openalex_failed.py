import sqlite3
from pathlib import Path
db=Path('local/state/ingest_state.db')
if not db.exists():
    print('State DB not found:', db)
    raise SystemExit(1)
conn=sqlite3.connect(db)
cur=conn.cursor()
cur.execute("SELECT status, source_system, COUNT(*) FROM work_items GROUP BY status, source_system ORDER BY status, source_system")
rows=cur.fetchall()
print('Counts by status, source_system:')
for r in rows:
    print(r)
# update pending openalex -> failed
cur.execute("UPDATE work_items SET status='failed' WHERE status='pending' AND source_system='openalex'")
updated=cur.rowcount
conn.commit()
print('Marked pending openalex as failed:', updated)
cur.execute("SELECT status, source_system, COUNT(*) FROM work_items GROUP BY status, source_system ORDER BY status, source_system")
for r in cur.fetchall():
    print(r)
conn.close()
