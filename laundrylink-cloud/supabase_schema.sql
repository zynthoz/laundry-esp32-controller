-- LaundryLink Cloud — Supabase Schema
-- Run this in the Supabase SQL Editor to set up all tables and functions.

-- ============================================================
-- TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS owners (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS api_keys (
    key         TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL REFERENCES owners(id),
    created_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL REFERENCES owners(id),
    name        TEXT NOT NULL,
    pi_url      TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id          TEXT PRIMARY KEY,
    location_id TEXT NOT NULL REFERENCES locations(id),
    machine_id  TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    status      TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    ended_at    TEXT,
    synced_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS machines (
    id          TEXT NOT NULL,
    location_id TEXT NOT NULL REFERENCES locations(id),
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,
    vend_price  INTEGER DEFAULT 60,
    status      TEXT DEFAULT 'IDLE',
    pulse_on    INTEGER DEFAULT 50,
    pulse_off   INTEGER DEFAULT 50,
    pulse_count INTEGER DEFAULT 2,
    updated_at  TIMESTAMPTZ,
    PRIMARY KEY (id, location_id)
);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
-- Enable RLS on all tables. The backend uses the service_role key,
-- which bypasses RLS automatically. These policies lock out the
-- anon key and any direct client access.

ALTER TABLE owners ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE machines ENABLE ROW LEVEL SECURITY;

-- No permissive policies for anon = anon gets zero access.
-- Service role key bypasses RLS entirely, so the Flask backend works as-is.

-- ============================================================
-- RPC FUNCTIONS
-- ============================================================

-- Get recent transactions for an owner (with location name)
CREATE OR REPLACE FUNCTION get_transactions_for_owner(p_owner_id TEXT, p_limit INTEGER DEFAULT 100)
RETURNS TABLE (
    id TEXT,
    location_id TEXT,
    machine_id TEXT,
    amount INTEGER,
    status TEXT,
    started_at TEXT,
    ended_at TEXT,
    synced_at TEXT,
    location_name TEXT
) LANGUAGE sql STABLE AS $$
    SELECT t.id, t.location_id, t.machine_id, t.amount, t.status,
           t.started_at, t.ended_at, t.synced_at, l.name AS location_name
    FROM transactions t
    JOIN locations l ON t.location_id = l.id
    WHERE l.owner_id = p_owner_id
    ORDER BY t.started_at DESC
    LIMIT p_limit;
$$;

-- Get all machines for an owner (with location name)
CREATE OR REPLACE FUNCTION get_machines_for_owner(p_owner_id TEXT)
RETURNS TABLE (
    id TEXT,
    location_id TEXT,
    name TEXT,
    type TEXT,
    vend_price INTEGER,
    status TEXT,
    pulse_on INTEGER,
    pulse_off INTEGER,
    pulse_count INTEGER,
    updated_at TIMESTAMPTZ,
    location_name TEXT
) LANGUAGE sql STABLE AS $$
    SELECT m.id, m.location_id, m.name, m.type, m.vend_price, m.status,
           m.pulse_on, m.pulse_off, m.pulse_count, m.updated_at,
           l.name AS location_name
    FROM machines m
    JOIN locations l ON m.location_id = l.id
    WHERE l.owner_id = p_owner_id
    ORDER BY m.location_id, m.id;
$$;

-- Dashboard summary stats
CREATE OR REPLACE FUNCTION get_dashboard_stats(p_owner_id TEXT)
RETURNS JSON LANGUAGE sql STABLE AS $$
    SELECT json_build_object(
        'total_revenue', (
            SELECT COALESCE(SUM(t.amount), 0)
            FROM transactions t
            JOIN locations l ON t.location_id = l.id
            WHERE l.owner_id = p_owner_id
        ),
        'total_transactions', (
            SELECT COUNT(*)
            FROM transactions t
            JOIN locations l ON t.location_id = l.id
            WHERE l.owner_id = p_owner_id
        ),
        'location_count', (
            SELECT COUNT(*)
            FROM locations
            WHERE owner_id = p_owner_id
        ),
        'today_revenue', (
            SELECT COALESCE(SUM(t.amount), 0)
            FROM transactions t
            JOIN locations l ON t.location_id = l.id
            WHERE l.owner_id = p_owner_id
              AND t.started_at >= CURRENT_DATE::TEXT
              AND t.started_at < (CURRENT_DATE + 1)::TEXT
        )
    );
$$;

-- Analytics stats with optional date range
CREATE OR REPLACE FUNCTION get_analytics_stats(
    p_owner_id TEXT,
    p_start_date TEXT DEFAULT NULL,
    p_end_date TEXT DEFAULT NULL
)
RETURNS JSON LANGUAGE plpgsql STABLE AS $$
DECLARE
    result JSON;
    v_total_revenue BIGINT;
    v_total_cycles BIGINT;
    v_avg_per_cycle NUMERIC;
    v_revenue_by_day JSON;
    v_cycles_by_day JSON;
    v_machine_usage JSON;
BEGIN
    -- Totals
    SELECT COALESCE(SUM(t.amount), 0), COUNT(*)
    INTO v_total_revenue, v_total_cycles
    FROM transactions t
    JOIN locations l ON t.location_id = l.id
    WHERE l.owner_id = p_owner_id
      AND t.status = 'COMPLETED'
      AND (p_start_date IS NULL OR t.started_at >= p_start_date)
      AND (p_end_date IS NULL OR t.started_at <= p_end_date || ' 23:59:59');

    IF v_total_cycles > 0 THEN
        v_avg_per_cycle := ROUND(v_total_revenue::NUMERIC / v_total_cycles, 1);
    ELSE
        v_avg_per_cycle := 0;
    END IF;

    -- Revenue by day
    SELECT COALESCE(json_agg(row_to_json(r)), '[]'::json)
    INTO v_revenue_by_day
    FROM (
        SELECT LEFT(t.started_at, 10) AS day, SUM(t.amount) AS revenue
        FROM transactions t
        JOIN locations l ON t.location_id = l.id
        WHERE l.owner_id = p_owner_id
          AND t.status = 'COMPLETED'
          AND (p_start_date IS NULL OR t.started_at >= p_start_date)
          AND (p_end_date IS NULL OR t.started_at <= p_end_date || ' 23:59:59')
        GROUP BY LEFT(t.started_at, 10)
        ORDER BY day
    ) r;

    -- Cycles by day
    SELECT COALESCE(json_agg(row_to_json(r)), '[]'::json)
    INTO v_cycles_by_day
    FROM (
        SELECT LEFT(t.started_at, 10) AS day, COUNT(*) AS cycles
        FROM transactions t
        JOIN locations l ON t.location_id = l.id
        WHERE l.owner_id = p_owner_id
          AND t.status = 'COMPLETED'
          AND (p_start_date IS NULL OR t.started_at >= p_start_date)
          AND (p_end_date IS NULL OR t.started_at <= p_end_date || ' 23:59:59')
        GROUP BY LEFT(t.started_at, 10)
        ORDER BY day
    ) r;

    -- Machine usage
    SELECT COALESCE(json_agg(row_to_json(r)), '[]'::json)
    INTO v_machine_usage
    FROM (
        SELECT t.machine_id, m.name, COUNT(*) AS cycles, SUM(t.amount) AS revenue
        FROM transactions t
        JOIN locations l ON t.location_id = l.id
        LEFT JOIN machines m ON t.machine_id = m.id AND t.location_id = m.location_id
        WHERE l.owner_id = p_owner_id
          AND (p_start_date IS NULL OR t.started_at >= p_start_date)
          AND (p_end_date IS NULL OR t.started_at <= p_end_date || ' 23:59:59')
        GROUP BY t.machine_id, m.name
        ORDER BY cycles DESC
    ) r;

    result := json_build_object(
        'total_revenue', v_total_revenue,
        'total_cycles', v_total_cycles,
        'avg_per_cycle', v_avg_per_cycle,
        'revenue_by_day', v_revenue_by_day,
        'cycles_by_day', v_cycles_by_day,
        'machine_usage', v_machine_usage
    );

    RETURN result;
END;
$$;
