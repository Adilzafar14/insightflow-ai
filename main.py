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
[data-testid="stSidebar"] .stButton button{
    background:#161B22 !important;border:1px solid #30363D !important;
    color:#E6EDF3 !important;border-radius:8px !important;
    font-weight:500 !important;transition:all 0.2s !important;
}
[data-testid="stSidebar"] .stButton button:hover{background:#21262D !important;border-color:#58A6FF !important;}
[data-testid="stSidebar"] .stButton button[kind="primary"]{
    background:linear-gradient(135deg,#1A6ED8,#2D6A9F) !important;
    border-color:#1A6ED8 !important;color:white !important;
}
div[data-testid="stMetric"]{
    background:#161B22;border:1px solid #21262D;
    border-radius:10px;padding:1rem;
}
div[data-testid="stMetric"] label{color:#8B949E !important;}
div[data-testid="stMetric"] div{color:#E6EDF3 !important;}
.stTabs [data-baseweb="tab-list"]{background:#161B22;border-radius:10px;padding:4px;}
.stTabs [data-baseweb="tab"]{color:#8B949E !important;border-radius:6px !important;}
.stTabs [aria-selected="true"]{background:#21262D !important;color:#E6EDF3 !important;}
.stDataFrame{background:#161B22 !important;}
[data-testid="stFileUploader"]{background:#161B22;border:1px dashed #30363D;border-radius:10px;padding:1rem;}

.hero{
    background:linear-gradient(135deg,#0D1117 0%,#161B22 50%,#0D1F3C 100%);
    border:1px solid #21262D;border-radius:16px;
    padding:2rem 2.5rem;margin-bottom:1.5rem;
    position:relative;overflow:hidden;
}
.hero::before{
    content:'';position:absolute;top:0;right:0;
    width:300px;height:100%;
    background:linear-gradient(135deg,transparent,#1A6ED822);
}
.hero h1{font-size:1.8rem;font-weight:800;color:#E6EDF3;margin:0;}
.hero p{color:#8B949E;margin:0.4rem 0 0;font-size:0.9rem;}
.hero .badge{
    display:inline-block;background:#1A6ED822;color:#58A6FF;
    border:1px solid #1A6ED844;border-radius:20px;
    padding:3px 12px;font-size:0.75rem;font-weight:600;margin-top:0.7rem;
}

.kpi{
    background:#161B22;border:1px solid #21262D;
    border-radius:12px;padding:1.2rem 1.4rem;
    transition:all 0.2s;position:relative;overflow:hidden;
}
.kpi::before{
    content:'';position:absolute;top:0;left:0;
    width:3px;height:100%;background:var(--accent,#58A6FF);
}
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

.login-wrap{
    max-width:400px;margin:0 auto;padding-top:3rem;
}
.login-card{
    background:#161B22;border:1px solid #30363D;
    border-radius:16px;padding:2rem;
    box-shadow:0 16px 48px rgba(0,0,0,0.4);
}
</style>
""",unsafe_allow_html=True)

DB="insightflow.db"
PALETTE=["#58A6FF","#3FB950","#D29922","#F85149","#BC8CFF","#F78166","#56D364","#79C0FF"]

# ══════════════════════════
# DATABASE
# ══════════════════════════
def get_db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    c=get_db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS clients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,industry TEXT,
        email TEXT DEFAULT '',city TEXT DEFAULT 'Lucknow',
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT(datetime('now')));
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,salt TEXT NOT NULL,
        role TEXT DEFAULT 'client',client_id INTEGER,
        full_name TEXT DEFAULT '',email TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,last_login TEXT,
        created_at TEXT DEFAULT(datetime('now')));
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
    h,s=_hp(npw); c=get_db()
    c.execute("UPDATE users SET password_hash=?,salt=? WHERE id=?",(h,s,uid)); c.commit(); c.close(); return True

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
    for k in ["df","cols","metrics","charts","insights","page","ac"]:
        st.session_state.pop(k,None)

# ══════════════════════════
# DATA PIPELINE
# ══════════════════════════
def clean_df(df):
    fixes,warns=[],[]
    orig=df.shape
    df.columns=[str(c).strip().lower().replace(" ","_").replace("-","_").replace(".","_").replace("/","_").replace("(","").replace(")","").replace("%","pct") for c in df.columns]
    fixes.append("✅ Column names normalize kiye")
    b=len(df); df.drop_duplicates(inplace=True)
    if len(df)<b: fixes.append(f"✅ {b-len(df)} duplicates remove kiye")
    df.dropna(how="all",inplace=True)
    for col in df.columns:
        if df[col].dtype==object:
            cl2=df[col].astype(str).str.replace(",","",regex=False).str.replace("₹","",regex=False).str.replace("$","",regex=False).str.strip()
            n=pd.to_numeric(cl2,errors="coerce")
            if n.notna().mean()>0.7: df[col]=n; fixes.append(f"✅ '{col}' → numeric"); continue
        if df[col].dtype==object:
            try:
                p=pd.to_datetime(df[col],infer_datetime_format=True,errors="coerce")
                if p.notna().mean()>0.7: df[col]=p; fixes.append(f"✅ '{col}' → datetime")
            except: pass
    for col in df.columns:
        m=df[col].isnull().mean()
        if m==0: continue
        if m>0.4: warns.append(f"⚠️ '{col}' mein {m*100:.0f}% missing values hain")
        if pd.api.types.is_numeric_dtype(df[col]): df[col]=df[col].fillna(df[col].median())
        else:
            md=df[col].mode(); df[col]=df[col].fillna(md[0] if len(md) else "Unknown")
    sc=max(0,min(100,round(100-len(warns)*8-(orig[0]-len(df))/max(orig[0],1)*20,1)))
    return df.reset_index(drop=True),{"fixes":fixes,"warns":warns,"score":sc,"orig":orig,"final":df.shape}

def classify_df(df):
    num,cat,dt,ids=[],[],[],[]
    for col in df.columns:
        if any(k in col for k in ["_id","id_","serial","patient_id","order_id","shipment_id","student_id"]) and df[col].nunique()>len(df)*0.7:
            ids.append(col); continue
        if pd.api.types.is_datetime64_any_dtype(df[col]): dt.append(col); continue
        if pd.api.types.is_numeric_dtype(df[col]): num.append(col); continue
        if df[col].nunique()<=min(50,len(df)*0.3): cat.append(col)
        else: ids.append(col)
    return{"num":num,"cat":cat,"dt":dt,"ids":ids}

def compute_metrics(df,cols):
    m={}; ch={}
    m["total_records"]=len(df)
    m["total_columns"]=len(df.columns)

    # Numeric stats
    for col in cols["num"]:
        l=col.replace("_"," ").title()
        tot=float(df[col].sum())
        avg=float(df[col].mean())
        mx=float(df[col].max())
        mn=float(df[col].min())
        m[f"{col}_total"]=round(tot,2)
        m[f"{col}_avg"]=round(avg,2)
        m[f"{col}_max"]=round(mx,2)

    # Date trends
    for col in cols["dt"][:1]:
        try:
            df["_month"]=df[col].dt.to_period("M").astype(str)
            mt=df.groupby("_month").size().reset_index()
            mt.columns=["Month","Count"]
            ch["monthly_trend"]={"t":"line","data":mt.to_dict("records"),"x":"Month","y":"Count","title":"Monthly Trend"}
            m["date_range"]=f"{df[col].min().strftime('%d %b %Y')} – {df[col].max().strftime('%d %b %Y')}"
            for nc in cols["num"][:2]:
                mr=df.groupby("_month")[nc].sum().reset_index()
                mr.columns=["Month",nc]
                ch[f"mtrend_{nc}"]={"t":"line","data":mr.to_dict("records"),"x":"Month","y":nc,"title":f"Monthly {nc.replace('_',' ').title()}"}
        except: pass

    # Categorical
    for col in cols["cat"]:
        l=col.replace("_"," ").title()
        vc=df[col].value_counts()
        m[f"{col}_top"]=str(vc.idxmax())
        m[f"{col}_unique"]=int(len(vc))
        cd=vc.reset_index()
        cd.columns=[l,"Count"]
        if len(vc)<=8:
            ch[f"pie_{col}"]={"t":"pie","data":cd.to_dict("records"),"n":l,"v":"Count","title":f"{l} Distribution"}
        else:
            ch[f"bar_{col}"]={"t":"bar","data":cd.head(10).to_dict("records"),"x":"Count","y":l,"title":f"Top {l}"}
        for nc in cols["num"][:1]:
            if 2<=len(vc)<=15:
                try:
                    ag=df.groupby(col)[nc].sum().sort_values(ascending=False).head(10)
                    ad=ag.reset_index()
                    ad.columns=[l,nc.replace("_"," ").title()]
                    ch[f"cross_{col}_{nc}"]={"t":"bar","data":ad.to_dict("records"),"x":nc.replace("_"," ").title(),"y":l,"title":f"{nc.replace('_',' ').title()} by {l}"}
                except: pass

    if len(cols["num"])>=2:
        ch["scatter"]={"t":"sc","x":cols["num"][0],"y":cols["num"][1],"title":f"{cols['num'][0].replace('_',' ').title()} vs {cols['num'][1].replace('_',' ').title()}"}
    return m,ch

def get_insights(df,m,cols):
    ins=[]
    ins.append(("i",f"📊 **{m['total_records']:,} records** aur **{m['total_columns']} columns** successfully analyze kiye gaye."))
    for col in cols["num"][:4]:
        l=col.replace("_"," ").title()
        tot=df[col].sum(); avg=df[col].mean(); std=df[col].std()
        cv=(std/avg*100) if avg!=0 else 0
        fmt=f"₹{tot/1e6:.2f}L" if tot>100000 else f"₹{tot:,.0f}" if tot>0 else f"{tot:,.1f}"
        ins.append(("i",f"💰 **Total {l}:** {fmt} | Avg: {avg:,.1f} | Max: {df[col].max():,.1f}"))
        if cv>80: ins.append(("w",f"⚠️ **'{l}'** mein bahut variation hai (CV={cv:.0f}%) — outliers check karo."))
        q1,q3=df[col].quantile(0.25),df[col].quantile(0.75)
        iqr=q3-q1
        out=int(((df[col]<q1-1.5*iqr)|(df[col]>q3+1.5*iqr)).sum())
        if out>len(df)*0.05: ins.append(("w",f"⚠️ **'{l}'** mein {out} outliers ({out/len(df)*100:.1f}%) — investigate karo."))
    for col in cols["cat"][:3]:
        l=col.replace("_"," ").title()
        vc=df[col].value_counts(); tp=vc.iloc[0]/len(df)*100
        if tp>70: ins.append(("w",f"⚠️ **'{l}'** mein '{vc.idxmax()}' ka {tp:.0f}% share — concentration risk hai."))
        else: ins.append(("i",f"📊 **Top {l}:** '{vc.idxmax()}' ({tp:.0f}%) | {len(vc)} unique values."))
    if "_month" in df.columns:
        mt=df.groupby("_month").size()
        if len(mt)>=3:
            last=int(mt.iloc[-2]); prev=int(mt.iloc[-3])
            chg=(last-prev)/prev*100 if prev else 0
            if abs(chg)>15: ins.append(("g" if chg>0 else "w",f"{'📈' if chg>0 else '📉'} Volume **{abs(chg):.0f}% {'badha' if chg>0 else 'ghata'}** last month."))
    miss=[(c,df[c].isnull().mean()*100) for c in df.columns if df[c].isnull().mean()>0.1]
    for col,pct in miss[:2]: ins.append(("w",f"⚠️ **'{col}'** mein {pct:.0f}% missing data — data collection improve karo."))
    if len(cols["num"])>=2:
        try:
            corr=df[cols["num"]].corr()
            for i in range(len(cols["num"])):
                for j in range(i+1,len(cols["num"])):
                    r=float(corr.iloc[i,j])
                    if abs(r)>0.7:
                        ins.append(("i",f"🔗 **Strong correlation** ({r:.2f}) between '{cols['num'][i]}' and '{cols['num'][j]}'."))
        except: pass
    return ins

def make_chart(cd,df):
    DARK=dict(plot_bgcolor="#161B22",paper_bgcolor="#161B22",
              font=dict(color="#8B949E",family="Inter"),
              margin=dict(l=10,r=10,t=40,b=10),height=300,
              title=dict(font=dict(color="#E6EDF3",size=13)),
              xaxis=dict(gridcolor="#21262D",showgrid=True),
              yaxis=dict(gridcolor="#21262D",showgrid=True))
    t=cd.get("t","")
    try:
        if t=="line":
            d=pd.DataFrame(cd["data"])
            fig=go.Figure(go.Scatter(
                x=d[cd["x"]],y=d[cd["y"]],
                fill="tozeroy",
                fillcolor="rgba(88,166,255,0.08)",
                line=dict(color="#58A6FF",width=2.5),
                mode="lines+markers",
                marker=dict(size=6,color="#58A6FF",line=dict(color="#0D1117",width=2))
            ))
            fig.update_layout(**DARK,title=cd.get("title",""))
            return fig
        elif t=="pie":
            d=pd.DataFrame(cd["data"])
            fig=px.pie(d,names=cd["n"],values=cd["v"],hole=0.5,color_discrete_sequence=PALETTE)
            fig.update_traces(textposition="outside",textinfo="percent+label",
                             textfont=dict(color="#8B949E",size=11))
            fig.update_layout(**DARK,title=cd.get("title",""),showlegend=False)
            return fig
        elif t=="bar":
            d=pd.DataFrame(cd["data"])
            fig=px.bar(d,x=cd["x"],y=cd["y"],orientation="h",
                      color_discrete_sequence=["#58A6FF"],title=cd.get("title",""))
            fig.update_traces(marker_line_width=0)
            fig.update_layout(**DARK)
            fig.update_layout(yaxis=dict(categoryorder="total ascending",gridcolor="#21262D"),
                             xaxis=dict(gridcolor="#21262D"))
            return fig
        elif t=="sc":
            cl2=classify_df(df); cc=cl2["cat"][0] if cl2["cat"] else None
            fig=px.scatter(df.sample(min(500,len(df))),x=cd["x"],y=cd["y"],
                          color=cc,color_discrete_sequence=PALETTE,opacity=0.7,title=cd.get("title",""))
            fig.update_layout(**DARK)
            return fig
    except: pass
    return None

# ══════════════════════════
# PAGES
# ══════════════════════════
def pg_login():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"]{background:radial-gradient(ellipse at top,#0D1F3C 0%,#0A0E1A 60%);}
    </style>""",unsafe_allow_html=True)
    _,col,_=st.columns([1,1.2,1])
    with col:
        st.markdown("""
        <div style="text-align:center;padding:3rem 0 2rem;">
            <div style="font-size:3rem;">📊</div>
            <div style="font-size:2.2rem;font-weight:800;color:#E6EDF3;margin-top:0.5rem;">InsightFlow AI</div>
            <div style="color:#8B949E;font-size:0.9rem;margin-top:0.3rem;">Lucknow Ki Data Analytics Agency</div>
        </div>""",unsafe_allow_html=True)
        st.markdown('<div class="login-card">',unsafe_allow_html=True)
        st.markdown('<p style="color:#E6EDF3;font-weight:600;font-size:1rem;margin-bottom:1rem;">🔐 Login Karo</p>',unsafe_allow_html=True)
        un=st.text_input("Username",placeholder="apna username daalo",label_visibility="collapsed")
        pw=st.text_input("Password",type="password",placeholder="password daalo",label_visibility="collapsed")
        if st.button("Login →",use_container_width=True,type="primary"):
            if not un or not pw: st.error("Dono fields bharo")
            else:
                r=do_login(un,pw)
                if r["ok"]: ss(r); st.session_state["page"]="dashboard"; st.rerun()
                else: st.error(r["msg"])
        st.markdown("</div>",unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#6E7681;font-size:0.75rem;margin-top:1rem;">Default: <b style="color:#8B949E">admin</b> / <b style="color:#8B949E">admin@123</b></p>',unsafe_allow_html=True)

def sidebar():
    u=gu()
    with st.sidebar:
        rc="#F85149" if ia() else "#58A6FF"
        st.markdown(f"""
        <div style="padding:1rem;background:#0D1117;border-radius:10px;margin-bottom:1rem;border:1px solid #21262D;">
            <div style="font-size:0.65rem;color:#6E7681;font-weight:600;letter-spacing:1px;">LOGGED IN</div>
            <div style="font-size:0.95rem;font-weight:700;color:#E6EDF3;margin-top:4px;">{u["name"]}</div>
            <span style="font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:6px;background:{rc}22;color:{rc};">{u["role"].upper()}</span>
            {"<div style='font-size:0.75rem;color:#6E7681;margin-top:4px;'>"+str(u.get('cn') or '')+"</div>" if u.get("cn") else ""}
        </div>""",unsafe_allow_html=True)

        pages={"upload":"📁  Upload & Analyze","clients":"👥  Clients","users":"🔐  Users","festival":"🎉  Festivals"} if ia() else {"dashboard":"📈  My Dashboard"}
        if ic() and not st.session_state.get("df"): pages={"upload":"📁  Upload Data",**pages}

        for pk,pl in pages.items():
            t="primary" if st.session_state.get("page")==pk else "secondary"
            if st.button(pl,key=f"n_{pk}",use_container_width=True,type=t):
                st.session_state["page"]=pk; st.rerun()

        if ia():
            st.markdown('<hr style="border-color:#21262D;margin:1rem 0;">',unsafe_allow_html=True)
            cls=get_clients()
            if cls:
                st.markdown('<div style="font-size:0.65rem;color:#6E7681;font-weight:600;letter-spacing:1px;margin-bottom:0.5rem;">ACTIVE CLIENT</div>',unsafe_allow_html=True)
                ops={"— Client Select Karo —":None}
                ops.update({c["name"]:c for c in cls})
                sel=st.selectbox("",list(ops.keys()),label_visibility="collapsed")
                if ops[sel]: st.session_state["ac"]=ops[sel]

        if st.session_state.get("df") is not None:
            df=st.session_state["df"]
            st.markdown(f"""
            <div style="background:#0D2818;border:1px solid #1A4731;border-radius:8px;padding:0.8rem;margin-top:0.5rem;">
                <div style="font-size:0.65rem;font-weight:600;color:#3FB950;">✓ DATA LOADED</div>
                <div style="font-size:0.78rem;color:#6E7681;margin-top:3px;">{df.shape[0]:,} rows · {df.shape[1]} columns</div>
            </div>""",unsafe_allow_html=True)

        st.markdown('<hr style="border-color:#21262D;margin:1rem 0;">',unsafe_allow_html=True)
        if st.button("🚪  Logout",use_container_width=True): lo(); st.rerun()
        st.markdown('<p style="text-align:center;color:#6E7681;font-size:0.7rem;margin-top:0.5rem;">InsightFlow AI v2.0</p>',unsafe_allow_html=True)

def pg_upload():
    ac=st.session_state.get("ac",{}) or {}
    cn=ac.get("name","") or (gu().get("cn") or "")

    st.markdown(f"""
    <div class="hero">
        <div class="badge">📍 Lucknow · Data Analytics</div>
        <h1>📊 InsightFlow AI</h1>
        <p>Koi bhi CSV ya Excel upload karo — AI automatically analyze karega{f" · {cn}" if cn else ""}</p>
    </div>""",unsafe_allow_html=True)

    c1,c2=st.columns([3,2])
    with c1:
        st.markdown('<div class="sec">📁 DATA UPLOAD</div>',unsafe_allow_html=True)
        up=st.file_uploader("",type=["csv","xlsx","xls"],label_visibility="collapsed")
        use_ai=st.checkbox("🤖 Claude AI se insights lo",value=False)
        ak=""
        if use_ai: ak=st.text_input("Anthropic API Key",type="password",placeholder="sk-ant-...",label_visibility="collapsed")

        if up:
            with st.spinner("🔄 Data analyze ho raha hai..."):
                try:
                    df_raw=pd.read_csv(up,on_bad_lines="skip") if up.name.endswith(".csv") else pd.read_excel(up)
                except: st.error("File read error. CSV ya Excel format check karo."); st.stop()
                df,cr=clean_df(df_raw.copy())
                cols=classify_df(df)
                m,ch=compute_metrics(df,cols)
                ins=get_insights(df,m,cols)
                st.session_state.update({"df":df,"cols":cols,"metrics":m,"charts":ch,"insights":ins,"cr":cr})
                if use_ai and ak:
                    with st.spinner("🤖 Claude analyze kar raha hai..."):
                        try:
                            import anthropic
                            ns="\n".join([f"  {c}: total={df[c].sum():,.1f}, avg={df[c].mean():,.1f}, max={df[c].max():,.1f}" for c in cols["num"][:5]])
                            cs="\n".join([f"  {c}: {dict(df[c].value_counts().head(3))}" for c in cols["cat"][:4]])
                            pr=f"You are InsightFlow AI data analyst for a business in Lucknow, India.\nDataset: {df.shape[0]} rows, columns: {', '.join(df.columns.tolist())}\nNumerics:\n{ns}\nCategories:\n{cs}\nProvide 6 specific actionable business insights with exact numbers. Use Indian context (rupees, lakh, crore). Be specific and data-driven. Use emojis. 1-2 sentences each."
                            ac2=anthropic.Anthropic(api_key=ak)
                            msg=ac2.messages.create(model="claude-sonnet-4-20250514",max_tokens=800,messages=[{"role":"user","content":pr}])
                            st.session_state["ai"]=msg.content[0].text
                        except Exception as e: st.session_state["ai"]=f"AI error: {e}"

            sc=cr["score"]
            col="#3FB950" if sc>=80 else "#D29922" if sc>=60 else "#F85149"
            lbl="Excellent" if sc>=85 else "Good" if sc>=70 else "Fair" if sc>=50 else "Needs Work"
            st.markdown(f"""
            <div style="background:#161B22;border:1px solid #21262D;border-radius:12px;padding:1.2rem 1.5rem;margin:1rem 0;display:flex;align-items:center;gap:1.5rem;">
                <div style="text-align:center;min-width:70px;">
                    <div style="font-size:2.5rem;font-weight:800;color:{col};">{sc}</div>
                    <div style="font-size:0.6rem;color:#6E7681;font-weight:600;">QUALITY</div>
                </div>
                <div>
                    <div style="font-weight:700;color:#E6EDF3;font-size:1rem;">{lbl} Data Quality</div>
                    <div style="font-size:0.8rem;color:#6E7681;margin-top:3px;">{df.shape[0]:,} rows · {len(cols["num"])} numeric · {len(cols["cat"])} categorical · {len(cols["dt"])} date</div>
                </div>
            </div>""",unsafe_allow_html=True)

            with st.expander("📋 Cleaning Details"):
                for f2 in cr["fixes"][:6]: st.success(f2,icon=None)
                for w in cr["warns"]: st.warning(w,icon=None)

            if st.button("📈 Dashboard Dekho →",type="primary",use_container_width=True):
                st.session_state["page"]="dashboard"; st.rerun()

    with c2:
        st.markdown('<div class="sec">🏭 SUPPORTED DATA TYPES</div>',unsafe_allow_html=True)
        items=[("🏥","Hospital","#F85149","Patient, revenue, department, disease"),("🎓","School / Coaching","#58A6FF","Student, marks, attendance, fee"),("🛒","Shop / E-Commerce","#D29922","Orders, product, amount, returns"),("🚚","Transport","#3FB950","Shipment, route, cost, delivery"),("🍽️","Restaurant","#F78166","Sales, items, daily revenue"),("🏠","Real Estate","#BC8CFF","Leads, property, area, price"),("💊","Pharmacy","#79C0FF","Medicine, stock, sales, expiry"),("📦","Koi bhi data","#56D364","CSV/Excel — AI khud samjhega!")]
        for icon,name,color,hint in items:
            st.markdown(f'<div style="background:#161B22;border:1px solid #21262D;border-left:3px solid {color};border-radius:8px;padding:0.7rem 1rem;margin:0.3rem 0;"><b style="color:#E6EDF3;">{icon} {name}</b><div style="font-size:0.72rem;color:#6E7681;margin-top:2px;">{hint}</div></div>',unsafe_allow_html=True)

def pg_dashboard():
    if not st.session_state.get("df"):
        st.markdown('<div style="text-align:center;padding:4rem;color:#8B949E;"><div style="font-size:3rem;">📂</div><div style="font-size:1.1rem;margin-top:1rem;color:#E6EDF3;">Koi data nahi mila</div><div style="margin-top:0.5rem;">Pehle data upload karo</div></div>',unsafe_allow_html=True)
        if st.button("→ Upload Karo",type="primary"): st.session_state["page"]="upload"; st.rerun()
        return

    df=st.session_state["df"]; cols=st.session_state["cols"]
    m=st.session_state["metrics"]; ch=st.session_state["charts"]
    ins=st.session_state["insights"]
    ac=st.session_state.get("ac",{}) or {}
    cn=ac.get("name","") or (gu().get("cn") or "Client")

    st.markdown(f"""
    <div class="hero">
        <div class="badge">📊 Live Dashboard</div>
        <h1>📈 Analytics Dashboard</h1>
        <p>{cn} · {m["total_records"]:,} records analyze kiye{f" · {m.get('date_range','')}" if m.get('date_range') else ""}</p>
    </div>""",unsafe_allow_html=True)

    # KPI Cards
    ncs=cols["num"][:4]
    if ncs:
        kcs=st.columns(len(ncs))
        colors_kpi=["#58A6FF","#3FB950","#D29922","#F85149"]
        for i,col in enumerate(ncs):
            l=col.replace("_"," ").title()
            tot=float(df[col].sum()); avg=float(df[col].mean())
            fmt=f"₹{tot/1e7:.2f}Cr" if tot>=1e7 else f"₹{tot/1e5:.1f}L" if tot>=1e5 else f"{tot:,.1f}"
            with kcs[i]:
                st.markdown(f'<div class="kpi" style="--accent:{colors_kpi[i]};"><div class="kpi-l">Total {l}</div><div class="kpi-v">{fmt}</div><div class="kpi-s">avg: {avg:,.1f} · max: {df[col].max():,.1f}</div></div>',unsafe_allow_html=True)
        st.markdown("")

    # Metric rows
    if cols["cat"]:
        cs2=st.columns(min(4,len(cols["cat"])))
        for i,col in enumerate(cols["cat"][:4]):
            with cs2[i]: st.metric(col.replace("_"," ").title(),str(df[col].value_counts().idxmax()),f"{int(df[col].value_counts().iloc[0])} entries")

    st.markdown("")
    t1,t2,t3,t4=st.tabs(["📈  Trends","📊  Charts","💡  Insights","📋  Raw Data"])

    with t1:
        tc={k:v for k,v in ch.items() if v.get("t")=="line"}
        if not tc:
            st.markdown('<div style="text-align:center;padding:3rem;color:#6E7681;"><div style="font-size:2rem;">📅</div><div style="margin-top:0.5rem;">Date column nahi mila — trends nahi dikha sakte</div></div>',unsafe_allow_html=True)
        else:
            it=list(tc.items())
            for i in range(0,len(it),2):
                cc2=st.columns(2)
                for j,(k,cd) in enumerate(it[i:i+2]):
                    with cc2[j]:
                        st.markdown(f'<div class="sec">{cd["title"].upper()}</div>',unsafe_allow_html=True)
                        fig=make_chart(cd,df)
                        if fig: st.plotly_chart(fig,use_container_width=True)

    with t2:
        dc={k:v for k,v in ch.items() if v.get("t") in ("pie","bar") and not k.startswith("cross")}
        if dc:
            it=list(dc.items())
            for i in range(0,min(len(it),8),2):
                cc2=st.columns(2)
                for j,(k,cd) in enumerate(it[i:i+2]):
                    with cc2[j]:
                        fig=make_chart(cd,df)
                        if fig: st.plotly_chart(fig,use_container_width=True)

        cx={k:v for k,v in ch.items() if k.startswith("cross")}
        if cx:
            st.markdown('<div class="sec">CATEGORY × NUMBERS</div>',unsafe_allow_html=True)
            it=list(cx.items())
            for i in range(0,min(len(it),4),2):
                cc2=st.columns(2)
                for j,(k,cd) in enumerate(it[i:i+2]):
                    with cc2[j]:
                        fig=make_chart(cd,df)
                        if fig: st.plotly_chart(fig,use_container_width=True)

        if len(cols["num"])>=2:
            st.markdown('<div class="sec">CORRELATION HEATMAP</div>',unsafe_allow_html=True)
            try:
                corr=df[cols["num"]].corr()
                fig=px.imshow(corr,text_auto=".2f",aspect="auto",
                             color_continuous_scale=["#F85149","#161B22","#58A6FF"],zmin=-1,zmax=1)
                fig.update_layout(plot_bgcolor="#161B22",paper_bgcolor="#161B22",
                                 font=dict(color="#8B949E"),height=380,
                                 margin=dict(l=10,r=10,t=10,b=10))
                st.plotly_chart(fig,use_container_width=True)
            except: pass

    with t3:
        st.markdown('<div class="sec">AUTO-GENERATED INSIGHTS</div>',unsafe_allow_html=True)
        cm={"g":"ig","w":"iw","d":"id","i":"ii"}
        for tp,txt in ins:
            st.markdown(f'<div class="ins {cm.get(tp,"ii")}">{txt}</div>',unsafe_allow_html=True)
        if ai:=st.session_state.get("ai"):
            st.markdown('<div class="sec" style="margin-top:1.5rem;">🤖 CLAUDE AI ANALYSIS</div>',unsafe_allow_html=True)
            st.markdown(f'<div class="ins ii">{ai.replace(chr(10),"<br>")}</div>',unsafe_allow_html=True)
        zc=next((c for c in cols["cat"] if any(z in c for z in ["city","zone","area","location","city"])),None)
        if zc:
            st.markdown('<div class="sec">📍 LOCATION ANALYSIS</div>',unsafe_allow_html=True)
            zd=df[zc].value_counts().reset_index(); zd.columns=["Location","Count"]
            fig=px.bar(zd.head(10),x="Count",y="Location",orientation="h",color_discrete_sequence=["#58A6FF"])
            fig.update_layout(plot_bgcolor="#161B22",paper_bgcolor="#161B22",font=dict(color="#8B949E"),height=300,margin=dict(l=10,r=10,t=10,b=10),yaxis=dict(categoryorder="total ascending",gridcolor="#21262D"),xaxis=dict(gridcolor="#21262D"))
            st.plotly_chart(fig,use_container_width=True)

    with t4:
        st.markdown(f'<div class="sec">RAW DATA — {len(df):,} ROWS</div>',unsafe_allow_html=True)
        st.dataframe(df.head(500),use_container_width=True)
        c1,c2=st.columns(2)
        with c1: st.download_button("⬇️ CSV Download",df.to_csv(index=False).encode(),"insightflow_data.csv","text/csv",use_container_width=True)
        with c2:
            try:
                buf=io.BytesIO()
                with pd.ExcelWriter(buf,engine="xlsxwriter") as w:
                    df.to_excel(w,index=False,sheet_name="Data")
                    if cols["num"]: df[cols["num"]].describe().round(2).to_excel(w,sheet_name="Stats")
                st.download_button("⬇️ Excel Download",buf.getvalue(),"insightflow_report.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
            except: pass

def pg_clients():
    st.markdown('<div class="hero"><h1>👥 Client Management</h1><p>Lucknow ke clients manage karo</p></div>',unsafe_allow_html=True)
    with st.expander("➕ Naya Client Add Karo"):
        with st.form("ac"):
            c1,c2=st.columns(2)
            with c1:
                nm=st.text_input("Client Name *")
                ind=st.selectbox("Industry",["hospital","education","ecommerce","logistics","restaurant","real_estate","pharmacy","other"])
            with c2:
                em=st.text_input("Email")
                city=st.selectbox("Lucknow Area",["Hazratganj","Gomtinagar","Alambagh","Chowk","Aliganj","Indira Nagar","Rajajipuram","Chinhat","Other"])
            if st.form_submit_button("✅ Add Client",use_container_width=True) and nm:
                cid=add_client(nm,ind,em,city)
                st.success(f"✅ '{nm}' add ho gaya! ID: {cid}"); st.rerun()

    icons={"hospital":"🏥","education":"🎓","ecommerce":"🛒","logistics":"🚚","restaurant":"🍽️","real_estate":"🏠","pharmacy":"💊","other":"📊"}
    for c in get_clients():
        col1,col2,col3=st.columns([4,3,1])
        with col1: st.markdown(f'<div style="color:#E6EDF3;font-weight:600;">{icons.get(c["industry"],"📊")} {c["name"]}</div><div style="font-size:0.78rem;color:#6E7681;">{c["industry"]} · 📍{c.get("city","Lucknow")}</div>',unsafe_allow_html=True)
        with col2: st.caption(c.get("email") or "—")
        with col3:
            if st.button("Load",key=f"l_{c['id']}",use_container_width=True):
                st.session_state["ac"]=c; st.session_state["page"]="upload"; st.rerun()
        st.markdown('<hr style="border-color:#21262D;margin:0.4rem 0;">',unsafe_allow_html=True)

def pg_users():
    st.markdown('<div class="hero"><h1>🔐 User Management</h1><p>Users banao aur manage karo</p></div>',unsafe_allow_html=True)
    cls=get_clients()
    with st.expander("➕ Naya User Add Karo"):
        with st.form("au"):
            c1,c2=st.columns(2)
            with c1:
                un=st.text_input("Username *"); pw=st.text_input("Password *",type="password"); fn=st.text_input("Full Name")
            with c2:
                role=st.selectbox("Role",["client","admin"]); em=st.text_input("Email"); cid=None
                if role=="client" and cls:
                    ops={f"{c['name']} ({c['industry']})":c["id"] for c in cls}
                    sel=st.selectbox("Client se Link Karo",list(ops.keys())); cid=ops[sel]
            if st.form_submit_button("✅ User Banao",use_container_width=True):
                r=create_user(un,pw,role,cid,fn,em)
                if r["ok"]: st.success(r["msg"]); st.rerun()
                else: st.error(r["msg"])

    st.markdown('<div class="sec">ALL USERS</div>',unsafe_allow_html=True)
    src=st.text_input("🔍 Search",placeholder="username search karo...",label_visibility="collapsed")
    us=get_users()
    if src: us=[u for u in us if src.lower() in u["username"].lower()]
    rc2={"admin":"#F85149","client":"#58A6FF"}
    for u in us:
        c1,c2,c3,c4,c5=st.columns([3,2,2,1,1])
        with c1: st.markdown(f'<div style="color:#E6EDF3;font-weight:600;">@{u["username"]} <span style="font-size:0.65rem;padding:2px 7px;border-radius:6px;background:{rc2.get(u["role"],"#888")}22;color:{rc2.get(u["role"],"#888")};">{u["role"].upper()}</span></div><div style="font-size:0.78rem;color:#6E7681;">{u.get("full_name") or "—"}</div>',unsafe_allow_html=True)
        with c2: st.caption(u.get("cn") or "Admin")
        with c3: st.caption(f"{'🟢' if u['is_active'] else '🔴'} {str(u.get('last_login') or 'Never')[:10]}")
        with c4:
            with st.popover("🔑"):
                np=st.text_input("New pw",type="password",key=f"np_{u['id']}")
                if st.button("Update",key=f"up_{u['id']}"): st.success("✅") if upw(u["id"],np) else st.error("Min 6 chars")
        with c5:
            if u["role"]!="admin":
                if st.button("⏸" if u["is_active"] else "▶",key=f"t_{u['id']}"): tog(u["id"]); st.rerun()
        st.markdown('<hr style="border-color:#21262D;margin:0.3rem 0;">',unsafe_allow_html=True)

def pg_festival():
    st.markdown('<div class="hero"><h1>🎉 Festival Calendar — Lucknow 2026</h1><p>Festivals ke hisaab se business plan karo — peak demand predict karo</p></div>',unsafe_allow_html=True)
    FEST={"January":["🪁 Makar Sankranti","🇮🇳 Republic Day"],"February":["🌸 Basant Panchami"],"March":["🎨 Holi","🌙 Eid ul-Fitr"],"April":["🪔 Ram Navami","🎭 Lucknow Mahotsav"],"August":["🇮🇳 Independence Day","🪢 Raksha Bandhan","🎪 Janmashtami"],"October":["🌺 Navratri","🏹 Dussehra","🪔 Diwali"],"November":["🪔 Diwali","🌊 Chhath Puja","🎭 Lucknow Mahotsav"],"December":["🎄 Christmas","🎆 New Year"]}
    months=["January","February","March","April","May","June","July","August","September","October","November","December"]
    cs=st.columns(3)
    for i,mo in enumerate(months):
        fs=FEST.get(mo,[])
        with cs[i%3]:
            col="#D29922" if fs else "#21262D"
            st.markdown(f'<div style="background:#161B22;border:1px solid {col};border-radius:10px;padding:1rem;margin:0.3rem 0;"><div style="font-weight:700;color:#E6EDF3;">{mo}</div>{"".join([f"<div style=font-size:0.8rem;color:#8B949E;margin-top:4px;>{f}</div>" for f in fs]) if fs else "<div style=font-size:0.8rem;color:#6E7681;>No major festivals</div>"}</div>',unsafe_allow_html=True)

    st.markdown('<div class="sec">💡 BUSINESS TIPS</div>',unsafe_allow_html=True)
    tips=[("🪔 Diwali (Oct-Nov)","Gift hampers, electronics, clothing — 30-50% sales boost. Stock 2 months pehle.","#D29922"),("🌙 Eid (March-April)","Clothing, sweets, gifts — Hazratganj aur Chowk mein 40%+ spike. Muslim-majority areas key zones.","#58A6FF"),("🌺 Navratri (Oct)","Organic/satvik products, puja items, new clothing — 9 din ka celebration.","#3FB950"),("📚 Back to School (Jun-Jul)","Stationery, uniforms, books — coaching institutes full capacity.","#BC8CFF"),("🎭 Lucknow Mahotsav (Nov)","Tourism spike — hospitality, food, handicrafts peak time.","#F78166")]
    for ev,tip,color in tips:
        st.markdown(f'<div class="ins ii" style="border-color:{color}44;background:{color}11;color:#E6EDF3;"><b style="color:{color};">{ev}</b><br><span style="color:#8B949E;">{tip}</span></div>',unsafe_allow_html=True)

# ══════════════════════════
# MAIN
# ══════════════════════════
init_db()
for k,v in {"page":"login","df":None,"ac":None,"ai":None}.items():
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
