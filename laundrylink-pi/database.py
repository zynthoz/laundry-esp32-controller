import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "laundrylink.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS machines (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            type        TEXT NOT NULL,
            esp32_ip    TEXT NOT NULL,
            pulse_on    INTEGER DEFAULT 50,
            pulse_off   INTEGER DEFAULT 50,
            pulse_count INTEGER DEFAULT 2,
            vend_price  INTEGER DEFAULT 60,
            status      TEXT DEFAULT 'IDLE'
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id          TEXT PRIMARY KEY,
            machine_id  TEXT NOT NULL,
            amount      INTEGER NOT NULL,
            status      TEXT NOT NULL,
            started_at  TEXT NOT NULL,
            ended_at    TEXT,
            synced      INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


def upsert_machine(machine_id, name, machine_type, esp32_ip, pulse_on, pulse_off, pulse_count, vend_price):
    conn = get_connection()
    conn.execute(
        """INSERT INTO machines (id, name, type, esp32_ip, pulse_on, pulse_off, pulse_count, vend_price)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
               name=excluded.name,
               type=excluded.type,
               esp32_ip=excluded.esp32_ip,
               pulse_on=excluded.pulse_on,
               pulse_off=excluded.pulse_off,
               pulse_count=excluded.pulse_count,
               vend_price=excluded.vend_price""",
        (machine_id, name, machine_type, esp32_ip, pulse_on, pulse_off, pulse_count, vend_price),
    )
    conn.commit()
    conn.close()


def get_all_machines():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM machines").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_machine(machine_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_machine_status(machine_id, status):
    conn = get_connection()
    conn.execute("UPDATE machines SET status = ? WHERE id = ?", (status, machine_id))
    conn.commit()
    conn.close()


def insert_transaction(txn_id, machine_id, amount, status, started_at):
    conn = get_connection()
    conn.execute(
        "INSERT INTO transactions (id, machine_id, amount, status, started_at) VALUES (?, ?, ?, ?, ?)",
        (txn_id, machine_id, amount, status, started_at),
    )
    conn.commit()
    conn.close()


def get_recent_transactions(limit=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transactions ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unsynced_transactions():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM transactions WHERE synced = 0").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_transactions_synced(txn_ids):
    if not txn_ids:
        return
    conn = get_connection()
    placeholders = ",".join("?" for _ in txn_ids)
    conn.execute(f"UPDATE transactions SET synced = 1 WHERE id IN ({placeholders})", txn_ids)
    conn.commit()
    conn.close()
