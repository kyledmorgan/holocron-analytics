import sqlite3
from pathlib import Path

DB = Path('local/state/ingest_state.db')
if not DB.exists():
    print('State DB missing:', DB)
    raise SystemExit(1)

conn = sqlite3.connect(DB)
cur = conn.cursor()
# Get last 50 completed mediawiki work items
cur.execute("SELECT work_item_id FROM work_items WHERE status='completed' AND source_name='wookieepedia' ORDER BY updated_at DESC LIMIT 50")
rows = cur.fetchall()
ids = [r[0] for r in rows]
print('Found', len(ids), 'completed wookieepedia items to reset')
if ids:
    placeholders = ','.join('?' for _ in ids)
    cur.execute(f"UPDATE work_items SET status='pending', attempt=0, updated_at=datetime('now') WHERE work_item_id IN ({placeholders})", ids)
    conn.commit()
    print('Reset', cur.rowcount, 'items to pending')
else:
    print('No items to reset')
conn.close()
