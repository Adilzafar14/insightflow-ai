import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import hashlib, hmac, secrets, sqlite3, json, io, os
from datetime import datetime

st.set_page_config(page_title="InsightFlow AI",page_icon="📊",layout="wide",initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Sora',sans-serif;}
[data-testid="stSidebar"]{background:#0D1B2A !important;}
[data-testid="stSidebar"] *{color:#CBD5E1 !important;}
[data-testid="stAppViewContainer"]{background:#F8FAFC;}
.hero{background:linear-gradient(135deg,#0D1B2A,#1E3A5F,#2D6A9F);border-radius:18px;padding:2rem 2.5rem;color:white;margin-bottom:1.5rem;position:relative;overflow:hidden;}
.hero::after{content:'📊';position:absolute;right:2rem;top:50%;transform:translateY(-50%);font-size:5rem;opacity:0.12;}
.hero h1{font-size:1.8rem;font-weight:800;margin:0;}
.hero p{opacity:0.75;margin:0.4rem 0 0;font-size:0.9rem;}
.kpi{background:white;border-radius:14px;padding:1.2rem 1.4rem;border:1px solid #E4EAF1;border-left:5px solid #2D6A9F;box-shadow:0 2px 12px rgba(0,0,0,0.06);transition:transform 0.18s;margin-bottom:0.5rem;}
.kpi:hover{transform:translateY(-2px);}
.kpi-l{font-size:0.68rem;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.8px;}
.kpi-v{font-size:1.7rem;font-weight:800;color:#1F2937;margin:0.25rem 0 0;}
.kpi-s{font-size:0.73rem;color:#6B7280;margin-top:2px;}
.ins{border-radius:10px;padding:0.9rem 1.1rem;margin:0.35rem 0;font-size:0.88rem;line-height:1.65;border-left:4px solid;}
.ig{background:#F0FDF4;border-color:#22C55E;color:#14532D;}
.iw{background:#FFFBEB;border-color:#F59E0B;color:#78350F;}
.id{background:#FEF2F2;border-color:#EF4444;color:#7F1D1D;}
.ii{background:#EFF6FF;border-color:#3B82F6;color:#1E3A8A;}
.sec{font-size:0.95rem;font-weight:700;color:#1F2937;border-bottom:2px solid #2D6A9F;padding-bottom:0.35rem;margin:1.4rem 0 0.8rem;}
div[data-testid="stMetric"]{background:white;border:1px solid #E4EAF1;border-radius:10px;padding:0.8rem;}
</style>
""",unsafe_allow_html=True)

DB="insightflow.db"
P=["#2D6A9F","#EF4444","#10B981","#F59E0B","#8B5CF6","#EC4899","#F97316","#06B6D4"]
ZONES=["Hazratganj","Gomtinagar","Alambagh","Chowk","Aliganj","Indira Nagar","Rajajipuram","Chinhat","Other"]
FESTIVALS={"January":["Makar Sankranti"],"February":["Basant Panchami"],"March":["Holi","Eid"],"April":["Ram Navami"],"August":["Independence Day","Raksha Bandhan"],"October":["Navratri","Dussehra","Diwali"],"November":["Diwali","Chhath Puja","Lucknow Mahotsav"],"December":["Christmas"]}

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

def vp(pw,h,s): a,_=_hp(pw,s); return hmac.compare_digest(a,h)

def do_login(un,pw):
    c=get_db()
    u=c.execute("SELECT u.*,cl.name as cn,cl.industry as ind FROM users u LEFT JOIN clients cl ON cl.id=u.client_id WHERE u.username=? COLLATE NOCASE",(un.strip(),)).fetchone()
    c.close()
    if not u: return{"ok":False,"msg":"❌ Username nahi mila"}
    if not u["is_active"]: return{"ok":False,"msg":"❌ Account disabled"}
    if not vp(pw,u["password_hash"],u["salt"]): return{"ok":False,"msg":"❌ Password galat"}
    c=get_db(); c.execute("UPDATE users SET last_login=datetime('now') WHERE id=?",(u["id"],)); c.commit(); c.close()
    return{"ok":True,"id":u["id"],"username":u["username"],"role":u["role"],"name":u["full_name"] or u["username"],"client_id":u["client_id"],"cn":u["cn"],"ind":u["ind"]}

def create_user(un,pw,role="client",cid=None,fn="",em=""):
    if len(un.strip())<3: return{"ok":False,"msg":"Username min 3 chars"}
    if len(pw)<6: return{"ok":False,"msg":"Password min 6 chars"}
    h,s=_hp(pw)
    c=get_db()
    try:
        c.execute("INSERT INTO users(username,password_hash,salt,role,client_id,full_name,email)VALUES(?,?,?,?,?,?,?)",(un.strip().lower(),h,s,role,cid,fn,em))
        c.commit(); c.close(); return{"ok":True,"msg":f"✅ '{un}' create ho gaya!"}
    except sqlite3.IntegrityError:
        c.close(); return{"ok":False,"msg":f"❌ '{un}' already exists"}

def get_clients():
    c=get_db(); r=c.execute("SELECT * FROM clients WHERE is_active=1 ORDER BY name").fetchall(); c.close(); return[dict(x) for x in r]

def get_users():
    c=get_db(); r=c.execute("SELECT u.*,cl.name as cn,cl.industry FROM users u LEFT JOIN clients cl ON cl.id=u.client_id ORDER BY u.role DESC,u.username").fetchall(); c.close(); return[dict(x) for x in r]

def add_client(nm,ind,em="",city="Lucknow"):
    c=get_db(); cur=c.execute("INSERT INTO clients(name,industry,email,city)VALUES(?,?,?,?)",(nm,ind,em,city)); c.commit(); i=cur.lastrowid; c.close(); return i

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
    for k in ["df","cols","metrics","charts","insights","page","ac"]: st.session_state.pop(k,None)

def clean(df):
    fixes,warns=[],[]
    orig=df.shape
    df.columns=[str(c).strip().lower().replace(" ","_").replace("-","_").replace(".","_").replace("/","_").replace("(","").replace(")","").replace("%","pct").replace("#","num") for c in df.columns]
    fixes.append("✅ Column names normalize kiye")
    b=len(df); df.drop_duplicates(inplace=True)
    if len(df)<b: fixes.append(f"✅ {b-len(df)} duplicates hataaye")
    df.dropna(how="all",inplace=True)
    for col in df.columns:
        if df[col].dtype==object:
            cl=df[col].astype(str).str.replace(",","",regex=False).str.replace("₹","",regex=False).str.replace("$","",regex=False).str.strip()
            n=pd.to_numeric(cl,errors="coerce")
            if n.notna().mean()>0.7: df[col]=n; fixes.append(f"✅ '{col}' → numeric"); continue
        if df[col].dtype==object:
            try:
                p=pd.to_datetime(df[col],infer_datetime_format=True,errors="coerce")
                if p.notna().mean()>0.7: df[col]=p; fixes.append(f"✅ '{col}' → datetime")
            except: pass
    for col in df.columns:
        m=df[col].isnull().mean()
        if m==0: continue
        if m>0.4: warns.append(f"⚠️ '{col}' mein {m*100:.0f}% missing")
        if pd.api.types.is_numeric_dtype(df[col]): df[col]=df[col].fillna(df[col].median())
        else:
            md=df[col].mode(); df[col]=df[col].fillna(md[0] if len(md) else "Unknown")
    sc=max(0,min(100,round(100-len(warns)*8-(orig[0]-len(df))/max(orig[0],1)*20,1)))
    return df.reset_index(drop=True),{"fixes":fixes,"warns":warns,"score":sc,"orig":orig,"final":df.shape}

def classify(df):
    num,cat,dt,ids=[],[],[],[]
    for col in df.columns:
        if any(k in col for k in ["_id","id_","serial"]) and df[col].nunique()>len(df)*0.8: ids.append(col); continue
        if pd.api.types.is_datetime64_any_dtype(df[col]): dt.append(col); continue
        if pd.api.types.is_numeric_dtype(df[col]): num.append(col); continue
        if df[col].nunique()<=min(50,len(df)*0.3): cat.append(col)
        else: ids.append(col)
    return{"num":num,"cat":cat,"dt":dt,"ids":ids}

def metrics(df,cols):
    m={};ch={}
    m["total"]=len(df); m["cols"]=len(df.columns)
    for col in cols["num"]:
        l=col.replace("_"," ").title()
        m[f"{col}_tot"]=round(df[col].sum(),2); m[f"{col}_avg"]=round(df[col].mean(),2)
        ch[f"h_{col}"]={"t":"hist","col":col,"title":f"{l} Distribution"}
    for col in cols["dt"][:1]:
        df["_m"]=df[col].dt.to_period("M").astype(str)
        mt=df.groupby("_m").size().reset_index(name="Count"); mt.columns=["Month","Count"]
        ch["trend"]={"t":"line","d":mt.to_dict("r"),"x":"Month","y":"Count","title":"Monthly Trend"}
        m["range"]=f"{df[col].min().strftime('%d %b %Y')} – {df[col].max().strftime('%d %b %Y')}"
        for nc in cols["num"][:2]:
            mr=df.groupby("_m")[nc].sum().reset_index(); mr.columns=["Month",nc]
            ch[f"mt_{nc}"]={"t":"line","d":mr.to_dict("r"),"x":"Month","y":nc,"title":f"Monthly {nc.replace('_',' ').title()}"}
    for col in cols["cat"]:
        l=col.replace("_"," ").title(); vc=df[col].value_counts()
        m[f"{col}_top"]=str(vc.idxmax()); m[f"{col}_u"]=len(vc)
        cd=vc.reset_index(); cd.columns=[l,"Count"]
        if len(vc)<=7: ch[f"p_{col}"]={"t":"pie","d":cd.to_dict("r"),"n":l,"v":"Count","title":f"{l} Split"}
        else: ch[f"b_{col}"]={"t":"bar","d":cd.head(10).to_dict("r"),"x":"Count","y":l,"title":f"Top {l}"}
        for nc in cols["num"][:1]:
            if len(vc)<=15:
                ag=df.groupby(col)[nc].sum().sort_values(ascending=False).head(10)
                ad=ag.reset_index(); ad.columns=[l,nc.replace("_"," ").title()]
                ch[f"c_{col}_{nc}"]={"t":"bar","d":ad.to_dict("r"),"x":nc.replace("_"," ").title(),"y":l,"title":f"{nc.replace('_',' ').title()} by {l}"}
    if len(cols["num"])>=2: ch["sc"]={"t":"sc","x":cols["num"][0],"y":cols["num"][1],"title":f"{cols['num'][0]} vs {cols['num'][1]}"}
    return m,ch

def insights(df,m,cols):
    ins=[]
    ins.append(("i",f"📊 {m['total']:,} records, {m['cols']} columns analyze kiye."))
    for col in cols["num"][:3]:
        l=col.replace("_"," ").title(); tot=df[col].sum(); avg=df[col].mean(); std=df[col].std()
        cv=(std/avg*100) if avg else 0
        fmt=f"₹{tot/1e6:.2f}L" if tot>1e5 else f"{tot:,.1f}"
        ins.append(("i",f"💰 Total {l}: {fmt} (avg: {avg:,.1f})"))
        if cv>80: ins.append(("w",f"⚠️ '{l}' mein bahut variation ({cv:.0f}%) — outliers check karo."))
        q1,q3=df[col].quantile(0.25),df[col].quantile(0.75)
        out=((df[col]<q1-1.5*(q3-q1))|(df[col]>q3+1.5*(q3-q1))).sum()
        if out>len(df)*0.05: ins.append(("w",f"⚠️ '{l}' mein {out} outliers."))
    for col in cols["cat"][:3]:
        l=col.replace("_"," ").title(); vc=df[col].value_counts(); tp=vc.iloc[0]/len(df)*100
        if tp>70: ins.append(("w",f"⚠️ '{l}' mein '{vc.idxmax()}' ka {tp:.0f}% — concentration risk."))
        else: ins.append(("i",f"📊 Top {l}: '{vc.idxmax()}' ({tp:.0f}%). {len(vc)} unique values."))
    if "_m" in df.columns:
        mt=df.groupby("_m").size()
        if len(mt)>=3:
            last,prev=mt.iloc[-2],mt.iloc[-3]
            chg=(last-prev)/prev*100 if prev else 0
            if abs(chg)>15: ins.append(("g" if chg>0 else "w",f"{'📈' if chg>0 else '📉'} Volume {abs(chg):.0f}% {'badha' if chg>0 else 'ghata'}."))
    return ins

def rc(cd,df):
    L=dict(plot_bgcolor="white",paper_bgcolor="white",margin=dict(l=5,r=5,t=35,b=5),height=280,font_family="Sora")
    t=cd.get("t","")
    try:
        if t=="hist":
            f=px.histogram(df,x=cd["col"],nbins=30,color_discrete_sequence=["#2D6A9F"],title=cd.get("title",""))
            f.update_layout(**L,bargap=0.05); return f
        elif t=="line":
            d=pd.DataFrame(cd["d"])
            f=go.Figure(go.Scatter(x=d[cd["x"]],y=d[cd["y"]],fill="tozeroy",fillcolor="rgba(45,106,159,0.1)",line=dict(color="#2D6A9F",width=2.5),mode="lines+markers",marker=dict(size=6)))
            f.update_layout(**L,title=dict(text=cd.get("title",""),font_size=12)); return f
        elif t=="pie":
            d=pd.DataFrame(cd["d"])
            f=px.pie(d,names=cd["n"],values=cd["v"],hole=0.45,color_discrete_sequence=P,title=cd.get("title",""))
            f.update_traces(textposition="outside",textinfo="percent+label"); f.update_layout(**L,showlegend=False); return f
        elif t=="bar":
            d=pd.DataFrame(cd["d"])
            f=px.bar(d,x=cd["x"],y=cd["y"],orientation="h",color_discrete_sequence=["#2D6A9F"],title=cd.get("title",""))
            f.update_layout(**L); f.update_layout(yaxis=dict(categoryorder="total ascending",showgrid=False),xaxis=dict(showgrid=True,gridcolor="#F0F3F8")); return f
        elif t=="sc":
            cl=classify(df); cc=cl["cat"][0] if cl["cat"] else None
            f=px.scatter(df.sample(min(500,len(df))),x=cd["x"],y=cd["y"],color=cc,color_discrete_sequence=P,opacity=0.6,title=cd.get("title",""))
            f.update_layout(**L); return f
    except: pass
    return None

def fest_ins(m):
    try:
        mn=datetime.strptime(m,"%Y-%m").strftime("%B")
        f=FESTIVALS.get(mn,[])
        if f: return f"🎉 {mn} mein {', '.join(f)} — peak demand expected!"
    except: pass
    return None

def pg_login():
    st.markdown("""<style>[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#0D1B2A,#1E3A5F,#0D1B2A);}[data-testid="stHeader"]{background:transparent;}</style>""",unsafe_allow_html=True)
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown('<div style="text-align:center;padding:2rem 0 1.5rem;"><div style="font-size:3.5rem;">📊</div><div style="font-size:2rem;font-weight:800;color:white;">InsightFlow AI</div><div style="color:rgba(255,255,255,0.5);font-size:0.85rem;">Lucknow Ki Data Analytics Agency</div></div>',unsafe_allow_html=True)
        st.markdown('<div style="background:white;border-radius:20px;padding:2rem;box-shadow:0 32px 80px rgba(0,0,0,0.4);">',unsafe_allow_html=True)
        st.markdown("#### 🔐 Login Karo")
        lang=st.radio("",["English","हिंदी"],horizontal=True)
        un=st.text_input("Username" if lang=="English" else "यूजरनेम",placeholder="username daalo")
        pw=st.text_input("Password" if lang=="English" else "पासवर्ड",type="password",placeholder="••••••••")
        if st.button("Login →" if lang=="English" else "लॉगिन →",use_container_width=True,type="primary"):
            if not un or not pw: st.error("Dono fields bharo")
            else:
                r=do_login(un,pw)
                if r["ok"]: ss(r); st.session_state["page"]="dashboard"; st.rerun()
                else: st.error(r["msg"])
        st.markdown("</div>",unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;color:rgba(255,255,255,0.3);font-size:0.75rem;margin-top:1rem;">Default: <b style="color:rgba(255,255,255,0.5)">admin</b> / <b style="color:rgba(255,255,255,0.5)">admin@123</b></div>',unsafe_allow_html=True)

def sidebar():
    u=gu(); rc2="#EF4444" if ia() else "#3B82F6"
    with st.sidebar:
        st.markdown(f'<div style="padding:1rem;background:rgba(255,255,255,0.05);border-radius:10px;margin-bottom:1rem;"><div style="font-size:0.65rem;color:#475569;font-weight:700;">LOGGED IN</div><div style="font-size:1rem;font-weight:700;color:#F1F5F9;margin-top:4px;">{u["name"]}</div><span style="font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:8px;background:{rc2}33;color:{rc2};">{u["role"].upper()}</span>{"<div style=font-size:0.75rem;color:#64748B;margin-top:4px;>"+str(u.get("cn") or "")+"</div>" if u.get("cn") else ""}</div>',unsafe_allow_html=True)
        pages={"upload":"📁 Upload","clients":"👥 Clients","users":"🔐 Users","festival":"🎉 Festivals"} if ia() else {"dashboard":"📈 Dashboard"}
        if ic() and st.session_state.get("df") is None: pages={"upload":"📁 Upload",**pages}
        for pk,pl in pages.items():
            t="primary" if st.session_state.get("page")==pk else "secondary"
            if st.button(pl,key=f"n_{pk}",use_container_width=True,type=t): st.session_state["page"]=pk; st.rerun()
        if ia():
            st.markdown('<hr style="border-color:rgba(255,255,255,0.08);margin:0.8rem 0;">',unsafe_allow_html=True)
            cls=get_clients()
            if cls:
                ops={"— Select —":None}; ops.update({f"{c['name']}":c for c in cls})
                sel=st.selectbox("Client",list(ops.keys()),label_visibility="collapsed")
                if ops[sel]: st.session_state["ac"]=ops[sel]
        if st.session_state.get("df") is not None:
            df=st.session_state["df"]
            st.markdown(f'<div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);border-radius:8px;padding:0.7rem;margin-top:0.5rem;"><div style="font-size:0.65rem;font-weight:700;color:#10B981;">DATA ✓</div><div style="font-size:0.78rem;color:#CBD5E1;">{df.shape[0]:,} rows · {df.shape[1]} cols</div></div>',unsafe_allow_html=True)
        st.markdown('<hr style="border-color:rgba(255,255,255,0.08);margin:0.8rem 0;">',unsafe_allow_html=True)
        if st.button("🚪 Logout",use_container_width=True): lo(); st.rerun()

def pg_upload():
    ac=st.session_state.get("ac",{}) or {}; cn=ac.get("name","") or (gu().get("cn") or "Client")
    st.markdown(f'<div class="hero"><h1>📊 InsightFlow AI</h1><p>Koi bhi data upload karo — AI analyze karega · {cn} · Lucknow</p></div>',unsafe_allow_html=True)
    c1,c2=st.columns([3,2])
    with c1:
        st.subheader("📁 Data Upload Karo")
        up=st.file_uploader("CSV ya Excel",type=["csv","xlsx","xls"],label_visibility="collapsed")
        use_ai=st.checkbox("🤖 Claude AI Insights")
        ak=""
        if use_ai: ak=st.text_input("Anthropic API Key",type="password",placeholder="sk-ant-...")
        if up:
            with st.spinner("🔄 Analyze ho raha hai..."):
                df_raw=pd.read_csv(up,on_bad_lines="skip") if up.name.endswith(".csv") else pd.read_excel(up)
                df,cr=clean(df_raw.copy()); cols=classify(df); m,ch=metrics(df,cols); ins=insights(df,m,cols)
                if "_m" in df.columns:
                    for mo in df["_m"].unique()[:3]:
                        fi=fest_ins(mo)
                        if fi: ins.insert(0,("i",fi))
                st.session_state.update({"df":df,"cols":cols,"metrics":m,"charts":ch,"insights":ins,"cr":cr})
                if use_ai and ak:
                    with st.spinner("🤖 Claude analyze kar raha hai..."):
                        try:
                            import anthropic
                            ns="\n".join([f"  {c}: sum={df[c].sum():,.1f}, avg={df[c].mean():,.1f}" for c in cols["num"][:5]])
                            cs="\n".join([f"  {c}: {dict(df[c].value_counts().head(3))}" for c in cols["cat"][:4]])
                            prompt=f"You are InsightFlow AI for {cn} in Lucknow India.\nData: {df.shape[0]} rows, columns: {', '.join(df.columns.tolist())}\nNumerics:\n{ns}\nCategories:\n{cs}\nGive 6 specific business insights with numbers. Use Indian context Rs lakh crore. Include Lucknow market context. Use emojis. 1-2 sentences each."
                            ac2=anthropic.Anthropic(api_key=ak)
                            msg=ac2.messages.create(model="claude-sonnet-4-20250514",max_tokens=800,messages=[{"role":"user","content":prompt}])
                            st.session_state["ai"]=msg.content[0].text
                        except Exception as e: st.session_state["ai"]=f"Error: {e}"
            sc=cr["score"]; col="#10B981" if sc>=80 else "#F59E0B" if sc>=60 else "#EF4444"
            lbl="Excellent" if sc>=85 else "Good" if sc>=70 else "Fair" if sc>=50 else "Fix Needed"
            st.markdown(f'<div style="background:white;border:2px solid {col};border-radius:12px;padding:1rem 1.5rem;margin:1rem 0;display:flex;align-items:center;gap:1.5rem;"><div style="text-align:center;min-width:60px;"><div style="font-size:2.2rem;font-weight:800;color:{col};">{sc}</div><div style="font-size:0.6rem;color:#9CA3AF;">QUALITY</div></div><div><div style="font-weight:700;color:#1F2937;">{lbl}</div><div style="font-size:0.78rem;color:#6B7280;">{df.shape[0]:,} rows · {len(cols["num"])} numeric · {len(cols["cat"])} categorical</div></div></div>',unsafe_allow_html=True)
            for f in cr["fixes"][:5]: st.success(f,icon=None)
            for w in cr["warns"]: st.warning(w,icon=None)
            if st.button("📈 Dashboard Dekho →",type="primary",use_container_width=True): st.session_state["page"]="dashboard"; st.rerun()
    with c2:
        st.subheader("🏭 Kaunsa Data Chalega?")
        for icon,name,color,hint in [("🏥","Hospital","#EF4444","Patient, revenue, department"),("🎓","School/Coaching","#3B82F6","Student, marks, attendance, fee"),("🛒","Shop/E-Commerce","#F59E0B","Orders, product, amount"),("🚚","Transport","#16A34A","Shipment, route, cost"),("🍽️","Restaurant","#F97316","Sales, items, daily revenue"),("🏠","Real Estate","#8B5CF6","Leads, property, price"),("💊","Pharmacy","#EC4899","Medicine, stock, sales"),("📦","Koi bhi data","#06B6D4","CSV/Excel — AI samjhega!")]:
            st.markdown(f'<div style="background:white;border:1px solid #E4EAF1;border-left:4px solid {color};border-radius:10px;padding:0.7rem 1rem;margin:0.3rem 0;"><b>{icon} {name}</b><div style="font-size:0.73rem;color:#9CA3AF;">{hint}</div></div>',unsafe_allow_html=True)

def pg_dashboard():
    if st.session_state.get("df") is None:
        st.info("Pehle data upload karo.")
        if st.button("→ Upload"): st.session_state["page"]="upload"; st.rerun()
        return
    df=st.session_state["df"]; cols=st.session_state["cols"]; m=st.session_state["metrics"]; ch=st.session_state["charts"]; ins=st.session_state["insights"]
    ac=st.session_state.get("ac",{}) or {}; cn=ac.get("name","") or (gu().get("cn") or "Client")
    st.markdown(f'<div class="hero"><h1>📈 Analytics Dashboard</h1><p>{cn} · {m["total"]:,} records · Lucknow</p></div>',unsafe_allow_html=True)
    ncs=cols["num"][:4]
    if ncs:
        kcs=st.columns(len(ncs))
        for i,col in enumerate(ncs):
            l=col.replace("_"," ").title(); tot=df[col].sum(); fmt=f"₹{tot/1e6:.2f}L" if tot>1e5 else f"{tot:,.1f}"
            with kcs[i]: st.markdown(f'<div class="kpi"><div class="kpi-l">Total {l}</div><div class="kpi-v">{fmt}</div><div class="kpi-s">avg: {df[col].mean():,.1f}</div></div>',unsafe_allow_html=True)
    if cols["cat"]:
        cs=st.columns(min(4,len(cols["cat"])))
        for i,col in enumerate(cols["cat"][:4]):
            with cs[i]: st.metric(col.replace("_"," ").title(),f"{df[col].value_counts().idxmax()}")
    t1,t2,t3,t4=st.tabs(["📈 Trends","📊 Charts","💡 Insights","📋 Data"])
    with t1:
        tc={k:v for k,v in ch.items() if v.get("t")=="line"}
        if not tc: st.info("Date column nahi mila — trends ke liye date column chahiye.")
        else:
            it=list(tc.items())
            for i in range(0,len(it),2):
                cc=st.columns(2)
                for j,(k,cd) in enumerate(it[i:i+2]):
                    with cc[j]:
                        st.markdown(f'<div class="sec">{cd["title"]}</div>',unsafe_allow_html=True)
                        f=rc(cd,df)
                        if f: st.plotly_chart(f,use_container_width=True)
    with t2:
        dc={k:v for k,v in ch.items() if v.get("t") in ("pie","bar","hist") and not k.startswith("c_")}
        if dc:
            it=list(dc.items())
            for i in range(0,min(len(it),8),2):
                cc=st.columns(2)
                for j,(k,cd) in enumerate(it[i:i+2]):
                    with cc[j]:
                        f=rc(cd,df)
                        if f: st.plotly_chart(f,use_container_width=True)
        cx={k:v for k,v in ch.items() if k.startswith("c_")}
        if cx:
            st.markdown('<div class="sec">📊 Category × Numbers</div>',unsafe_allow_html=True)
            it=list(cx.items())
            for i in range(0,min(len(it),4),2):
                cc=st.columns(2)
                for j,(k,cd) in enumerate(it[i:i+2]):
                    with cc[j]:
                        f=rc(cd,df)
                        if f: st.plotly_chart(f,use_container_width=True)
        if len(cols["num"])>=2:
            st.markdown('<div class="sec">🔗 Correlation</div>',unsafe_allow_html=True)
            cr2=df[cols["num"]].corr()
            f=px.imshow(cr2,text_auto=".2f",aspect="auto",color_continuous_scale=["#EF4444","white","#2D6A9F"],zmin=-1,zmax=1)
            f.update_layout(height=350,margin=dict(l=5,r=5,t=35,b=5)); st.plotly_chart(f,use_container_width=True)
    with t3:
        cm={"g":"ig","w":"iw","d":"id","i":"ii"}
        for tp,txt in ins: st.markdown(f'<div class="ins {cm.get(tp,"ii")}">{txt}</div>',unsafe_allow_html=True)
        if ai:=st.session_state.get("ai"):
            st.markdown("---"); st.markdown("### 🤖 Claude AI Analysis")
            st.markdown(f'<div class="ins ii">{ai.replace(chr(10),"<br>")}</div>',unsafe_allow_html=True)
        zc=next((c for c in cols["cat"] if any(z in c for z in ["city","zone","area","location"])),None)
        if zc:
            st.markdown("---"); st.markdown("### 📍 Lucknow Area Analysis")
            zd=df[zc].value_counts().reset_index(); zd.columns=["Area","Count"]
            f=px.bar(zd,x="Count",y="Area",orientation="h",color_discrete_sequence=["#2D6A9F"])
            f.update_layout(height=300,plot_bgcolor="white",paper_bgcolor="white",margin=dict(l=5,r=5,t=10,b=5)); st.plotly_chart(f,use_container_width=True)
    with t4:
        st.dataframe(df.head(500),use_container_width=True)
        c1,c2=st.columns(2)
        with c1: st.download_button("⬇️ CSV",df.to_csv(index=False).encode(),"data.csv","text/csv",use_container_width=True)
        with c2:
            try:
                buf=io.BytesIO()
                with pd.ExcelWriter(buf,engine="xlsxwriter") as w:
                    df.to_excel(w,index=False)
                st.download_button("⬇️ Excel",buf.getvalue(),"report.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
            except: pass

def pg_clients():
    st.subheader("👥 Clients — Lucknow")
    with st.expander("➕ Add Client"):
        with st.form("ac"):
            c1,c2=st.columns(2)
            with c1: nm=st.text_input("Name *"); ind=st.selectbox("Industry",["hospital","education","ecommerce","logistics","restaurant","real_estate","pharmacy","other"])
            with c2: em=st.text_input("Email"); city=st.selectbox("Area",ZONES)
            if st.form_submit_button("✅ Add") and nm: add_client(nm,ind,em,city); st.success(f"✅ '{nm}' added!"); st.rerun()
    icons={"hospital":"🏥","education":"🎓","ecommerce":"🛒","logistics":"🚚","restaurant":"🍽️","real_estate":"🏠","pharmacy":"💊","other":"📊"}
    for c in get_clients():
        c1,c2,c3=st.columns([4,3,2])
        with c1: st.markdown(f"**{icons.get(c['industry'],'📊')} {c['name']}** · `{c['industry']}` · 📍{c.get('city','Lucknow')}")
        with c2: st.caption(c.get("email") or "—")
        with c3:
            if st.button("Load",key=f"l_{c['id']}"): st.session_state["ac"]=c; st.session_state["page"]="upload"; st.rerun()
        st.markdown("<hr style='margin:0.3rem 0;border-color:#F0F3F8;'>",unsafe_allow_html=True)

def pg_users():
    st.subheader("🔐 Users")
    cls=get_clients()
    with st.expander("➕ Add User"):
        with st.form("au"):
            c1,c2=st.columns(2)
            with c1: un=st.text_input("Username *"); pw=st.text_input("Password *",type="password"); fn=st.text_input("Full Name")
            with c2:
                role=st.selectbox("Role",["client","admin"]); em=st.text_input("Email"); cid=None
                if role=="client" and cls:
                    ops={f"{c['name']}":c["id"] for c in cls}; sel=st.selectbox("Client",list(ops.keys())); cid=ops[sel]
            if st.form_submit_button("✅ Create"):
                r=create_user(un,pw,role,cid,fn,em)
                if r["ok"]: st.success(r["msg"]); st.rerun()
                else: st.error(r["msg"])
    st.markdown("---")
    us=get_users(); src=st.text_input("🔍 Search",placeholder="username...",label_visibility="collapsed")
    if src: us=[u for u in us if src.lower() in u["username"].lower()]
    rc3={"admin":"#EF4444","client":"#3B82F6"}
    for u in us:
        c1,c2,c3,c4,c5=st.columns([3,2,2,1,1])
        with c1: st.markdown(f'<b>@{u["username"]}</b> <span style="font-size:0.65rem;padding:2px 7px;border-radius:8px;background:{rc3.get(u["role"],"#888")}22;color:{rc3.get(u["role"],"#888")};">{u["role"].upper()}</span><br><span style="font-size:0.78rem;color:#666;">{u.get("full_name") or "—"}</span>',unsafe_allow_html=True)
        with c2: st.caption(u.get("cn") or "Admin")
        with c3: st.caption(f"{'🟢' if u['is_active'] else '🔴'} {str(u.get('last_login') or 'Never')[:10]}")
        with c4:
            with st.popover("🔑"):
                np=st.text_input("New pw",type="password",key=f"np_{u['id']}")
                if st.button("Update",key=f"up_{u['id']}"):
                    if upw(u["id"],np): st.success("✅")
                    else: st.error("Min 6 chars")
        with c5:
            if u["role"]!="admin":
                if st.button("⏸" if u["is_active"] else "▶",key=f"t_{u['id']}"): tog(u["id"]); st.rerun()
        st.markdown("<hr style='margin:0.3rem 0;border-color:#F0F3F8;'>",unsafe_allow_html=True)

def pg_festival():
    st.markdown('<div class="hero"><h1>🎉 Festival Calendar — Lucknow 2026</h1><p>Festivals ke hisaab se business plan karo</p></div>',unsafe_allow_html=True)
    months=["January","February","March","April","May","June","July","August","September","October","November","December"]
    cs=st.columns(3)
    for i,mo in enumerate(months):
        fs=FESTIVALS.get(mo,[])
        with cs[i%3]:
            col="#EF4444" if fs else "#E4EAF1"
            st.markdown(f'<div style="background:white;border:1px solid {col};border-left:4px solid {col};border-radius:12px;padding:1rem;margin:0.4rem 0;"><div style="font-weight:700;">{mo}</div>{"".join([f"<div style=font-size:0.8rem;color:#6B7280;>🎉 {f}</div>" for f in fs]) if fs else "<div style=font-size:0.8rem;color:#CBD5E1;>—</div>"}</div>',unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 💡 Business Tips")
    for ev,tip in [("Diwali (Oct-Nov)","🪔 Gift hampers, electronics, clothing — 30-50% sales boost. Stock 2 months pehle."),("Eid (March-April)","🌙 Clothing, sweets — Hazratganj aur Chowk mein 40%+ spike."),("Navratri (Oct)","🌺 Organic products, puja items — 9 din ka celebration."),("Back to School (Jun-Jul)","📚 Stationery, uniforms — coaching institutes full capacity.")]:
        st.markdown(f'<div class="ins ii"><b>{ev}</b><br>{tip}</div>',unsafe_allow_html=True)

init_db()
for k,v in {"page":"login","df":None,"ac":None}.items():
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
