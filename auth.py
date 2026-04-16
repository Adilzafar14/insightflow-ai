import streamlit as st
import hashlib, hmac, secrets, sqlite3
from datetime import datetime

DB = "insightflow.db"

def get_db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = get_db()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, industry TEXT, email TEXT DEFAULT '',
            city TEXT DEFAULT 'Lucknow', is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL, salt TEXT NOT NULL,
            role TEXT DEFAULT 'client', client_id INTEGER,
            full_name TEXT DEFAULT '', email TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1, last_login TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            industry TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            data TEXT NOT NULL,
            entered_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    if not c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone():
        h, s = _hash_pw("admin@123")
        c.execute("INSERT INTO users(username,password_hash,salt,role,full_name) VALUES(?,?,?,'admin','Administrator')",
                  ("admin", h, s))
    c.commit(); c.close()

def _hash_pw(pw, salt=None):
    if not salt: salt = secrets.token_hex(16)
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 260000).hex(), salt

def verify_pw(pw, h, s):
    a, _ = _hash_pw(pw, s)
    return hmac.compare_digest(a, h)

def login(un, pw):
    c = get_db()
    u = c.execute("""
        SELECT u.*, cl.name as cn, cl.industry as ind
        FROM users u LEFT JOIN clients cl ON cl.id = u.client_id
        WHERE u.username = ? COLLATE NOCASE
    """, (un.strip(),)).fetchone()
    c.close()
    if not u: return {"ok": False, "msg": "❌ Username not found"}
    if not u["is_active"]: return {"ok": False, "msg": "❌ Account disabled"}
    if not verify_pw(pw, u["password_hash"], u["salt"]): return {"ok": False, "msg": "❌ Wrong password"}
    c = get_db()
    c.execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (u["id"],))
    c.commit(); c.close()
    return {"ok": True, "id": u["id"], "username": u["username"], "role": u["role"],
            "name": u["full_name"] or u["username"], "client_id": u["client_id"],
            "cn": u["cn"], "ind": u["ind"]}

def create_user(un, pw, role="client", cid=None, fn="", em=""):
    if len(un.strip()) < 3: return {"ok": False, "msg": "Username min 3 chars"}
    if len(pw) < 6: return {"ok": False, "msg": "Password min 6 chars"}
    h, s = _hash_pw(pw)
    c = get_db()
    try:
        c.execute("INSERT INTO users(username,password_hash,salt,role,client_id,full_name,email) VALUES(?,?,?,?,?,?,?)",
                  (un.strip().lower(), h, s, role, cid, fn, em))
        c.commit(); c.close()
        return {"ok": True, "msg": f"✅ User '{un}' created!"}
    except sqlite3.IntegrityError:
        c.close()
        return {"ok": False, "msg": f"❌ Username '{un}' already exists"}

def get_clients():
    c = get_db()
    r = c.execute("SELECT * FROM clients WHERE is_active=1 ORDER BY name").fetchall()
    c.close(); return [dict(x) for x in r]

def get_users():
    c = get_db()
    r = c.execute("""
        SELECT u.*, cl.name as cn FROM users u
        LEFT JOIN clients cl ON cl.id = u.client_id
        ORDER BY u.role DESC, u.username
    """).fetchall()
    c.close(); return [dict(x) for x in r]


def save_entry(client_id, industry, entry_date, data, user_id):
    import json
    c = get_db()
    c.execute("INSERT INTO entries(client_id,industry,entry_date,data,entered_by) VALUES(?,?,?,?,?)",
              (client_id, industry, entry_date, json.dumps(data), user_id))
    c.commit(); c.close()

def get_entries(client_id, industry=None, limit=30):
    import json
    c = get_db()
    if industry:
        rows = c.execute("SELECT * FROM entries WHERE client_id=? AND industry=? ORDER BY entry_date DESC LIMIT ?",
                        (client_id, industry, limit)).fetchall()
    else:
        rows = c.execute("SELECT * FROM entries WHERE client_id=? ORDER BY entry_date DESC LIMIT ?",
                        (client_id, limit)).fetchall()
    c.close()
    result = []
    for r in rows:
        d = dict(r)
        d['data'] = json.loads(d['data'])
        result.append(d)
    return result

def entries_to_df(entries, industry):
    if not entries: return None
    rows = []
    for e in entries:
        row = {'Date': e['entry_date']}
        row.update(e['data'])
        rows.append(row)
    return pd.DataFrame(rows)

def add_client(nm, ind, em="", city="Lucknow"):
    c = get_db()
    cur = c.execute("INSERT INTO clients(name,industry,email,city) VALUES(?,?,?,?)", (nm, ind, em, city))
    c.commit(); i = cur.lastrowid; c.close(); return i

def upw(uid, npw):
    if len(npw) < 6: return False
    h, s = _hash_pw(npw)
    c = get_db()
    c.execute("UPDATE users SET password_hash=?,salt=? WHERE id=?", (h, s, uid))
    c.commit(); c.close(); return True

def toggle_user(uid):
    c = get_db()
    r = c.execute("SELECT is_active FROM users WHERE id=?", (uid,)).fetchone()
    if r:
        c.execute("UPDATE users SET is_active=? WHERE id=?", (0 if r["is_active"] else 1, uid))
        c.commit(); c.close()

# Session helpers
KEY = "insightflow_v2"
def is_logged_in(): return st.session_state.get(KEY) is not None
def get_user(): return st.session_state.get(KEY)
def is_admin(): u = get_user(); return u and u["role"] == "admin"
def is_client(): u = get_user(); return u and u["role"] == "client"
def set_session(u): st.session_state[KEY] = u
def do_logout():
    st.session_state[KEY] = None
    for k in ["df", "result", "page", "ac", "ai_insight"]:
        st.session_state.pop(k)

# ══════════════════════════════════════════════════════════════════
# INDUSTRY DETECTION - Strict & Accurate
# ══════════════════════════════════════════════════════════════════

def save_entry(client_id, industry, entry_date, data, user_id):
    import json
    c = get_db()
    c.execute("INSERT INTO entries(client_id,industry,entry_date,data,entered_by) VALUES(?,?,?,?,?)",
              (client_id, industry, entry_date, json.dumps(data), user_id))
    c.commit(); c.close()

def get_entries(client_id, industry=None, limit=30):
    import json
    c = get_db()
    if industry:
        rows = c.execute("SELECT * FROM entries WHERE client_id=? AND industry=? ORDER BY entry_date DESC LIMIT ?",
                        (client_id, industry, limit)).fetchall()
    else:
        rows = c.execute("SELECT * FROM entries WHERE client_id=? ORDER BY entry_date DESC LIMIT ?",
                        (client_id, limit)).fetchall()
    c.close()
    result = []
    for r in rows:
        d = dict(r)
        d['data'] = json.loads(d['data'])
        result.append(d)
    return result

# Session helpers
KEY = "insightflow_v2"
def is_logged_in(): return st.session_state.get(KEY) is not None
def get_user(): return st.session_state.get(KEY)
def is_admin(): u = get_user(); return u and u["role"] == "admin"
def is_client(): u = get_user(); return u and u["role"] == "client"
def set_session(u): st.session_state[KEY] = u
def do_logout():
    st.session_state[KEY] = None
    for k in ["df", "result", "page", "ac", "ai_insight"]:
        st.session_state.pop(k, None)

def delete_client(cid):
    c = get_db()
    c.execute('UPDATE clients SET is_active=0 WHERE id=?', (cid,))
    c.commit()
    c.close()

def save_client_data(client_id, industry, filename, df):
    return False

def load_client_data(client_id):
    return None, None, None

def create_user(un, pw, role='client', cid=None, fn='', em=''):
    if len(un.strip()) < 3: return {'ok': False, 'msg': 'Username min 3 chars'}
    if len(pw) < 6: return {'ok': False, 'msg': 'Password min 6 chars'}
    h, s = _hash_pw(pw)
    sb = get_supabase()
    if sb:
        try:
            sb.table('users').insert({'username': un.strip().lower(), 'password_hash': h, 'salt': s, 'role': role, 'client_id': cid, 'full_name': fn, 'email': em, 'is_active': 1}).execute()
            return {'ok': True, 'msg': f'User created!'}
        except Exception as e:
            if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                return {'ok': False, 'msg': 'Username already exists'}
    c = get_db()
    try:
        c.execute('INSERT INTO users(username,password_hash,salt,role,client_id,full_name,email) VALUES(?,?,?,?,?,?,?)', (un.strip().lower(), h, s, role, cid, fn, em))
        c.commit(); c.close()
        return {'ok': True, 'msg': 'User created!'}
    except:
        c.close()
        return {'ok': False, 'msg': 'Username already exists'}
