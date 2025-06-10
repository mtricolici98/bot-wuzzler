# Simple in-memory MMR storage and calculation

import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("MMR_DB_PATH", "/app/db/mmr.db")
DEFAULT_MMR = 1000

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.commit()
    conn.close()

def init_db():
    with get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS mmr (
            user_id TEXT PRIMARY KEY,
            mmr INTEGER NOT NULL
        )''')

def init_history():
    with get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS history (
            user_id TEXT PRIMARY KEY,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0
        )''')

def get_mmr(user_id):
    with get_conn() as conn:
        cur = conn.execute('SELECT mmr FROM mmr WHERE user_id=?', (user_id,))
        row = cur.fetchone()
        return row[0] if row else DEFAULT_MMR

def set_mmr(user_id, mmr):
    with get_conn() as conn:
        conn.execute('INSERT OR REPLACE INTO mmr (user_id, mmr) VALUES (?, ?)', (user_id, mmr))

def get_all_mmr():
    with get_conn() as conn:
        cur = conn.execute('SELECT user_id, mmr FROM mmr')
        return dict(cur.fetchall())

def update_mmr(winners, losers, score_diff):
    # Returns a dict of user_id -> (old_mmr, new_mmr, delta)
    K = 32
    deltas = {}
    for user in winners:
        old = get_mmr(user)
        delta = int(K * (1 - 0.5 + score_diff/10))
        new = old + delta
        set_mmr(user, new)
        deltas[user] = (old, new, delta)
    for user in losers:
        old = get_mmr(user)
        delta = int(-K * (1 - 0.5 + score_diff/10))
        new = max(100, old + delta)
        set_mmr(user, new)
        deltas[user] = (old, new, delta)
    return deltas

def update_mmr_elo(winners, losers, K=32):
    # Team Elo: adjust by average MMR, expected score
    winner_avg = sum(get_mmr(u) for u in winners) / len(winners)
    loser_avg = sum(get_mmr(u) for u in losers) / len(losers)
    E_winner = 1 / (1 + 10 ** ((loser_avg - winner_avg) / 400))
    E_loser = 1 - E_winner
    deltas = {}
    for user in winners:
        old = get_mmr(user)
        delta = int(K * (1 - E_winner))
        new = old + delta
        set_mmr(user, new)
        deltas[user] = (old, new, delta)
    for user in losers:
        old = get_mmr(user)
        delta = int(K * (0 - E_loser))
        new = max(100, old + delta)
        set_mmr(user, new)
        deltas[user] = (old, new, delta)
    return deltas

def record_history(winners, losers):
    with get_conn() as conn:
        for user in winners:
            conn.execute('INSERT INTO history (user_id, wins, losses) VALUES (?, 1, 0) ON CONFLICT(user_id) DO UPDATE SET wins = wins + 1', (user,))
        for user in losers:
            conn.execute('INSERT INTO history (user_id, wins, losses) VALUES (?, 0, 1) ON CONFLICT(user_id) DO UPDATE SET losses = losses + 1', (user,))

def get_history(user_id):
    with get_conn() as conn:
        cur = conn.execute('SELECT wins, losses FROM history WHERE user_id = ?', (user_id,))
        row = cur.fetchone()
        return row if row else (0, 0)

# Call this at startup
init_db()
init_history()
