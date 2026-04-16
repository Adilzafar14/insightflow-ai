import streamlit as st
import hashlib, hmac, secrets, sqlite3
from datetime import datetime

DB = "insightflow.db"

# ══════════════════════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════════════════════
_sb_client = None

def get_supabase():
    global _sb_client
    if _sb_client:
        return _sb_client
    try:
        from supabase import create_client, Client
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        if url and key:
            _sb_client = create_client(url, key)
            return _sb_client
    except:
        pass
    return None

# ══════════════════════════════════════════════════════
# SQLITE FALLBACK
# ══════════════════════════════════════════════════════
def get_db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = get_db()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, industry TEXT,
            email TEXT DEFAULT '', city TEXT DEFAULT 'Lucknow',
            is_active INTEGER DEFAULT 1,
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
            client_id INTEGER NOT NULL, industry TEXT NOT NULL,
            entry_date TEXT NOT NULL, data TEXT NOT NULL,
            entered_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    if not c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone():
        h, s = _hash_pw("admin@123")
        c.execute("INSERT OR IGNORE INTO users(username,password_hash,salt,role,full_name) VALUES(?,?,?,'admin','Administrator')",
                  ("admin", h, s))
    c.commit(); c.close()

def _hash_pw(pw, salt=None):
    if not salt: salt = secrets.token_hex(16)
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 260000).hex(), salt

def verify_pw(pw, h, s):
    a, _ = _hash_pw(pw, s)
    return hmac.compare_digest(a, h)

# ══════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════
def login(un, pw):
    user = None
    sb = get_supabase()

    # Try Supabase
    if sb:
        try:
            res = sb.table("users").select("*").ilike("username", un.strip()).execute()
            if res.data:
                u = res.data[0]
                cn, ind = None, None
                if u.get("client_id"):
                    try:
                        cr = sb.table("clients").select("name,industry").eq("id", u["client_id"]).execute()
                        if cr.data:
                            cn = cr.data[0]["name"]
                            ind = cr.data[0]["industry"]
                    except: pass
                user = {
                    "id": u["id"], "username": u["username"],
                    "password_hash": u["password_hash"], "salt": u["salt"],
                    "role": u["role"], "client_id": u.get("client_id"),
                    "full_name": u.get("full_name", ""),
                    "is_active": u.get("is_active", 1),
                    "cn": cn, "ind": ind
                }
        except: pass

    # Fallback SQLite
    if not user:
        c = get_db()
        row = c.execute("""
            SELECT u.*, cl.name as cn, cl.industry as ind
            FROM users u LEFT JOIN clients cl ON cl.id = u.client_id
            WHERE u.username = ? COLLATE NOCASE
        """, (un.strip(),)).fetchone()
        c.close()
        if row: user = dict(row)

    if not user: return {"ok": False, "msg": "❌ Username not found"}
    if not user.get("is_active"): return {"ok": False, "msg": "❌ Account disabled"}
    if not verify_pw(pw, user["password_hash"], user["salt"]): return {"ok": False, "msg": "❌ Wrong password"}

    return {
        "ok": True, "id": user["id"], "username": user["username"],
        "role": user["role"], "name": user.get("full_name") or user["username"],
        "client_id": user.get("client_id"), "cn": user.get("cn"), "ind": user.get("ind")
    }

# ══════════════════════════════════════════════════════
# USER MANAGEMENT
# ══════════════════════════════════════════════════════
def create_user(un, pw, role="client", cid=None, fn="", em=""):
    if len(un.strip()) < 3: return {"ok": False, "msg": "Username min 3 chars"}
    if len(pw) < 6: return {"ok": False, "msg": "Password min 6 chars"}
    h, s = _hash_pw(pw)
    sb = get_supabase()

    if sb:
        try:
            sb.table("users").insert({
                "username": un.strip().lower(), "password_hash": h, "salt": s,
                "role": role, "client_id": cid, "full_name": fn, "email": em, "is_active": 1
            }).execute()
            return {"ok": True, "msg": f"✅ User '{un}' created!"}
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                return {"ok": False, "msg": f"❌ Username '{un}' already exists"}

    # Fallback SQLite
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
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("clients").select("*").eq("is_active", 1).order("name").execute()
            if res.data: return res.data
        except: pass
    c = get_db()
    r = c.execute("SELECT * FROM clients WHERE is_active=1 ORDER BY name").fetchall()
    c.close()
    return [dict(x) for x in r]

def get_users():
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("users").select("*").order("role", desc=True).execute()
            users = []
            for u in (res.data or []):
                cn = None
                if u.get("client_id"):
                    try:
                        cr = sb.table("clients").select("name").eq("id", u["client_id"]).execute()
                        if cr.data: cn = cr.data[0]["name"]
                    except: pass
                u["cn"] = cn
                users.append(u)
            return users
        except: pass
    c = get_db()
    r = c.execute("""
        SELECT u.*, cl.name as cn FROM users u
        LEFT JOIN clients cl ON cl.id = u.client_id
        ORDER BY u.role DESC, u.username
    """).fetchall()
    c.close()
    return [dict(x) for x in r]

def add_client(nm, ind, em="", city="Lucknow"):
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("clients").insert({
                "name": nm, "industry": ind, "email": em, "city": city, "is_active": 1
            }).execute()
            if res.data: return res.data[0]["id"]
        except: pass
    c = get_db()
    cur = c.execute("INSERT INTO clients(name,industry,email,city) VALUES(?,?,?,?)", (nm, ind, em, city))
    c.commit(); i = cur.lastrowid; c.close()
    return i

def delete_client(cid):
    sb = get_supabase()
    if sb:
        try:
            sb.table("clients").update({"is_active": 0}).eq("id", cid).execute()
            return
        except: pass
    c = get_db()
    c.execute("UPDATE clients SET is_active=0 WHERE id=?", (cid,))
    c.commit(); c.close()

def upw(uid, npw):
    if len(npw) < 6: return False
    h, s = _hash_pw(npw)
    sb = get_supabase()
    if sb:
        try:
            sb.table("users").update({"password_hash": h, "salt": s}).eq("id", uid).execute()
            return True
        except: pass
    c = get_db()
    c.execute("UPDATE users SET password_hash=?,salt=? WHERE id=?", (h, s, uid))
    c.commit(); c.close()
    return True

def toggle_user(uid):
    sb = get_supabase()
    if sb:
        try:
            res = sb.table("users").select("is_active").eq("id", uid).execute()
            if res.data:
                new_val = 0 if res.data[0]["is_active"] else 1
                sb.table("users").update({"is_active": new_val}).eq("id", uid).execute()
                return
        except: pass
    c = get_db()
    r = c.execute("SELECT is_active FROM users WHERE id=?", (uid,)).fetchone()
    if r:
        c.execute("UPDATE users SET is_active=? WHERE id=?", (0 if r["is_active"] else 1, uid))
        c.commit(); c.close()

def save_entry(client_id, industry, entry_date, data, user_id):
    import json
    sb = get_supabase()
    if sb:
        try:
            sb.table("entries").insert({
                "client_id": client_id, "industry": industry,
                "entry_date": entry_date, "data": json.dumps(data),
                "entered_by": user_id
            }).execute()
            return
        except: pass
    c = get_db()
    c.execute("INSERT INTO entries(client_id,industry,entry_date,data,entered_by) VALUES(?,?,?,?,?)",
              (client_id, industry, entry_date, json.dumps(data), user_id))
    c.commit(); c.close()

def get_entries(client_id, industry=None, limit=30):
    import json
    sb = get_supabase()
    if sb:
        try:
            q = sb.table("entries").select("*").eq("client_id", client_id)
            if industry: q = q.eq("industry", industry)
            res = q.order("entry_date", desc=True).limit(limit).execute()
            result = []
            for r in (res.data or []):
                if isinstance(r.get("data"), str):
                    r["data"] = json.loads(r["data"])
                result.append(r)
            return result
        except: pass
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
        d["data"] = json.loads(d["data"])
        result.append(d)
    return result

def save_client_data(client_id, industry, filename, df):
    return False

def load_client_data(client_id):
    return None, None, None

# Session
KEY = "insightflow_v2"
def is_logged_in(): return st.session_state.get(KEY) is not None
def get_user(): return st.session_state.get(KEY)
def is_admin(): u = get_user(); return u and u["role"] == "admin"
def is_client(): u = get_user(); return u and u["role"] == "client"
def set_session(u): st.session_state[KEY] = u
def do_logout():
    st.session_state[KEY] = None
    for k in ["df", "result", "page", "ac", "ai_insight", "chat_history", "data_summary"]:
        st.session_state.pop(k, None)
