import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import hashlib, hmac, secrets, sqlite3, io, os
from datetime import datetime

st.set_page_config(page_title="InsightFlow AI",page_icon="📊",layout="wide",initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif !important;}
[data-testid="stAppViewContainer"]{background:#0A0E1A;}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stSidebar"]{background:#0D1117 !important;border-right:1px solid #1E2D3D;}
[data-testid="stSidebar"] *{color:#8B949E !important;}
[data-testid="stSidebar"] .stButton button{background:#161B22 !important;border:1px solid #30363D !important;color:#E6EDF3 !important;border-radius:8px !important;font-weight:500 !important;transition:all 0.2s !important;}
[data-testid="stSidebar"] .stButton button:hover{background:#21262D !important;border-color:#58A6FF !important;}
[data-testid="stSidebar"] .stButton button[kind="primary"]{background:linear-gradient(135deg,#1A6ED8,#2D6A9F) !important;border-color:#1A6ED8 !important;color:white !important;}
div[data-testid="stMetric"]{background:#161B22;border:1px solid #21262D;border-radius:10px;padding:1rem;}
div[data-testid="stMetric"] label{color:#8B949E !important;}
div[data-testid="stMetric"] div{color:#E6EDF3 !important;}
.stTabs [data-baseweb="tab-list"]{background:#161B22;border-radius:10px;padding:4px;}
.stTabs [data-baseweb="tab"]{color:#8B949E !important;border-radius:6px !important;}
.stTabs [aria-selected="true"]{background:#21262D !important;color:#E6EDF3 !important;}
[data-testid="stFileUploader"]{background:#161B22;border:1px dashed #30363D;border-radius:10px;padding:1rem;}
.hero{background:linear-gradient(135deg,#0D1117 0%,#161B22 50%,#0D1F3C 100%);border:1px solid #21262D;border-radius:16px;padding:2rem 2.5rem;margin-bottom:1.5rem;position:relative;overflow:hidden;}
.hero h1{font-size:1.8rem;font-weight:800;color:#E6EDF3;margin:0;}
.hero p{color:#8B949E;margin:0.4rem 0 0;font-size:0.9rem;}
.hero .badge{display:inline-block;background:#1A6ED822;color:#58A6FF;border:1px solid #1A6ED844;border-radius:20px;padding:3px 12px;font-size:0.75rem;font-weight:600;margin-top:0.7rem;}
.kpi{background:#161B22;border:1px solid #21262D;border-radius:12px;padding:1.2rem 1.4rem;transition:all 0.2s;position:relative;overflow:hidden;margin-bottom:0.5rem;}
.kpi::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;background:var(--accent,#58A6FF);}
.kpi:hover{border-color:#30363D;transform:translateY(-2px);}
.kpi-l{font-size:0.68rem;font-weight:600;color:#8B949E;text-transform:uppercase;letter-spacing:1px;}
.kpi-v{font-size:1.7rem;font-weight:800;color:#E6EDF3;margin:0.3rem 0 0;}
.kpi-s{font-size:0.73rem;color:#6E7681;margin-top:3px;}
.ins{border-radius:10px;padding:0.9rem 1.2rem;margin:0.4rem 0;font-size:0.88rem;line-height:1.7;border:1px solid;}
.ig{background:#0D2818;border-color:#1A4731;color:#3FB950;}
.iw{background:#2D1F00;border-color:#4D3300;color:#D29922;}
.id{background:#2D0C0C;border-color:#4D1515;color:#F85149;}
.ii{background:#0D1F3C;border-color:#1A3A5C;color:#58A6FF;}
.card{background:#161B22;border:1px solid #21262D;border-radius:12px;padding:1.2rem;}
.sec{font-size:0.82rem;font-weight:600;color:#8B949E;text-transform:uppercase;letter-spacing:1px;margin:1.2rem 0 0.7rem;padding-bottom:0.5rem;border-bottom:1px solid #21262D;}
</style>
""",unsafe_allow_html=True)

DB="insightflow.db"
PALETTE=["#58A6FF","#3FB950","#D29922","#F85149","#BC8CFF","#F78166","#56D364","#79C0FF"]

def get_db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    c=get_db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,industry TEXT,email TEXT DEFAULT '',city TEXT DEFAULT 'Lucknow',is_active INTEGER DEFAULT 1,created_at TEXT DEFAULT(datetime('now')));
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE COLLATE NOCASE,password_hash TEXT NOT NULL,salt TEXT NOT NULL,role TEXT DEFAULT 'client',client_id INTEGER,full_name TEXT DEFAULT '',email TEXT DEFAULT '',is_active INTEGER DEFAULT 1,last_login TEXT,created_at TEXT DEFAULT(datetime('now')));
    """)
    if not c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone():
        h,s=_hp("admin@123")
        c.execute("INSERT INTO users(username,password_hash,salt,role,full_name)VALUES(?,?,?,'admin','Administrator')",("admin",h,s))
    c.commit(); c.close()

def _hp(pw,salt=None):
    if not salt: salt=secrets.token_hex(16)
    return hashlib.pbkdf2_hmac("sha256",pw.encode(),salt.encode(),260000).hex(),salt

def vp(pw,h,s):
    a,_=_hp(pw,s); return hmac.compare_digest(a,h)

def do_login(un,pw):
    c=get_db()
    u=c.execute("SELECT u.*,cl.name as cn,cl.industry as ind FROM users u LEFT JOIN clients cl ON cl.id=u.client_id WHERE u.username=? COLLATE NOCASE",(un.strip(),)).fetchone()
    c.close()
    if not u: return{"ok":False,"msg":"❌ Username nahi mila"}
    if not u["is_active"]: return{"ok":False,"msg":"❌ Account disabled hai"}
    if not vp(pw,u["password_hash"],u["salt"]): return{"ok":False,"msg":"❌ Password galat hai"}
    c=get_db(); c.execute("UPDATE users SET last_login=datetime('now') WHERE id=?",(u["id"],)); c.commit(); c.close()
    return{"ok":True,"id":u["id"],"username":u["username"],"role":u["role"],"name":u["full_name"] or u["username"],"client_id":u["client_id"],"cn":u["cn"],"ind":u["ind"]}

def create_user(un,pw,role="client",cid=None,fn="",em=""):
    if len(un.strip())<3: return{"ok":False,"msg":"Username min 3 chars"}
    if len(pw)<6: return{"ok":False,"msg":"Password min 6 chars"}
    h,s=_hp(pw); c=get_db()
    try:
        c.execute("INSERT INTO users(username,password_hash,salt,role,client_id,full_name,email)VALUES(?,?,?,?,?,?,?)",(un.strip().lower(),h,s,role,cid,fn,em))
        c.commit(); c.close(); return{"ok":True,"msg":f"✅ User '{un}' banaya!"}
    except sqlite3.IntegrityError:
        c.close(); return{"ok":False,"msg":f"❌ '{un}' already exists"}

def get_clients():
    c=get_db(); r=c.execute("SELECT * FROM clients WHERE is_active=1 ORDER BY name").fetchall(); c.close(); return[dict(x) for x in r]

def get_users():
    c=get_db(); r=c.execute("SELECT u.*,cl.name as cn FROM users u LEFT JOIN clients cl ON cl.id=u.client_id ORDER BY u.role DESC,u.username").fetchall(); c.close(); return[dict(x) for x in r]

def add_client(nm,ind,em="",city="Lucknow"):
    c=get_db(); cur=c.execute("INSERT INTO clients(name,industry,email,city)VALUES(?,?,?,?)",(nm,ind,em,city))
    c.commit(); i=cur.lastrowid; c.close(); return i

def upw(uid,npw):
    if len(npw)<6: return False
    h,s=_hp(npw); c=get_db(); c.execute("UPDATE users SET password_hash=?,salt=? WHERE id=?",(h,s,uid)); c.commit(); c.close(); return True

def tog(uid):
    c=get_db(); r=c.execute("SELECT is_active FROM users WHERE id=?",(uid,)).fetchone()
    if r: c.execute("UPDATE users SET is_active=? WHERE id=?",(0 if r["is_active"] else 1,uid)); c.commit(); c.close()

K="ifuser"
def li(): return st.session_state.get(K) is not None
def gu(): return st.session_state.get(K)
def ia(): u=gu(); return u and u["role"]=="admin"
def ic(): u=gu(); return u and u["role"]=="client"
def ss(u): st.session_state[K]=u
def lo():
    st.session_state[K]=None
    for k in ["df","cols","metrics","charts","insights","page","ac","industry_type"]:
        st.session_state.pop(k,None)

# ══════════════════════════
# SMART INDUSTRY DETECTOR
# ══════════════════════════
def detect_industry(df):
    # Check both original and lowercase column names
    cols_lower = [c.lower() for c in df.columns]
    col_str = " ".join(cols_lower)
    
    # Hospital keywords
    hosp_kw = ["patient","admission","discharge","diagnosis","treatment_cost","treatment","disease","doctor","ward"]
    if any(w in col_str for w in hosp_kw):
        return "hospital"
    
    # Logistics keywords  
    logi_kw = ["shipment","delivery_date","freight","vehicle_type","vehicle","warehouse","distance_km","distance","shipment_cost","fuel_cost"]
    if any(w in col_str for w in logi_kw):
        return "logistics"
    
    # Ecommerce keywords
    ecom_kw = ["product_price","order_date","order_status","order_id","payment_mode","discount","quantity","product","cart"]
    if any(w in col_str for w in ecom_kw):
        return "ecommerce"
    
    # Education keywords
    edu_kw = ["student","attendance","cgpa","marks","course","enrollment","placement","semester","backlog","fees_paid","hostel"]
    if any(w in col_str for w in edu_kw):
        return "education"
    
    return "generic"

# ══════════════════════════
# INDUSTRY-SPECIFIC PIPELINE
# ══════════════════════════
def process_hospital(df):
    kpis={}; charts={}; insights=[]
    # Date
    for col in ["Admission_Date","admission_date","Date","date"]:
        if col in df.columns:
            df[col]=pd.to_datetime(df[col],errors="coerce")
            df["_month"]=df[col].dt.to_period("M").astype(str)
            break
    for col in ["Discharge_Date","discharge_date"]:
        if col in df.columns:
            df[col]=pd.to_datetime(df[col],errors="coerce")
            break
    # LOS
    if "Admission_Date" in df.columns and "Discharge_Date" in df.columns:
        df["LOS"]=(df["Discharge_Date"]-df["Admission_Date"]).dt.days.abs()
        kpis["avg_stay"]=round(df["LOS"].mean(),1)
    # Cost col
    cost_col=next((c for c in df.columns if "cost" in c.lower() or "revenue" in c.lower()),None)
    if cost_col:
        kpis["total_revenue"]=round(df[cost_col].sum(),0)
        kpis["avg_cost"]=round(df[cost_col].mean(),0)
    kpis["total_patients"]=len(df)
    kpis["avg_age"]=round(df["Age"].mean(),0) if "Age" in df.columns else None
    # Charts
    dept_col=next((c for c in df.columns if "dept" in c.lower() or "department" in c.lower()),None)
    if dept_col and cost_col:
        d=df.groupby(dept_col)[cost_col].sum().sort_values(ascending=False).reset_index()
        d.columns=["Department","Revenue"]
        charts["dept_revenue"]={"t":"bar","data":d.to_dict("records"),"x":"Revenue","y":"Department","title":"Revenue by Department"}
        d2=df[dept_col].value_counts().reset_index()
        d2.columns=["Department","Patients"]
        charts["dept_patients"]={"t":"bar","data":d2.to_dict("records"),"x":"Patients","y":"Department","title":"Patients by Department"}
    dis_col=next((c for c in df.columns if "disease" in c.lower() or "diagnosis" in c.lower()),None)
    if dis_col:
        d=df[dis_col].value_counts().head(8).reset_index()
        d.columns=["Disease","Cases"]
        charts["diseases"]={"t":"bar","data":d.to_dict("records"),"x":"Cases","y":"Disease","title":"Top Diseases"}
    status_col=next((c for c in df.columns if "status" in c.lower()),None)
    if status_col:
        d=df[status_col].value_counts().reset_index()
        d.columns=["Status","Count"]
        charts["status"]={"t":"pie","data":d.to_dict("records"),"n":"Status","v":"Count","title":"Patient Status"}
    gender_col=next((c for c in df.columns if "gender" in c.lower() or "sex" in c.lower()),None)
    if gender_col:
        d=df[gender_col].value_counts().reset_index()
        d.columns=["Gender","Count"]
        charts["gender"]={"t":"pie","data":d.to_dict("records"),"n":"Gender","v":"Count","title":"Gender Split"}
    pay_col=next((c for c in df.columns if "payment" in c.lower() or "pay_mode" in c.lower()),None)
    if pay_col:
        d=df[pay_col].value_counts().reset_index()
        d.columns=["Mode","Count"]
        charts["payment"]={"t":"pie","data":d.to_dict("records"),"n":"Mode","v":"Count","title":"Payment Mode"}
    city_col=next((c for c in df.columns if "city" in c.lower()),None)
    if city_col:
        d=df[city_col].value_counts().head(8).reset_index()
        d.columns=["City","Patients"]
        charts["city"]={"t":"bar","data":d.to_dict("records"),"x":"Patients","y":"City","title":"Patients by City"}
    if "_month" in df.columns and cost_col:
        d=df.groupby("_month")[cost_col].sum().reset_index()
        d.columns=["Month","Revenue"]
        charts["monthly_revenue"]={"t":"line","data":d.to_dict("records"),"x":"Month","y":"Revenue","title":"Monthly Revenue"}
        d2=df.groupby("_month").size().reset_index(name="Patients")
        d2.columns=["Month","Patients"]
        charts["monthly_patients"]={"t":"line","data":d2.to_dict("records"),"x":"Month","y":"Patients","title":"Monthly Patients"}
    # Insights
    insights.append(("i",f"🏥 **Total Patients:** {kpis['total_patients']:,}"))
    if kpis.get("total_revenue"): insights.append(("i",f"💰 **Total Revenue:** ₹{kpis['total_revenue']/1e7:.2f}Cr | Avg: ₹{kpis['avg_cost']:,.0f}/patient"))
    if kpis.get("avg_stay"): insights.append(("g" if kpis["avg_stay"]<=7 else "w",f"🛏️ **Avg Length of Stay:** {kpis['avg_stay']} days {'✅ Good' if kpis['avg_stay']<=7 else '⚠️ High — discharge planning improve karo'}"))
    if kpis.get("avg_age"): insights.append(("i",f"👤 **Avg Patient Age:** {kpis['avg_age']:.0f} years"))
    if dept_col:
        top_dept=df[dept_col].value_counts().idxmax()
        insights.append(("i",f"🏨 **Busiest Department:** {top_dept}"))
    if dis_col:
        top_dis=df[dis_col].value_counts().idxmax()
        insights.append(("i",f"🦠 **Most Common Disease:** {top_dis}"))
    return kpis,charts,insights

def process_ecommerce(df):
    kpis={}; charts={}; insights=[]
    # Calculate revenue correctly
    price_col=next((c for c in df.columns if "price" in c.lower() or "product_price" in c.lower()),None)
    qty_col=next((c for c in df.columns if "qty" in c.lower() or "quantity" in c.lower()),None)
    disc_col=next((c for c in df.columns if "discount" in c.lower()),None)
    date_col=next((c for c in df.columns if "date" in c.lower() or "order_date" in c.lower()),None)
    cat_col=next((c for c in df.columns if "category" in c.lower() or "cat" in c.lower()),None)
    pay_col=next((c for c in df.columns if "payment" in c.lower()),None)
    city_col=next((c for c in df.columns if "city" in c.lower()),None)
    status_col=next((c for c in df.columns if "status" in c.lower()),None)
    cust_col=next((c for c in df.columns if "customer" in c.lower()),None)

    # Calculate Revenue = Price × Quantity
    if price_col and qty_col:
        df["_revenue"]=df[price_col]*df[qty_col]
        if disc_col:
            df["_net_revenue"]=df["_revenue"]*(1-df[disc_col]/100)
        else:
            df["_net_revenue"]=df["_revenue"]
        kpis["gross_revenue"]=round(df["_revenue"].sum(),0)
        kpis["net_revenue"]=round(df["_net_revenue"].sum(),0)
        kpis["avg_order_value"]=round(df["_revenue"].mean(),0)
    if disc_col: kpis["avg_discount"]=round(df[disc_col].mean(),1)
    kpis["total_orders"]=len(df)
    if cust_col: kpis["unique_customers"]=df[cust_col].nunique()

    # Date trends
    if date_col:
        df[date_col]=pd.to_datetime(df[date_col],errors="coerce")
        df["_month"]=df[date_col].dt.to_period("M").astype(str)
        d=df.groupby("_month")["_net_revenue"].sum().reset_index()
        d.columns=["Month","Revenue"]
        charts["monthly_revenue"]={"t":"line","data":d.to_dict("records"),"x":"Month","y":"Revenue","title":"Monthly Revenue (Net)"}
        d2=df.groupby("_month").size().reset_index(name="Orders")
        d2.columns=["Month","Orders"]
        charts["monthly_orders"]={"t":"line","data":d2.to_dict("records"),"x":"Month","y":"Orders","title":"Monthly Orders"}

    # Category
    if cat_col:
        d=df.groupby(cat_col)["_net_revenue"].sum().sort_values(ascending=False).reset_index()
        d.columns=["Category","Revenue"]
        charts["category_revenue"]={"t":"bar","data":d.to_dict("records"),"x":"Revenue","y":"Category","title":"Revenue by Category"}
        d2=df[cat_col].value_counts().reset_index()
        d2.columns=["Category","Orders"]
        charts["category_orders"]={"t":"pie","data":d2.to_dict("records"),"n":"Category","v":"Orders","title":"Orders by Category"}

    # Payment
    if pay_col:
        d=df[pay_col].value_counts().reset_index()
        d.columns=["Mode","Orders"]
        charts["payment"]={"t":"pie","data":d.to_dict("records"),"n":"Mode","v":"Orders","title":"Payment Mode"}

    # City
    if city_col:
        d=df.groupby(city_col)["_net_revenue"].sum().sort_values(ascending=False).head(8).reset_index()
        d.columns=["City","Revenue"]
        charts["city"]={"t":"bar","data":d.to_dict("records"),"x":"Revenue","y":"City","title":"Revenue by City"}

    # Status
    if status_col:
        d=df[status_col].value_counts().reset_index()
        d.columns=["Status","Orders"]
        charts["status"]={"t":"pie","data":d.to_dict("records"),"n":"Status","v":"Orders","title":"Order Status"}

    # Insights
    insights.append(("i",f"🛒 **Total Orders:** {kpis['total_orders']:,} | Unique Customers: {kpis.get('unique_customers','N/A')}"))
    if kpis.get("gross_revenue"):
        insights.append(("i",f"💰 **Gross Revenue:** ₹{kpis['gross_revenue']/1e7:.2f}Cr | **Net (after discount):** ₹{kpis['net_revenue']/1e7:.2f}Cr"))
    if kpis.get("avg_discount"):
        insights.append(("w" if kpis["avg_discount"]>20 else "i",f"🏷️ **Avg Discount:** {kpis['avg_discount']:.1f}% {'— bahut zyada hai, margin check karo!' if kpis['avg_discount']>20 else '— reasonable hai'}"))
    if kpis.get("avg_order_value"):
        insights.append(("i",f"📦 **Avg Order Value:** ₹{kpis['avg_order_value']:,.0f}"))
    if cat_col:
        top_cat=df.groupby(cat_col)["_net_revenue"].sum().idxmax()
        insights.append(("i",f"⭐ **Top Category:** {top_cat}"))
    if city_col:
        top_city=df.groupby(city_col)["_net_revenue"].sum().idxmax()
        insights.append(("i",f"📍 **Top City:** {top_city}"))
    if status_col:
        ret=df[status_col].str.lower().isin(["returned","cancelled"]).mean()*100
        insights.append(("w" if ret>15 else "g",f"↩️ **Return/Cancel Rate:** {ret:.1f}% {'— high hai!' if ret>15 else '— good!'}"))
    return kpis,charts,insights

def process_logistics(df):
    kpis={}; charts={}; insights=[]
    ship_date=next((c for c in df.columns if "shipment_date" in c.lower() or "dispatch" in c.lower()),None)
    del_date=next((c for c in df.columns if "delivery_date" in c.lower()),None)
    cost_col=next((c for c in df.columns if "shipment_cost" in c.lower() or "freight" in c.lower()),None)
    fuel_col=next((c for c in df.columns if "fuel" in c.lower()),None)
    dist_col=next((c for c in df.columns if "distance" in c.lower() or "km" in c.lower()),None)
    status_col=next((c for c in df.columns if "status" in c.lower()),None)
    vehicle_col=next((c for c in df.columns if "vehicle" in c.lower()),None)
    wh_col=next((c for c in df.columns if "warehouse" in c.lower()),None)
    origin_col=next((c for c in df.columns if "origin" in c.lower()),None)
    dest_col=next((c for c in df.columns if "destination" in c.lower()),None)

    # Transit days
    if ship_date and del_date:
        df[ship_date]=pd.to_datetime(df[ship_date],errors="coerce")
        df[del_date]=pd.to_datetime(df[del_date],errors="coerce")
        df["_transit"]=(df[del_date]-df[ship_date]).dt.days.abs()
        kpis["avg_transit_days"]=round(df["_transit"].mean(),1)
        kpis["max_transit_days"]=int(df["_transit"].max())
        df["_month"]=df[ship_date].dt.to_period("M").astype(str)

    kpis["total_shipments"]=len(df)
    if cost_col:
        kpis["total_revenue"]=round(df[cost_col].sum(),0)
        kpis["avg_cost"]=round(df[cost_col].mean(),0)
    if fuel_col:
        kpis["total_fuel"]=round(df[fuel_col].sum(),0)
        if cost_col: kpis["fuel_pct"]=round(df[fuel_col].sum()/df[cost_col].sum()*100,1)
    if dist_col and cost_col:
        kpis["avg_cost_per_km"]=round((df[cost_col]/df[dist_col]).mean(),0)

    # Status
    if status_col:
        sc=df[status_col].value_counts()
        d=sc.reset_index(); d.columns=["Status","Count"]
        charts["status"]={"t":"pie","data":d.to_dict("records"),"n":"Status","v":"Count","title":"Shipment Status"}
        del_rate=df[status_col].str.lower().isin(["delivered"]).mean()*100
        kpis["delivery_rate"]=round(del_rate,1)
        delay_rate=df[status_col].str.lower().isin(["delayed"]).mean()*100
        kpis["delay_rate"]=round(delay_rate,1)

    # Vehicle
    if vehicle_col and cost_col:
        d=df.groupby(vehicle_col)[cost_col].sum().sort_values(ascending=False).reset_index()
        d.columns=["Vehicle","Revenue"]
        charts["vehicle_revenue"]={"t":"bar","data":d.to_dict("records"),"x":"Revenue","y":"Vehicle","title":"Revenue by Vehicle Type"}
        d2=df[vehicle_col].value_counts().reset_index()
        d2.columns=["Vehicle","Shipments"]
        charts["vehicle_count"]={"t":"pie","data":d2.to_dict("records"),"n":"Vehicle","v":"Shipments","title":"Shipments by Vehicle"}

    # Warehouse
    if wh_col and cost_col:
        d=df.groupby(wh_col)[cost_col].sum().sort_values(ascending=False).reset_index()
        d.columns=["Warehouse","Revenue"]
        charts["warehouse"]={"t":"bar","data":d.to_dict("records"),"x":"Revenue","y":"Warehouse","title":"Revenue by Warehouse"}

    # Routes
    if origin_col and dest_col:
        df["_route"]=df[origin_col]+" → "+df[dest_col]
        d=df["_route"].value_counts().head(10).reset_index()
        d.columns=["Route","Shipments"]
        charts["routes"]={"t":"bar","data":d.to_dict("records"),"x":"Shipments","y":"Route","title":"Top Routes"}

    # Monthly
    if "_month" in df.columns and cost_col:
        d=df.groupby("_month")[cost_col].sum().reset_index()
        d.columns=["Month","Revenue"]
        charts["monthly_revenue"]={"t":"line","data":d.to_dict("records"),"x":"Month","y":"Revenue","title":"Monthly Revenue"}
        d2=df.groupby("_month").size().reset_index(name="Shipments")
        d2.columns=["Month","Shipments"]
        charts["monthly_shipments"]={"t":"line","data":d2.to_dict("records"),"x":"Month","y":"Shipments","title":"Monthly Shipments"}

    # Insights
    insights.append(("i",f"🚚 **Total Shipments:** {kpis['total_shipments']:,}"))
    if kpis.get("total_revenue"): insights.append(("i",f"💰 **Total Revenue:** ₹{kpis['total_revenue']/1e5:.2f}L | Avg: ₹{kpis['avg_cost']:,.0f}/shipment"))
    if kpis.get("delivery_rate"): insights.append(("g" if kpis["delivery_rate"]>80 else "w",f"✅ **Delivery Rate:** {kpis['delivery_rate']:.1f}% {'— Good!' if kpis['delivery_rate']>80 else '— Low, improve karo!'}"))
    if kpis.get("delay_rate"): insights.append(("g" if kpis["delay_rate"]<15 else "w",f"⚠️ **Delay Rate:** {kpis['delay_rate']:.1f}% {'— Under control' if kpis['delay_rate']<15 else '— High! Route planning improve karo'}"))
    if kpis.get("avg_transit_days"): insights.append(("i",f"📅 **Avg Transit:** {kpis['avg_transit_days']} days | Max: {kpis.get('max_transit_days','N/A')} days"))
    if kpis.get("avg_cost_per_km"): insights.append(("i",f"🛣️ **Avg Cost/KM:** ₹{kpis['avg_cost_per_km']}"))
    if kpis.get("fuel_pct"): insights.append(("w" if kpis["fuel_pct"]>35 else "g",f"⛽ **Fuel = {kpis['fuel_pct']:.1f}% of Revenue** {'— High, route optimize karo' if kpis['fuel_pct']>35 else '— Good ratio'}"))
    if origin_col and dest_col:
        top_route=df["_route"].value_counts().idxmax()
        insights.append(("i",f"🗺️ **Busiest Route:** {top_route}"))
    return kpis,charts,insights


def process_education(df):
    kpis={}; charts={}; insights=[]

    att_col  = next((c for c in df.columns if 'attendance' in c.lower()),None)
    cgpa_col = next((c for c in df.columns if 'cgpa' in c.lower() or 'marks' in c.lower() or 'score' in c.lower()),None)
    fee_col  = next((c for c in df.columns if 'fee' in c.lower() or 'fees_paid' in c.lower()),None)
    dept_col = next((c for c in df.columns if 'department' in c.lower() or 'dept' in c.lower() or 'branch' in c.lower()),None)
    place_col= next((c for c in df.columns if 'placement' in c.lower()),None)
    company_col=next((c for c in df.columns if 'company' in c.lower()),None)
    pkg_col  = next((c for c in df.columns if 'package' in c.lower() or 'lpa' in c.lower()),None)
    gender_col=next((c for c in df.columns if 'gender' in c.lower()),None)
    city_col = next((c for c in df.columns if 'city' in c.lower()),None)
    scholar_col=next((c for c in df.columns if 'scholar' in c.lower()),None)
    hostel_col=next((c for c in df.columns if 'hostel' in c.lower()),None)
    intern_col=next((c for c in df.columns if 'intern' in c.lower()),None)
    backlog_col=next((c for c in df.columns if 'backlog' in c.lower()),None)
    year_col = next((c for c in df.columns if c.lower()=='year'),None)

    kpis["total_students"]=len(df)

    if att_col:
        kpis["avg_attendance"]=round(df[att_col].mean(),1)
        kpis["low_attendance_count"]=int((df[att_col]<75).sum())
        kpis["low_attendance_pct"]=round((df[att_col]<75).mean()*100,1)
        d=pd.DataFrame({"Category":["≥75% Regular","<75% Low"],"Students":[int((df[att_col]>=75).sum()),int((df[att_col]<75).sum())]})
        charts["attendance_split"]={"t":"pie","data":d.to_dict("records"),"n":"Category","v":"Students","title":"Attendance Split"}

    if cgpa_col:
        kpis["avg_cgpa"]=round(df[cgpa_col].mean(),2)
        kpis["top_cgpa"]=round(df[cgpa_col].max(),2)

    if fee_col:
        kpis["total_fees"]=round(df[fee_col].sum(),0)
        kpis["avg_fee"]=round(df[fee_col].mean(),0)

    if place_col:
        placed=(df[place_col].str.lower().isin(["placed","yes","1","true"]))
        kpis["placement_rate"]=round(placed.mean()*100,1)
        kpis["placed_count"]=int(placed.sum())
        d=df[place_col].value_counts().reset_index()
        d.columns=["Status","Students"]
        charts["placement_status"]={"t":"pie","data":d.to_dict("records"),"n":"Status","v":"Students","title":"Placement Status"}

    if pkg_col:
        placed_pkg=df[df[pkg_col]>0][pkg_col]
        if len(placed_pkg)>0: kpis["avg_package_lpa"]=round(placed_pkg.mean(),2)

    if scholar_col:
        kpis["scholarship_pct"]=round((df[scholar_col].str.lower()=="yes").mean()*100,1)

    if hostel_col:
        kpis["hostel_pct"]=round((df[hostel_col].str.lower()=="yes").mean()*100,1)

    if intern_col:
        kpis["internship_pct"]=round((df[intern_col].str.lower()=="yes").mean()*100,1)

    if backlog_col:
        kpis["students_with_backlogs"]=int((df[backlog_col]>0).sum())
        kpis["backlog_pct"]=round((df[backlog_col]>0).mean()*100,1)

    # Dept charts
    if dept_col:
        d=df[dept_col].value_counts().reset_index()
        d.columns=["Department","Students"]
        charts["dept_enrollment"]={"t":"bar","data":d.to_dict("records"),"x":"Students","y":"Department","title":"Students by Department"}
        if cgpa_col:
            dc=df.groupby(dept_col)[cgpa_col].mean().sort_values(ascending=False).reset_index()
            dc.columns=["Department","Avg_CGPA"]
            charts["dept_cgpa"]={"t":"bar","data":dc.to_dict("records"),"x":"Avg_CGPA","y":"Department","title":"Avg CGPA by Department"}
        if place_col:
            dp=df.groupby(dept_col)[place_col].apply(lambda x:(x.str.lower()=="placed").mean()*100).sort_values(ascending=False).reset_index()
            dp.columns=["Department","Placement_Rate"]
            charts["dept_placement"]={"t":"bar","data":dp.to_dict("records"),"x":"Placement_Rate","y":"Department","title":"Placement % by Department"}

    # Company
    if company_col:
        cv=df[company_col].dropna().value_counts().head(8).reset_index()
        cv.columns=["Company","Placements"]
        charts["top_companies"]={"t":"bar","data":cv.to_dict("records"),"x":"Placements","y":"Company","title":"Top Recruiting Companies"}

    # Gender
    if gender_col:
        d=df[gender_col].value_counts().reset_index()
        d.columns=["Gender","Students"]
        charts["gender"]={"t":"pie","data":d.to_dict("records"),"n":"Gender","v":"Students","title":"Gender Split"}

    # City
    if city_col:
        d=df[city_col].value_counts().head(8).reset_index()
        d.columns=["City","Students"]
        charts["city"]={"t":"bar","data":d.to_dict("records"),"x":"Students","y":"City","title":"Students by City"}

    # Year wise
    if year_col:
        d=df[year_col].value_counts().reset_index()
        d.columns=["Year","Students"]
        charts["year_dist"]={"t":"pie","data":d.to_dict("records"),"n":"Year","v":"Students","title":"Year-wise Students"}

    # Insights
    insights.append(("i",f"🎓 **Total Students:** {kpis['total_students']:,}"))
    if att_col:
        t="w" if kpis["low_attendance_pct"]>30 else "g"
        insights.append((t,f"📅 **Avg Attendance:** {kpis['avg_attendance']:.1f}% | {kpis['low_attendance_count']} students below 75% ({kpis['low_attendance_pct']:.1f}%) {'— Bahut zyada! Counseling karo' if kpis['low_attendance_pct']>30 else '— Good'}"))
    if cgpa_col:
        insights.append(("i",f"📊 **Avg CGPA:** {kpis['avg_cgpa']:.2f} | Top: {kpis['top_cgpa']:.2f}"))
    if fee_col:
        insights.append(("i",f"💰 **Total Fees Collected:** ₹{kpis['total_fees']/1e7:.2f}Cr | Avg: ₹{kpis['avg_fee']:,.0f}/student"))
    if place_col:
        t="w" if kpis["placement_rate"]<50 else "g"
        insights.append((t,f"🏢 **Placement Rate:** {kpis['placement_rate']:.1f}% ({kpis['placed_count']} students placed) {'— Low! Industry tie-ups badhao' if kpis['placement_rate']<50 else '— Good!'}"))
    if pkg_col and kpis.get("avg_package_lpa"):
        insights.append(("i",f"💼 **Avg Package:** ₹{kpis['avg_package_lpa']:.2f} LPA"))
    if backlog_col:
        t="w" if kpis["backlog_pct"]>40 else "i"
        insights.append((t,f"⚠️ **Students with Backlogs:** {kpis['students_with_backlogs']} ({kpis['backlog_pct']:.1f}%) {'— High! Extra classes aur mentoring karo' if kpis['backlog_pct']>40 else ''}"))
    if scholar_col:
        insights.append(("i",f"🏅 **Scholarship Students:** {kpis['scholarship_pct']:.1f}%"))
    if intern_col:
        t="w" if kpis["internship_pct"]<50 else "g"
        insights.append((t,f"💻 **Internship Rate:** {kpis['internship_pct']:.1f}% {'— Low! More internship drives karo' if kpis['internship_pct']<50 else '— Good!'}"))

    return kpis,charts,insights

def process_generic(df):
    kpis={}; charts={}; insights=[]
    num_cols=[c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols=[c for c in df.columns if df[c].dtype==object and df[c].nunique()<=50]
    date_cols=[c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    kpis["total_records"]=len(df)
    for col in num_cols[:4]:
        kpis[f"{col}_total"]=round(df[col].sum(),2)
        kpis[f"{col}_avg"]=round(df[col].mean(),2)
    for col in cat_cols[:4]:
        vc=df[col].value_counts()
        d=vc.reset_index(); d.columns=[col,"Count"]
        if len(vc)<=8: charts[f"pie_{col}"]={"t":"pie","data":d.to_dict("records"),"n":col,"v":"Count","title":f"{col} Distribution"}
        else: charts[f"bar_{col}"]={"t":"bar","data":d.head(10).to_dict("records"),"x":"Count","y":col,"title":f"Top {col}"}
    for dc in date_cols[:1]:
        df["_month"]=df[dc].dt.to_period("M").astype(str)
        d=df.groupby("_month").size().reset_index(name="Count")
        d.columns=["Month","Count"]
        charts["monthly"]={"t":"line","data":d.to_dict("records"),"x":"Month","y":"Count","title":"Monthly Trend"}
    insights.append(("i",f"📊 **{len(df):,} records** analyze kiye gaye."))
    for col in num_cols[:3]:
        insights.append(("i",f"💰 **{col}:** Total={df[col].sum():,.1f} | Avg={df[col].mean():,.1f}"))
    return kpis,charts,insights

def clean_df(df):
    fixes=[]
    df.columns=[str(c).strip() for c in df.columns]
    b=len(df); df.drop_duplicates(inplace=True)
    if len(df)<b: fixes.append(f"✅ {b-len(df)} duplicates remove kiye")
    df.dropna(how="all",inplace=True)
    for col in df.columns:
        if df[col].dtype==object:
            try:
                p=pd.to_datetime(df[col],infer_datetime_format=True,errors="coerce")
                if p.notna().mean()>0.8: df[col]=p; fixes.append(f"✅ '{col}' → datetime")
            except: pass
    miss=df.isnull().mean()
    for col in df.columns:
        if miss[col]==0: continue
        if pd.api.types.is_numeric_dtype(df[col]): df[col]=df[col].fillna(df[col].median())
        else:
            md=df[col].mode(); df[col]=df[col].fillna(md[0] if len(md) else "Unknown")
    score=max(0,min(100,round(100-(df.shape[0]-len(df))/max(df.shape[0],1)*20,1)))
    return df.reset_index(drop=True),{"fixes":fixes,"score":score}

def make_chart(cd,df):
    DARK=dict(plot_bgcolor="#161B22",paper_bgcolor="#161B22",font=dict(color="#8B949E",family="Inter"),margin=dict(l=10,r=10,t=40,b=10),height=300,title=dict(font=dict(color="#E6EDF3",size=13)),xaxis=dict(gridcolor="#21262D"),yaxis=dict(gridcolor="#21262D"))
    t=cd.get("t","")
    try:
        if t=="line":
            d=pd.DataFrame(cd["data"])
            fig=go.Figure(go.Scatter(x=d[cd["x"]],y=d[cd["y"]],fill="tozeroy",fillcolor="rgba(88,166,255,0.08)",line=dict(color="#58A6FF",width=2.5),mode="lines+markers",marker=dict(size=6,color="#58A6FF")))
            fig.update_layout(**DARK,title=cd.get("title",""))
            return fig
        elif t=="pie":
            d=pd.DataFrame(cd["data"])
            fig=px.pie(d,names=cd["n"],values=cd["v"],hole=0.5,color_discrete_sequence=PALETTE)
            fig.update_traces(textposition="outside",textinfo="percent+label",textfont=dict(color="#8B949E",size=11))
            fig.update_layout(**DARK,title=cd.get("title",""),showlegend=False)
            return fig
        elif t=="bar":
            d=pd.DataFrame(cd["data"])
            fig=px.bar(d,x=cd["x"],y=cd["y"],orientation="h",color_discrete_sequence=["#58A6FF"],title=cd.get("title",""))
            fig.update_traces(marker_line_width=0)
            fig.update_layout(**DARK)
            fig.update_layout(yaxis=dict(categoryorder="total ascending",gridcolor="#21262D"),xaxis=dict(gridcolor="#21262D"))
            return fig
    except: pass
    return None

# ══════════════════════════
# SESSION
# ══════════════════════════
def pg_login():
    st.markdown("""<style>[data-testid="stAppViewContainer"]{background:radial-gradient(ellipse at top,#0D1F3C 0%,#0A0E1A 60%);}[data-testid="stHeader"]{background:transparent;}</style>""",unsafe_allow_html=True)
    _,col,_=st.columns([1,1.2,1])
    with col:
        st.markdown('<div style="text-align:center;padding:3rem 0 2rem;"><div style="font-size:3.5rem;">📊</div><div style="font-size:2.2rem;font-weight:800;color:#E6EDF3;margin-top:0.5rem;">InsightFlow AI</div><div style="color:#8B949E;font-size:0.9rem;">Lucknow Ki Data Analytics Agency</div></div>',unsafe_allow_html=True)
        st.markdown('<div style="background:#161B22;border:1px solid #30363D;border-radius:16px;padding:2rem;box-shadow:0 16px 48px rgba(0,0,0,0.4);">',unsafe_allow_html=True)
        st.markdown('<p style="color:#E6EDF3;font-weight:600;margin-bottom:1rem;">🔐 Login Karo</p>',unsafe_allow_html=True)
        un=st.text_input("Username",placeholder="username daalo",label_visibility="collapsed")
        pw=st.text_input("Password",type="password",placeholder="password daalo",label_visibility="collapsed")
        if st.button("Login →",use_container_width=True,type="primary"):
            if not un or not pw: st.error("Dono fields bharo")
            else:
                r=do_login(un,pw)
                if r["ok"]: ss(r); st.session_state["page"]="upload"; st.rerun()
                else: st.error(r["msg"])
        st.markdown("</div>",unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#6E7681;font-size:0.75rem;margin-top:1rem;">Default: <b style="color:#8B949E">admin</b> / <b style="color:#8B949E">admin@123</b></p>',unsafe_allow_html=True)

def sidebar():
    u=gu(); rc="#F85149" if ia() else "#58A6FF"
    with st.sidebar:
        client_div = f"<div style='font-size:0.75rem;color:#6E7681;margin-top:4px;'>{str(u.get('cn') or '')}</div>" if u.get("cn") else ""
        st.markdown(f'<div style="padding:1rem;background:#0D1117;border-radius:10px;margin-bottom:1rem;border:1px solid #21262D;"><div style="font-size:0.65rem;color:#6E7681;font-weight:600;letter-spacing:1px;">LOGGED IN</div><div style="font-size:0.95rem;font-weight:700;color:#E6EDF3;margin-top:4px;">{u["name"]}</div><span style="font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:6px;background:{rc}22;color:{rc};">{u["role"].upper()}</span>{client_div}</div>',unsafe_allow_html=True)
        pages={"upload":"📁  Upload & Analyze","clients":"👥  Clients","users":"🔐  Users","festival":"🎉  Festivals"} if ia() else {"dashboard":"📈  Dashboard"}
        if ic() and st.session_state.get("df") is None: pages={"upload":"📁  Upload Data",**pages}
        for pk,pl in pages.items():
            t="primary" if st.session_state.get("page")==pk else "secondary"
            if st.button(pl,key=f"n_{pk}",use_container_width=True,type=t): st.session_state["page"]=pk; st.rerun()
        if ia():
            st.markdown('<hr style="border-color:#21262D;margin:1rem 0;">',unsafe_allow_html=True)
            cls=get_clients()
            if cls:
                ops={"— Client Select —":None}; ops.update({c["name"]:c for c in cls})
                sel=st.selectbox("",list(ops.keys()),label_visibility="collapsed")
                if ops[sel]: st.session_state["ac"]=ops[sel]
        if st.session_state.get("df") is not None:
            ind=st.session_state.get("industry_type","")
            ind_icons={"hospital":"🏥","ecommerce":"🛒","logistics":"🚚","education":"🎓","generic":"📊"}
            st.markdown(f'<div style="background:#0D2818;border:1px solid #1A4731;border-radius:8px;padding:0.8rem;margin-top:0.5rem;"><div style="font-size:0.65rem;font-weight:600;color:#3FB950;">{ind_icons.get(ind,"📊")} DATA LOADED</div><div style="font-size:0.78rem;color:#6E7681;margin-top:3px;">{st.session_state["df"].shape[0]:,} rows · {ind.upper()}</div></div>',unsafe_allow_html=True)
        st.markdown('<hr style="border-color:#21262D;margin:1rem 0;">',unsafe_allow_html=True)
        if st.button("🚪  Logout",use_container_width=True): lo(); st.rerun()

def pg_upload():
    ac=st.session_state.get("ac",{}) or {}
    cn=ac.get("name","") or (gu().get("cn") or "")
    st.markdown(f'<div class="hero"><div class="badge">📍 Lucknow · InsightFlow AI</div><h1>📊 Data Upload & Analyze</h1><p>Koi bhi data upload karo — Hospital, Ecommerce, Logistics, ya kuch bhi!{f" · {cn}" if cn else ""}</p></div>',unsafe_allow_html=True)
    c1,c2=st.columns([3,2])
    with c1:
        st.markdown('<div class="sec">📁 FILE UPLOAD</div>',unsafe_allow_html=True)
        up=st.file_uploader("",type=["csv","xlsx","xls"],label_visibility="collapsed")
        use_ai=st.checkbox("🤖 Claude AI Insights",value=False)
        ak=""
        if use_ai: ak=st.text_input("API Key",type="password",placeholder="sk-ant-...",label_visibility="collapsed")
        if up:
            with st.spinner("🔄 Analyze ho raha hai..."):
                try:
                    df_raw=pd.read_csv(up,on_bad_lines="skip") if up.name.endswith(".csv") else pd.read_excel(up)
                except: st.error("File read error!"); st.stop()
                df,cr=clean_df(df_raw.copy())
                ind=detect_industry(df)
                if ind=="hospital": kpis,charts,insights=process_hospital(df)
                elif ind=="ecommerce": kpis,charts,insights=process_ecommerce(df)
                elif ind=="logistics": kpis,charts,insights=process_logistics(df)
                elif ind=="education": kpis,charts,insights=process_education(df)
                else: kpis,charts,insights=process_generic(df)
                st.session_state.update({"df":df,"metrics":kpis,"charts":charts,"insights":insights,"industry_type":ind,"cr":cr})
                if use_ai and ak:
                    with st.spinner("🤖 Claude analyze kar raha hai..."):
                        try:
                            import anthropic
                            kpi_txt="\n".join([f"  {k}: {v}" for k,v in kpis.items()])
                            pr=f"You are InsightFlow AI analyst for a {ind} business in Lucknow, India.\nKey Metrics:\n{kpi_txt}\nDataset: {df.shape[0]} rows, columns: {', '.join(df.columns.tolist())}\nGive 5 specific actionable business insights. Use Indian context (Rs, lakh, crore). Use emojis."
                            ac2=anthropic.Anthropic(api_key=ak)
                            msg=ac2.messages.create(model="claude-sonnet-4-20250514",max_tokens=600,messages=[{"role":"user","content":pr}])
                            st.session_state["ai"]=msg.content[0].text
                        except Exception as e: st.session_state["ai"]=f"Error: {e}"
            ind_labels={"hospital":"🏥 Hospital","ecommerce":"🛒 E-Commerce","logistics":"🚚 Logistics","education":"🎓 Education","generic":"📊 Generic"}
            st.success(f"✅ **{ind_labels.get(ind,ind)}** data detect hua! {df.shape[0]:,} rows processed.")
            for f in cr["fixes"][:4]: st.info(f,icon=None)
            if st.button("📈 Dashboard Dekho →",type="primary",use_container_width=True):
                st.session_state["page"]="dashboard"; st.rerun()
    with c2:
        st.markdown('<div class="sec">🏭 SUPPORTED INDUSTRIES</div>',unsafe_allow_html=True)
        for icon,name,color,hint in [("🏥","Hospital","#F85149","Patient, doctor, treatment_cost, disease"),("🛒","E-Commerce","#D29922","Product_Price, Quantity, Discount, Category"),("🚚","Logistics","#3FB950","Shipment_Cost, Distance_KM, Vehicle_Type"),("🎓","Education","#58A6FF","Student, marks, attendance, fee"),("📦","Any Data","#BC8CFF","Koi bhi CSV/Excel — AI samjhega!")]:
            st.markdown(f'<div style="background:#161B22;border:1px solid #21262D;border-left:3px solid {color};border-radius:8px;padding:0.7rem 1rem;margin:0.3rem 0;"><b style="color:#E6EDF3;">{icon} {name}</b><div style="font-size:0.72rem;color:#6E7681;margin-top:2px;">{hint}</div></div>',unsafe_allow_html=True)

def pg_dashboard():
    if st.session_state.get("df") is None:
        st.markdown('<div style="text-align:center;padding:4rem;"><div style="font-size:3rem;">📂</div><div style="color:#E6EDF3;font-size:1.1rem;margin-top:1rem;">Koi data nahi mila</div><div style="color:#6E7681;">Pehle data upload karo</div></div>',unsafe_allow_html=True)
        if st.button("→ Upload",type="primary"): st.session_state["page"]="upload"; st.rerun()
        return
    df=st.session_state["df"]; kpis=st.session_state["metrics"]
    charts=st.session_state["charts"]; insights=st.session_state["insights"]
    ind=st.session_state.get("industry_type","generic")
    ac=st.session_state.get("ac",{}) or {}; cn=ac.get("name","") or (gu().get("cn") or "Client")
    ind_labels={"hospital":"🏥 Hospital Analytics","ecommerce":"🛒 E-Commerce Analytics","logistics":"🚚 Logistics Analytics","education":"🎓 Education Analytics","generic":"📊 Analytics"}
    st.markdown(f'<div class="hero"><div class="badge">📊 Live Dashboard</div><h1>{ind_labels.get(ind,"📊 Analytics")}</h1><p>{cn} · {df.shape[0]:,} records</p></div>',unsafe_allow_html=True)

    # KPI Cards
    kpi_items=[(k,v) for k,v in kpis.items() if v is not None and not isinstance(v,str)][:6]
    if kpi_items:
        cols_kpi=st.columns(min(len(kpi_items),3))
        colors_kpi=["#58A6FF","#3FB950","#D29922","#F85149","#BC8CFF","#F78166"]
        for i,(k,v) in enumerate(kpi_items):
            label=k.replace("_"," ").title()
            if "revenue" in k or "cost" in k or "fuel" in k:
                if v>=1e7: fmt=f"₹{v/1e7:.2f}Cr"
                elif v>=1e5: fmt=f"₹{v/1e5:.1f}L"
                else: fmt=f"₹{v:,.0f}"
            elif "rate" in k or "pct" in k or "discount" in k: fmt=f"{v:.1f}%"
            elif "days" in k or "age" in k: fmt=f"{v:.1f}"
            elif isinstance(v,float): fmt=f"{v:,.1f}"
            else: fmt=f"{int(v):,}"
            with cols_kpi[i%3]:
                st.markdown(f'<div class="kpi" style="--accent:{colors_kpi[i]};"><div class="kpi-l">{label}</div><div class="kpi-v">{fmt}</div></div>',unsafe_allow_html=True)
        st.markdown("")

    # Tabs
    t1,t2,t3,t4=st.tabs(["📈 Trends","📊 Charts","💡 Insights","📋 Raw Data"])

    with t1:
        tc={k:v for k,v in charts.items() if v.get("t")=="line"}
        if not tc: st.markdown('<div style="text-align:center;padding:3rem;color:#6E7681;"><div style="font-size:2rem;">📅</div><div>Date column nahi mila</div></div>',unsafe_allow_html=True)
        else:
            it=list(tc.items())
            for i in range(0,len(it),2):
                cc=st.columns(2)
                for j,(k,cd) in enumerate(it[i:i+2]):
                    with cc[j]:
                        fig=make_chart(cd,df)
                        if fig: st.plotly_chart(fig,use_container_width=True)

    with t2:
        non_line={k:v for k,v in charts.items() if v.get("t") in ("pie","bar")}
        if non_line:
            it=list(non_line.items())
            for i in range(0,min(len(it),8),2):
                cc=st.columns(2)
                for j,(k,cd) in enumerate(it[i:i+2]):
                    with cc[j]:
                        fig=make_chart(cd,df)
                        if fig: st.plotly_chart(fig,use_container_width=True)

    with t3:
        st.markdown('<div class="sec">AUTO-GENERATED INSIGHTS</div>',unsafe_allow_html=True)
        cm={"g":"ig","w":"iw","d":"id","i":"ii"}
        for tp,txt in insights:
            st.markdown(f'<div class="ins {cm.get(tp,"ii")}">{txt}</div>',unsafe_allow_html=True)
        if ai:=st.session_state.get("ai"):
            st.markdown('<div class="sec" style="margin-top:1.5rem;">🤖 CLAUDE AI ANALYSIS</div>',unsafe_allow_html=True)
            st.markdown(f'<div class="ins ii">{ai.replace(chr(10),"<br>")}</div>',unsafe_allow_html=True)

    with t4:
        st.dataframe(df.head(500),use_container_width=True)
        c1,c2=st.columns(2)
        with c1: st.download_button("⬇️ CSV",df.to_csv(index=False).encode(),"data.csv","text/csv",use_container_width=True)
        with c2:
            try:
                buf=io.BytesIO()
                with pd.ExcelWriter(buf,engine="xlsxwriter") as w: df.to_excel(w,index=False)
                st.download_button("⬇️ Excel",buf.getvalue(),"report.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
            except: pass

def pg_clients():
    st.markdown('<div class="hero"><h1>👥 Clients</h1><p>Lucknow ke clients manage karo</p></div>',unsafe_allow_html=True)
    with st.expander("➕ Naya Client"):
        with st.form("ac"):
            c1,c2=st.columns(2)
            with c1: nm=st.text_input("Name *"); ind=st.selectbox("Industry",["hospital","ecommerce","logistics","education","other"])
            with c2: em=st.text_input("Email"); city=st.selectbox("Area",["Hazratganj","Gomtinagar","Alambagh","Chowk","Aliganj","Indira Nagar","Other"])
            if st.form_submit_button("✅ Add",use_container_width=True) and nm: add_client(nm,ind,em,city); st.success(f"✅ '{nm}' added!"); st.rerun()
    icons={"hospital":"🏥","ecommerce":"🛒","logistics":"🚚","education":"🎓","other":"📊"}
    for c in get_clients():
        col1,col2,col3=st.columns([4,3,1])
        with col1: st.markdown(f'<div style="color:#E6EDF3;font-weight:600;">{icons.get(c["industry"],"📊")} {c["name"]}</div><div style="font-size:0.78rem;color:#6E7681;">📍{c.get("city","Lucknow")} · {c["industry"]}</div>',unsafe_allow_html=True)
        with col2: st.caption(c.get("email") or "—")
        with col3:
            if st.button("Load",key=f"l_{c['id']}",use_container_width=True): st.session_state["ac"]=c; st.session_state["page"]="upload"; st.rerun()
        st.markdown('<hr style="border-color:#21262D;margin:0.4rem 0;">',unsafe_allow_html=True)

def pg_users():
    st.markdown('<div class="hero"><h1>🔐 Users</h1><p>Users banao aur manage karo</p></div>',unsafe_allow_html=True)
    cls=get_clients()
    with st.expander("➕ Naya User"):
        with st.form("au"):
            c1,c2=st.columns(2)
            with c1: un=st.text_input("Username *"); pw=st.text_input("Password *",type="password"); fn=st.text_input("Full Name")
            with c2:
                role=st.selectbox("Role",["client","admin"]); em=st.text_input("Email"); cid=None
                if role=="client" and cls:
                    ops={f"{c['name']}":c["id"] for c in cls}; sel=st.selectbox("Client",list(ops.keys())); cid=ops[sel]
            if st.form_submit_button("✅ Create",use_container_width=True):
                r=create_user(un,pw,role,cid,fn,em)
                if r["ok"]: st.success(r["msg"]); st.rerun()
                else: st.error(r["msg"])
    rc2={"admin":"#F85149","client":"#58A6FF"}
    for u in get_users():
        c1,c2,c3,c4,c5=st.columns([3,2,2,1,1])
        with c1: st.markdown(f'<div style="color:#E6EDF3;font-weight:600;">@{u["username"]} <span style="font-size:0.65rem;padding:2px 7px;border-radius:6px;background:{rc2.get(u["role"],"#888")}22;color:{rc2.get(u["role"],"#888")};">{u["role"].upper()}</span></div><div style="font-size:0.78rem;color:#6E7681;">{u.get("full_name") or "—"}</div>',unsafe_allow_html=True)
        with c2: st.caption(u.get("cn") or "Admin")
        with c3: st.caption(f"{'🟢' if u['is_active'] else '🔴'} {str(u.get('last_login') or 'Never')[:10]}")
        with c4:
            with st.popover("🔑"):
                np2=st.text_input("New pw",type="password",key=f"np_{u['id']}")
                if st.button("Update",key=f"up_{u['id']}"): st.success("✅") if upw(u["id"],np2) else st.error("Min 6")
        with c5:
            if u["role"]!="admin":
                if st.button("⏸" if u["is_active"] else "▶",key=f"t_{u['id']}"): tog(u["id"]); st.rerun()
        st.markdown('<hr style="border-color:#21262D;margin:0.3rem 0;">',unsafe_allow_html=True)

def pg_festival():
    st.markdown('<div class="hero"><h1>🎉 Festival Calendar — Lucknow 2026</h1><p>Festivals ke hisaab se business plan karo</p></div>',unsafe_allow_html=True)
    FEST={"January":["🪁 Makar Sankranti","🇮🇳 Republic Day"],"February":["🌸 Basant Panchami"],"March":["🎨 Holi","🌙 Eid ul-Fitr"],"April":["🪔 Ram Navami"],"August":["🇮🇳 Independence Day","🪢 Raksha Bandhan","🎪 Janmashtami"],"October":["🌺 Navratri","🏹 Dussehra","🪔 Diwali"],"November":["🪔 Diwali","🌊 Chhath Puja","🎭 Lucknow Mahotsav"],"December":["🎄 Christmas"]}
    months=["January","February","March","April","May","June","July","August","September","October","November","December"]
    cs=st.columns(3)
    for i,mo in enumerate(months):
        fs=FEST.get(mo,[])
        with cs[i%3]:
            col2="#D29922" if fs else "#21262D"
            st.markdown(f'<div style="background:#161B22;border:1px solid {col2};border-radius:10px;padding:1rem;margin:0.3rem 0;"><div style="font-weight:700;color:#E6EDF3;">{mo}</div>{"".join([f"<div style=font-size:0.8rem;color:#8B949E;margin-top:4px;>{f}</div>" for f in fs]) if fs else "<div style=font-size:0.8rem;color:#6E7681;>—</div>"}</div>',unsafe_allow_html=True)
    st.markdown('<div class="sec">💡 BUSINESS TIPS</div>',unsafe_allow_html=True)
    for ev,tip,color in [("🪔 Diwali","Gift hampers, electronics — 30-50% sales boost. Stock 2 months pehle.","#D29922"),("🌙 Eid","Clothing, sweets — Chowk mein 40%+ spike.","#58A6FF"),("🌺 Navratri","Organic products, puja items — 9 din celebration.","#3FB950"),("📚 Back to School (Jun-Jul)","Stationery, uniforms — coaching institutes full.","#BC8CFF")]:
        st.markdown(f'<div class="ins ii" style="border-color:{color}44;"><b style="color:{color};">{ev}</b><br><span style="color:#8B949E;">{tip}</span></div>',unsafe_allow_html=True)

# ══════════════════════════
# MAIN
# ══════════════════════════
init_db()
for k,v in {"page":"login","df":None,"ac":None,"ai":None,"industry_type":None}.items():
    if k not in st.session_state: st.session_state[k]=v

if not li(): pg_login(); st.stop()

sidebar()
p=st.session_state.get("page","upload")
if ic() and p in ("clients","users","festival"): p="dashboard"; st.session_state["page"]=p
if p=="upload": pg_upload()
elif p=="dashboard": pg_dashboard()
elif p=="clients": pg_clients()
elif p=="users": pg_users()
elif p=="festival": pg_festival()
else: pg_upload()
