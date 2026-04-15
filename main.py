import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
from datetime import datetime

from auth import (init_db, is_logged_in, get_user, is_admin, is_client,
                  set_session, do_logout, login, create_user, get_clients,
                  get_users, add_client, upw, toggle_user)
from pipeline import detect_industry, clean_data, process_hospital, process_ecommerce, process_logistics, process_education, process_generic
from dashboard import COLORS, DARK_LAYOUT, render_chart, render_multivariate
from portal import page_entry
from reports import generate_pdf_report
from chatbot import page_chatbot

st.set_page_config(
    page_title="InsightFlow AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*, html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif !important; }

/* Hide keyboard double arrow icon */
span[data-testid="stIconMaterial"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }

/* App background */
[data-testid="stAppViewContainer"] { background: #0A0F1E; }
[data-testid="stHeader"] { background: transparent; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1117 0%, #0D1B2A 100%) !important;
    border-right: 1px solid #1E2D3D !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div { color: #8B949E !important; }

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton > button {
    background: #161B22 !important;
    border: 1px solid #30363D !important;
    color: #C9D1D9 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #21262D !important;
    border-color: #388BFD !important;
    color: #E6EDF3 !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1F6FEB, #388BFD) !important;
    border-color: #1F6FEB !important;
    color: white !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #161B22;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    color: #8B949E !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
    background: #21262D !important;
    color: #E6EDF3 !important;
}

/* Metrics */
div[data-testid="stMetric"] {
    background: #161B22;
    border: 1px solid #21262D;
    border-radius: 12px;
    padding: 1rem;
}
div[data-testid="stMetric"] label { color: #8B949E !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #E6EDF3 !important; }

/* Dataframe */
.stDataFrame { background: #161B22 !important; }

/* File uploader */
[data-testid="stFileUploader"] {
    background: #161B22;
    border: 2px dashed #30363D;
    border-radius: 12px;
    padding: 1rem;
}
[data-testid="stFileUploaderDropzone"] {
    background: #161B22 !important;
}
[data-testid="stFileUploader"] button {
    background: #21262D !important;
    border: 1px solid #30363D !important;
    color: #E6EDF3 !important;
    border-radius: 6px !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: #161B22;
    border: 1px solid #21262D;
    border-radius: 10px;
}

/* Form */
[data-testid="stForm"] {
    background: #161B22;
    border: 1px solid #21262D;
    border-radius: 12px;
    padding: 1rem;
}

/* Custom classes */
.kpi-card {
    background: #161B22;
    border: 1px solid #21262D;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, border-color 0.2s;
}
.kpi-card:hover { transform: translateY(-2px); border-color: #388BFD; }
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: var(--accent, #388BFD);
}
.kpi-label { font-size: 0.7rem; font-weight: 600; color: #8B949E; text-transform: uppercase; letter-spacing: 1.2px; }
.kpi-value { font-size: 1.8rem; font-weight: 800; color: #E6EDF3; margin-top: 0.3rem; line-height: 1.1; }
.kpi-sub { font-size: 0.75rem; color: #6E7681; margin-top: 0.3rem; }

.hero {
    background: linear-gradient(135deg, #0D1117 0%, #0D1B2A 60%, #0D1F3C 100%);
    border: 1px solid #1E2D3D;
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero::after {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px; height: 300px;
    background: radial-gradient(circle, #1F6FEB22 0%, transparent 70%);
    pointer-events: none;
}
.hero-title { font-size: 1.9rem; font-weight: 800; color: #E6EDF3; margin: 0; }
.hero-sub { color: #8B949E; margin: 0.4rem 0 0; font-size: 0.9rem; }
.hero-badge {
    display: inline-block;
    background: #1F6FEB22;
    color: #388BFD;
    border: 1px solid #1F6FEB44;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-bottom: 0.7rem;
}

.section-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: #8B949E;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin: 1.2rem 0 0.7rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #21262D;
}

.insight-card {
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin: 0.4rem 0;
    font-size: 0.88rem;
    line-height: 1.7;
    border: 1px solid;
}
.ins-good   { background: #0D2818; border-color: #1A4731; color: #3FB950; }
.ins-warn   { background: #2D1F00; border-color: #4D3A00; color: #D29922; }
.ins-danger { background: #2D0C0C; border-color: #4D1515; color: #F85149; }
.ins-info   { background: #0D1F3C; border-color: #1E3A5C; color: #58A6FF; }

.login-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}
</style>
""", unsafe_allow_html=True)

def page_login():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: radial-gradient(ellipse at top, #0D1F3C 0%, #0A0F1E 60%); }
    [data-testid="stHeader"] { background: transparent; }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("""
        <div style="text-align:center; padding: 3rem 0 2rem;">
            <div style="font-size: 3.5rem;">📊</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: #E6EDF3; margin-top: 0.5rem;">InsightFlow AI</div>
            <div style="color: #8B949E; font-size: 0.9rem; margin-top: 0.3rem;">Data Analytics Platform · Lucknow</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<p style="color: #E6EDF3; font-weight: 600; font-size: 1rem; margin-bottom: 1.2rem;">🔐 Sign In</p>', unsafe_allow_html=True)
        un = st.text_input("Username", placeholder="Enter username", label_visibility="collapsed")
        pw = st.text_input("Password", type="password", placeholder="Enter password", label_visibility="collapsed")
        if st.button("Sign In →", use_container_width=True, type="primary"):
            if not un or not pw:
                st.error("Please fill both fields")
            else:
                r = login(un, pw)
                if r["ok"]:
                    set_session(r)
                    st.session_state["page"] = "upload"
                    st.rerun()
                else:
                    st.error(r["msg"])
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#6E7681; font-size:0.75rem; margin-top:1rem;">Default: <b style="color:#8B949E">admin</b> / <b style="color:#8B949E">admin@123</b></p>', unsafe_allow_html=True)


def render_sidebar():
    u = get_user()
    role_color = "#F85149" if is_admin() else "#388BFD"
    cn = u.get("cn") or ""

    with st.sidebar:
        # User info
        cn_html = f"<div style='font-size:0.75rem;color:#6E7681;margin-top:4px;'>{cn}</div>" if cn else ""
        st.markdown(f"""
        <div style="padding:1rem; background:#161B22; border-radius:10px; margin-bottom:1rem; border:1px solid #21262D;">
            <div style="font-size:0.65rem; color:#6E7681; font-weight:600; letter-spacing:1px;">LOGGED IN</div>
            <div style="font-size:0.95rem; font-weight:700; color:#E6EDF3; margin-top:4px;">{u["name"]}</div>
            <span style="font-size:0.65rem; font-weight:700; padding:2px 8px; border-radius:6px; background:{role_color}22; color:{role_color};">{u["role"].upper()}</span>
            {cn_html}
        </div>
        """, unsafe_allow_html=True)

        # Navigation
        if is_admin():
            pages = {"upload": "📁 Upload", "entry": "✏️ Data Entry", "chatbot": "🤖 AI Chatbot", "clients": "👥 Clients", "users": "🔐 Users", "festival": "🎉 Festivals"}
        else:
            if st.session_state.get("df") is not None:
                pages = {"dashboard": "📈 Dashboard", "entry": "✏️ Data Entry", "chatbot": "🤖 AI Chatbot", "profile": "👤 Profile"}
            else:
                pages = {"upload": "📁  Upload Data", "entry": "✏️  Data Entry"}
            # Auto redirect client to dashboard if data loaded
            if st.session_state.get("df") is not None and st.session_state.get("page") == "upload":
                st.session_state["page"] = "dashboard"

        for i, (pk, pl) in enumerate(pages.items()):
            t = "primary" if st.session_state.get("page") == pk else "secondary"
            if st.button(pl, key=f"sbtn_{i}_{pk}", use_container_width=True, type=t):
                st.session_state["page"] = pk
                st.rerun()

        # Admin: client switcher
        if is_admin():
            st.markdown('<hr style="border-color:#21262D; margin:1rem 0;">', unsafe_allow_html=True)
            clients = get_clients()
            if clients:
                st.markdown('<div style="font-size:0.65rem; color:#6E7681; font-weight:600; letter-spacing:1px; margin-bottom:0.5rem;">ACTIVE CLIENT</div>', unsafe_allow_html=True)
                opts = {"— Select Client —": None}
                opts.update({c["name"]: c for c in clients})
                sel = st.selectbox("", list(opts.keys()), label_visibility="collapsed")
                if opts.get(sel):
                    st.session_state["ac"] = opts[sel]

        # Data status
        if st.session_state.get("df") is not None:
            ind = st.session_state.get("industry", "")
            icons = {"hospital": "🏥", "ecommerce": "🛒", "logistics": "🚚", "education": "🎓", "generic": "📊"}
            st.markdown(f"""
            <div style="background:#0D2818; border:1px solid #1A4731; border-radius:8px; padding:0.8rem; margin-top:0.5rem;">
                <div style="font-size:0.65rem; font-weight:600; color:#3FB950;">{icons.get(ind,'📊')} DATA LOADED</div>
                <div style="font-size:0.78rem; color:#6E7681; margin-top:3px;">{st.session_state['df'].shape[0]:,} rows · {ind.upper()}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<hr style="border-color:#21262D; margin:1rem 0;">', unsafe_allow_html=True)
        if st.button("🚪  Sign Out", key="sbtn_signout", use_container_width=True):
            do_logout(); st.rerun()
        st.caption("InsightFlow AI v3.0")


def page_upload():
    ac = st.session_state.get("ac", {}) or {}
    cn = ac.get("name", "") or (get_user().get("cn") or "")

    # Client industry restriction
    client_industry = None
    if is_client() and get_user().get("client_id"):
        c = get_db()
        cl = c.execute("SELECT industry FROM clients WHERE id=?", (get_user()["client_id"],)).fetchone()
        c.close()
        if cl: client_industry = cl["industry"]

    st.markdown(f"""
    <div class="hero">
        <div class="hero-badge">📍 Lucknow · Data Analytics</div>
        <div class="hero-title">📊 Upload & Analyze</div>
        <div class="hero-sub">Upload your {client_industry.title() if client_industry else ""} data — CSV or Excel{f" · {cn}" if cn else ""}</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown('<div class="section-title">📁 FILE UPLOAD</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("", type=["csv", "xlsx", "xls"], label_visibility="collapsed")
        use_ai = st.checkbox("🤖 Claude AI Insights", value=False)
        api_key = ""
        if use_ai:
            api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...", label_visibility="collapsed")

        if uploaded:
            with st.spinner("🔄 Processing..."):
                try:
                    if uploaded.name.endswith(".csv"):
                        df_raw = pd.read_csv(uploaded, on_bad_lines="skip")
                    else:
                        df_raw = pd.read_excel(uploaded)
                except Exception as e:
                    st.error(f"File read error: {e}")
                    st.stop()

                df, clean_rep = clean_data(df_raw.copy())
                industry = detect_industry(df)

                # If client, force their industry
                if client_industry:
                    if industry != client_industry:
                        st.warning(f"⚠️ Wrong data! Aapko sirf {client_industry.title()} data upload karna chahiye. Analysis {client_industry.title()} mode mein hoga.")
                    industry = client_industry

                if industry == "hospital":   kpis, charts, insights = process_hospital(df)
                elif industry == "ecommerce": kpis, charts, insights = process_ecommerce(df)
                elif industry == "logistics": kpis, charts, insights = process_logistics(df)
                elif industry == "education": kpis, charts, insights = process_education(df)
                else:                         kpis, charts, insights = process_generic(df)

                st.session_state.update({
                    "df": df, "kpis": kpis, "charts": charts,
                    "insights": insights, "industry": industry
                })
                # Save to Supabase if client logged in
                if is_client() and get_user().get("client_id"):
                    save_client_data(get_user()["client_id"], industry, uploaded.name, df)

                # Claude AI
                if use_ai and api_key:
                    with st.spinner("🤖 Claude analyzing..."):
                        try:
                            import anthropic
                            kpi_summary = "\n".join([f"  {k}: {v}" for k, v in kpis.items()])
                            prompt = f"""You are InsightFlow AI data analyst for a {industry} business in Lucknow, India.

Key Metrics:
{kpi_summary}

Dataset: {df.shape[0]} rows, columns: {', '.join(df.columns.tolist())}

Provide 6 specific, data-driven business insights. Include:
- What is working well
- What needs attention  
- Specific actionable recommendations
- Lucknow market context where relevant

Use Indian currency context (Rs, lakh, crore). Use emojis. Keep each insight to 1-2 sentences."""
                            client = anthropic.Anthropic(api_key=api_key)
                            msg = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=800,
                                messages=[{"role": "user", "content": prompt}]
                            )
                            st.session_state["ai_insight"] = msg.content[0].text
                        except Exception as e:
                            st.session_state["ai_insight"] = f"AI error: {e}"

            # Quality score
            score = clean_rep["score"]
            sc = "#3FB950" if score >= 80 else "#D29922" if score >= 60 else "#F85149"
            label = "Excellent" if score >= 85 else "Good" if score >= 70 else "Fair" if score >= 50 else "Needs Attention"
            ind_labels = {"hospital": "🏥 Hospital", "ecommerce": "🛒 E-Commerce", "logistics": "🚚 Logistics", "education": "🎓 Education", "generic": "📊 Generic"}

            st.success(f"✅ **{ind_labels.get(industry, industry)}** detected | {df.shape[0]:,} rows processed")
            st.markdown(f"""
            <div style="background:#161B22; border:1px solid {sc}44; border-radius:12px; padding:1rem 1.5rem; margin:0.8rem 0; display:flex; align-items:center; gap:1.5rem;">
                <div style="text-align:center; min-width:60px;">
                    <div style="font-size:2.2rem; font-weight:800; color:{sc};">{score}</div>
                    <div style="font-size:0.6rem; color:#6E7681; font-weight:600;">QUALITY</div>
                </div>
                <div>
                    <div style="font-weight:700; color:#E6EDF3;">{label} Data Quality</div>
                    <div style="font-size:0.78rem; color:#6E7681; margin-top:2px;">{df.shape[0]:,} rows · {len(df.columns)} columns · {len([c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])])} numeric</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            for f in clean_rep["fixes"][:4]:
                st.info(f, icon=None)

            if st.button("📈 View Dashboard →", type="primary", use_container_width=True):
                st.session_state["page"] = "dashboard"
                st.rerun()

    with col2:
        st.markdown('<div class="section-title">🏭 SUPPORTED INDUSTRIES</div>', unsafe_allow_html=True)
        industries = [
            ("🏥", "Hospital", "#F85149", "Patient_ID, Treatment_Cost, Disease, Department"),
            ("🛒", "E-Commerce", "#D29922", "Order_ID, Product_Price, Quantity, Discount"),
            ("🚚", "Logistics", "#3FB950", "Shipment_ID, Shipment_Cost, Distance_KM, Vehicle_Type"),
            ("🎓", "Education", "#388BFD", "Student_ID, CGPA, Attendance_Percentage, Placement_Status"),
            ("📦", "Any Data", "#BC8CFF", "Any CSV or Excel — AI will analyze it"),
        ]
        for icon, name, color, hint in industries:
            st.markdown(f"""
            <div style="background:#161B22; border:1px solid #21262D; border-left:3px solid {color}; border-radius:8px; padding:0.7rem 1rem; margin:0.3rem 0;">
                <b style="color:#E6EDF3;">{icon} {name}</b>
                <div style="font-size:0.72rem; color:#6E7681; margin-top:2px;">{hint}</div>
            </div>
            """, unsafe_allow_html=True)


def page_dashboard():
    if st.session_state.get("df") is None:
        st.markdown("""
        <div style="text-align:center; padding:4rem; color:#8B949E;">
            <div style="font-size:3rem;">📂</div>
            <div style="font-size:1.1rem; color:#E6EDF3; margin-top:1rem;">No data loaded</div>
            <div style="margin-top:0.5rem;">Please upload data first</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("→ Upload Data", type="primary"):
            st.session_state["page"] = "upload"; st.rerun()
        return

    df       = st.session_state["df"]
    kpis     = st.session_state["kpis"]
    charts   = st.session_state["charts"]
    insights = st.session_state["insights"]
    industry = st.session_state.get("industry", "generic")
    ac       = st.session_state.get("ac", {}) or {}
    cn       = ac.get("name", "") or (get_user().get("cn") or "Client")

    ind_labels = {
        "hospital":  "🏥 Hospital Analytics",
        "ecommerce": "🛒 E-Commerce Analytics",
        "logistics": "🚚 Logistics Analytics",
        "education": "🎓 Education Analytics",
        "generic":   "📊 Data Analytics"
    }

    st.markdown(f"""
    <div class="hero">
        <div class="hero-badge">📊 Live Dashboard</div>
        <div class="hero-title">{ind_labels.get(industry, "📊 Analytics")}</div>
        <div class="hero-sub">{cn} · {df.shape[0]:,} records analyzed</div>
    </div>
    """, unsafe_allow_html=True)

    # KPI Cards
    kpi_items = [(k, v) for k, v in kpis.items() if v is not None and isinstance(v, (int, float))][:6]
    if kpi_items:
        accent_colors = ["#388BFD", "#3FB950", "#D29922", "#F85149", "#BC8CFF", "#F78166"]
        cols = st.columns(min(3, len(kpi_items)))
        for i, (k, v) in enumerate(kpi_items):
            label = k
            ac_color = accent_colors[i % len(accent_colors)]

            # Format value
            if any(x in k.lower() for x in ["revenue", "cost", "fee", "fuel"]):
                if v >= 1e7:    fmt = f"₹{v/1e7:.2f}Cr"
                elif v >= 1e5:  fmt = f"₹{v/1e5:.1f}L"
                elif v >= 1e3:  fmt = f"₹{v/1e3:.0f}K"
                else:           fmt = f"₹{v:,.0f}"
            elif "low attendance" in k.lower() or "placed students" in k.lower() or "students with" in k.lower() or "count" in k.lower():
                fmt = f"{int(v):,}"
            elif any(x in k.lower() for x in ["rate", "%", "discount", "pct", "avg attendance", "placement rate", "scholarship", "internship", "backlog %", "hostel"]):
                fmt = f"{v:.1f}%"
            elif "days" in k.lower() or "cgpa" in k.lower() or "lpa" in k.lower():
                fmt = f"{v:.1f}"
            elif isinstance(v, float) and v < 100:
                fmt = f"{v:.2f}"
            else:
                fmt = f"{int(v):,}"

            with cols[i % 3]:
                st.markdown(f"""
                <div class="kpi-card" style="--accent:{ac_color};">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{fmt}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("")

    # String KPIs as metrics
    str_kpis = [(k, v) for k, v in kpis.items() if isinstance(v, str)]
    if str_kpis:
        mcols = st.columns(min(4, len(str_kpis)))
        for i, (k, v) in enumerate(str_kpis[:4]):
            with mcols[i]:
                st.metric(k, v)

    # TABS
    tab_names = ["📈 Trends", "📊 Charts", "🔬 Bivariate", "🧮 Multivariate", "💡 Insights", "📋 Data"]
    tabs = st.tabs(tab_names)

    # ── Trends ──────────────────────────────────────────────
    with tabs[0]:
        line_charts = {k: v for k, v in charts.items() if v.get("type") == "line"}
        if not line_charts:
            st.markdown('<div style="text-align:center; padding:3rem; color:#6E7681;"><div style="font-size:2rem;">📅</div><div style="margin-top:0.5rem;">No date column detected for trends</div></div>', unsafe_allow_html=True)
        else:
            items = list(line_charts.items())
            for i in range(0, len(items), 2):
                c1, c2 = st.columns(2)
                for j, (k, cd) in enumerate(items[i:i+2]):
                    with (c1 if j == 0 else c2):
                        fig = render_chart(cd, df)
                        if fig: st.plotly_chart(fig, use_container_width=True)

    # ── Charts ──────────────────────────────────────────────
    with tabs[1]:
        other_charts = {k: v for k, v in charts.items() if v.get("type") in ("pie", "bar_h")}
        if other_charts:
            items = list(other_charts.items())
            for i in range(0, min(len(items), 10), 2):
                c1, c2 = st.columns(2)
                for j, (k, cd) in enumerate(items[i:i+2]):
                    with (c1 if j == 0 else c2):
                        fig = render_chart(cd, df)
                        if fig: st.plotly_chart(fig, use_container_width=True)

    # ── Bivariate ───────────────────────────────────────────
    with tabs[2]:
        st.markdown('<div class="section-title">🔬 BIVARIATE ANALYSIS</div>', unsafe_allow_html=True)

        # Industry-specific scatter plots
        scatter_charts = {k: v for k, v in charts.items() if v.get("type") == "scatter"}
        if scatter_charts:
            items = list(scatter_charts.items())
            for i in range(0, len(items), 2):
                c1, c2 = st.columns(2)
                for j, (k, cd) in enumerate(items[i:i+2]):
                    with (c1 if j == 0 else c2):
                        fig = render_chart(cd, df, height=350)
                        if fig: st.plotly_chart(fig, use_container_width=True)

        # Custom scatter
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique() > 5]
        cat_cols = [c for c in df.columns if df[c].dtype == object and 2 <= df[c].nunique() <= 15]

        if len(num_cols) >= 2:
            st.markdown('<div class="section-title">🎯 CUSTOM SCATTER PLOT</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1: x = st.selectbox("X-axis", num_cols, key="sc_x")
            with c2: y = st.selectbox("Y-axis", num_cols, index=1 if len(num_cols) > 1 else 0, key="sc_y")
            with c3: color = st.selectbox("Color by", ["None"] + cat_cols, key="sc_c")
            sample = df.sample(min(500, len(df)), random_state=42)
            fig = px.scatter(sample, x=x, y=y,
                             color=color if color != "None" else None,
                             color_discrete_sequence=COLORS, opacity=0.7)
            fig.update_layout(plot_bgcolor="#161B22", paper_bgcolor="#161B22",
                              font=dict(color="#8B949E"), height=400,
                              margin=dict(l=10, r=10, t=40, b=10),
                              xaxis=dict(gridcolor="#21262D"), yaxis=dict(gridcolor="#21262D"),
                              legend=dict(font=dict(color="#8B949E")))
            st.plotly_chart(fig, use_container_width=True)

        # Bar comparison
        if num_cols and cat_cols:
            st.markdown('<div class="section-title">📊 CATEGORY VS NUMERIC (Bar)</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1: cn2 = st.selectbox("Category", cat_cols, key="bar_cat")
            with c2: nn = st.selectbox("Numeric", num_cols, key="bar_num")
            agg = st.radio("Aggregation", ["Mean", "Sum", "Median", "Max"], horizontal=True, key="bar_agg")
            agg_fn = {"Mean": "mean", "Sum": "sum", "Median": "median", "Max": "max"}[agg]
            d = df.groupby(cn2)[nn].agg(agg_fn).sort_values(ascending=False).head(15).reset_index()
            d.columns = [cn2, nn]
            fig = px.bar(d, x=nn, y=cn2, orientation="h", color_discrete_sequence=["#388BFD"],
                         title=f"{agg} of {nn} by {cn2}")
            fig.update_layout(plot_bgcolor="#161B22", paper_bgcolor="#161B22",
                              font=dict(color="#8B949E"), height=400,
                              margin=dict(l=10, r=10, t=40, b=10),
                              yaxis=dict(categoryorder="total ascending", gridcolor="#21262D"),
                              xaxis=dict(gridcolor="#21262D"), title_font=dict(color="#E6EDF3"))
            st.plotly_chart(fig, use_container_width=True)

    # ── Multivariate ─────────────────────────────────────────
    with tabs[3]:
        render_multivariate(df)

    # ── Insights ─────────────────────────────────────────────
    with tabs[4]:
        st.markdown('<div class="section-title">💡 AUTO-GENERATED INSIGHTS</div>', unsafe_allow_html=True)
        cls_map = {"good": "ins-good", "warn": "ins-warn", "danger": "ins-danger", "info": "ins-info"}
        for tp, txt in insights:
            st.markdown(f'<div class="insight-card {cls_map.get(tp, "ins-info")}">{txt}</div>', unsafe_allow_html=True)

        if ai := st.session_state.get("ai_insight"):
            st.markdown('<div class="section-title" style="margin-top:1.5rem;">🤖 CLAUDE AI ANALYSIS</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="insight-card ins-info">{ai.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

        # Statistical summary
        st.markdown('<div class="section-title">📊 STATISTICAL SUMMARY</div>', unsafe_allow_html=True)
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if num_cols:
            st.dataframe(df[num_cols].describe().round(2), use_container_width=True)

    # ── Raw Data ─────────────────────────────────────────────
    with tabs[5]:
        st.markdown(f'<div class="section-title">📋 RAW DATA — {len(df):,} ROWS</div>', unsafe_allow_html=True)

        # Filter
        search_col = st.selectbox("Filter by column", ["— No filter —"] + list(df.columns), label_visibility="collapsed")
        df_show = df
        if search_col != "— No filter —":
            search_val = st.text_input(f"Search in '{search_col}'", label_visibility="collapsed")
            if search_val:
                df_show = df[df[search_col].astype(str).str.contains(search_val, case=False, na=False)]
                st.caption(f"{len(df_show):,} rows match")

        st.dataframe(df_show.head(500), use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode(), "insightflow_data.csv", "text/csv", use_container_width=True)
        with c2:
            try:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
                    df.to_excel(w, index=False, sheet_name="Data")
                    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                    if num_cols:
                        df[num_cols].describe().round(2).to_excel(w, sheet_name="Statistics")
                st.download_button("⬇️ Download Excel", buf.getvalue(), "insightflow_report.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
            except:
                pass

        st.markdown('<div class="section-title">📄 PDF REPORT</div>', unsafe_allow_html=True)
        if st.button("📄 Generate PDF Report", type="primary", use_container_width=True, key="btn_pdf"):
            with st.spinner("PDF ban raha hai..."):
                pdf = generate_pdf_report(cn, industry, kpis, insights, df)
                if pdf:
                    st.download_button(
                        "⬇️ Download PDF Report",
                        pdf,
                        f"{cn}_InsightFlow_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                        "application/pdf",
                        use_container_width=True,
                        key="btn_dl_pdf"
                    )
                    st.success("✅ PDF ready!")
                else:
                    st.error("PDF generate nahi hua.")


def page_clients():
    st.markdown('<div class="hero"><div class="hero-badge">👥 Management</div><div class="hero-title">Client Management</div><div class="hero-sub">Add and manage clients</div></div>', unsafe_allow_html=True)

    with st.expander("➕ Add New Client"):
        with st.form("frm_add_client"):
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                nm  = st.text_input("Client Name *")
                ind = st.selectbox("Industry", ["hospital", "ecommerce", "logistics", "education", "other"])
            with r1c2:
                em   = st.text_input("Email")
                city = st.selectbox("Area", ["Hazratganj", "Gomtinagar", "Alambagh", "Chowk", "Aliganj", "Indira Nagar", "Other"])
            if st.form_submit_button("Add Client", use_container_width=True) and nm:
                add_client(nm, ind, em, city)
                st.success(f"Added!")
                st.rerun()

    icons = {"hospital": "Hospital", "ecommerce": "Shop", "logistics": "Logistics", "education": "College", "other": "Other"}
    for cl in get_clients():
        ra, rb, rc, rd = st.columns([4, 3, 1, 1])
        with ra:
            st.markdown(f'<div style="color:#E6EDF3;font-weight:600;">{cl["name"]}</div><div style="font-size:0.78rem;color:#6E7681;">{cl.get("city","Lucknow")} · {cl["industry"]}</div>', unsafe_allow_html=True)
        with rb:
            st.caption(cl.get("email") or "—")
        with rc:
            if st.button("Load", key=f"ld_{cl['id']}", use_container_width=True):
                st.session_state["ac"] = cl
                st.session_state["page"] = "upload"
                st.rerun()
        with rd:
            if st.button("Del", key=f"dl_{cl['id']}", help="Delete"):
                delete_client(cl["id"])
                xdb.commit()
                xdb.close()
                st.rerun()
        st.markdown('<hr style="border-color:#21262D;margin:0.3rem 0;">', unsafe_allow_html=True)

def page_users():
    st.markdown('<div class="hero"><div class="hero-badge">🔐 Access Control</div><div class="hero-title">User Management</div><div class="hero-sub">Create and manage user accounts</div></div>', unsafe_allow_html=True)

    clients = get_clients()
    with st.expander("➕ Add New User"):
        with st.form("frm_add_user"):
            c1, c2 = st.columns(2)
            with c1:
                un   = st.text_input("Username *")
                pw   = st.text_input("Password *", type="password")
                fn   = st.text_input("Full Name")
            with c2:
                role = st.selectbox("Role", ["client", "admin"])
                em   = st.text_input("Email")
                cid  = None
                if role == "client" and clients:
                    opts = {f"{c['name']} ({c['industry']})": c["id"] for c in clients}
                    sel  = st.selectbox("Link to Client *", list(opts.keys()))
                    cid  = opts[sel]
            if st.form_submit_button("✅ Create User", use_container_width=True):
                r = create_user(un, pw, role, cid, fn, em)
                if r["ok"]: st.success(r["msg"]); st.rerun()
                else: st.error(r["msg"])

    st.markdown('<div class="section-title">ALL USERS</div>', unsafe_allow_html=True)
    search = st.text_input("🔍 Search users", placeholder="Search by username...", label_visibility="collapsed")
    users = get_users()
    if search:
        users = [u for u in users if search.lower() in u["username"].lower() or search.lower() in (u.get("full_name") or "").lower()]

    rc = {"admin": "#F85149", "client": "#388BFD"}
    for u in users:
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1, 1])
        with c1:
            st.markdown(f'<div style="color:#E6EDF3; font-weight:600;">@{u["username"]} <span style="font-size:0.65rem; padding:2px 7px; border-radius:6px; background:{rc.get(u["role"],"#888")}22; color:{rc.get(u["role"],"#888")};">{u["role"].upper()}</span></div><div style="font-size:0.78rem; color:#6E7681;">{u.get("full_name") or "—"}</div>', unsafe_allow_html=True)
        with c2:
            st.caption(u.get("cn") or "Admin")
        with c3:
            st.caption(f"{'🟢' if u['is_active'] else '🔴'} {str(u.get('last_login') or 'Never')[:10]}")
        with c4:
            with st.popover("🔑"):
                npw = st.text_input("New password", type="password", key=f"npw_{u['id']}")
                if st.button("Update", key=f"upd_{u['id']}"):
                    if upw(u["id"], npw): st.success("✅ Updated!")
                    else: st.error("Min 6 chars")
        with c5:
            if u["role"] != "admin":
                lbl = "⏸" if u["is_active"] else "▶"
                if st.button(lbl, key=f"tog_{u['id']}", help="Enable/Disable"):
                    toggle_user(u["id"]); st.rerun()
        st.markdown('<hr style="border-color:#21262D; margin:0.3rem 0;">', unsafe_allow_html=True)






def page_profile():
    u = get_user()
    st.markdown(f"""
    <div class="hero">
        <div class="hero-badge">👤 Profile</div>
        <div class="hero-title">My Profile</div>
        <div class="hero-sub">Apni account settings manage karo</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">🔐 CHANGE PASSWORD</div>', unsafe_allow_html=True)
    
    with st.form("frm_change_pw"):
        old_pw  = st.text_input("Current Password", type="password", key="old_pw")
        new_pw  = st.text_input("New Password (min 6 chars)", type="password", key="new_pw")
        conf_pw = st.text_input("Confirm New Password", type="password", key="conf_pw")
        
        if st.form_submit_button("Update Password", use_container_width=True, type="primary"):
            if not old_pw or not new_pw or not conf_pw:
                st.error("Sab fields bharo!")
            elif new_pw != conf_pw:
                st.error("New password aur confirm password match nahi karte!")
            elif len(new_pw) < 6:
                st.error("Password minimum 6 characters ka hona chahiye!")
            else:
                # Verify old password
                c = get_db()
                user = c.execute("SELECT * FROM users WHERE id=?", (u["id"],)).fetchone()
                c.close()
                if user and verify_pw(old_pw, user["password_hash"], user["salt"]):
                    if upw(u["id"], new_pw):
                        st.success("✅ Password successfully change ho gaya!")
                    else:
                        st.error("Password change nahi hua — try again!")
                else:
                    st.error("❌ Current password galat hai!")

    st.markdown('<div class="section-title">👤 ACCOUNT INFO</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Username", u["username"])
        st.metric("Role", u["role"].title())
    with col2:
        st.metric("Full Name", u["name"] or "—")
        st.metric("Client", u.get("cn") or "Admin")

def page_festival():
    st.markdown('<div class="hero"><div class="hero-badge">🎉 Lucknow Calendar</div><div class="hero-title">Festival & Business Calendar 2026</div><div class="hero-sub">Plan your business strategy around Lucknow festivals</div></div>', unsafe_allow_html=True)

    FESTIVALS = {
        "January":   ["🪁 Makar Sankranti (Jan 14)", "🇮🇳 Republic Day (Jan 26)"],
        "February":  ["🌸 Basant Panchami", "💝 Valentine's Day"],
        "March":     ["🎨 Holi", "🌙 Eid ul-Fitr"],
        "April":     ["🪔 Ram Navami", "🐣 Easter"],
        "May":       ["👩 Mother's Day"],
        "June":      ["📚 Board Results Season"],
        "July":      ["🎓 Admission Season Starts"],
        "August":    ["🇮🇳 Independence Day (Aug 15)", "🪢 Raksha Bandhan", "🎪 Janmashtami"],
        "September": ["🌺 Ganesh Chaturthi"],
        "October":   ["🌺 Navratri", "🏹 Dussehra", "🪔 Diwali"],
        "November":  ["🪔 Diwali (if late)", "🌊 Chhath Puja", "🎭 Lucknow Mahotsav"],
        "December":  ["🎄 Christmas", "🎆 New Year Prep"],
    }

    months = list(FESTIVALS.keys())
    cols = st.columns(3)
    for i, month in enumerate(months):
        festivals = FESTIVALS[month]
        with cols[i % 3]:
            color = "#D29922" if festivals else "#21262D"
            items_html = "".join([f'<div style="font-size:0.8rem; color:#8B949E; margin-top:4px;">{f}</div>' for f in festivals]) or '<div style="font-size:0.8rem; color:#6E7681;">—</div>'
            st.markdown(f"""
            <div style="background:#161B22; border:1px solid {color}; border-radius:10px; padding:1rem; margin:0.3rem 0;">
                <div style="font-weight:700; color:#E6EDF3;">{month}</div>
                {items_html}
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">💡 BUSINESS STRATEGY TIPS</div>', unsafe_allow_html=True)
    tips = [
        ("🪔 Diwali (Oct-Nov)", "Gift hampers, electronics, clothing — expect 30-50% sales boost. Stock inventory 2 months in advance. Offer EMI options.", "#D29922"),
        ("🌙 Eid (March-April)", "Clothing, sweets, gifts — Hazratganj and Chowk see 40%+ spike. Muslim-majority areas key. Stock kurtas, sherwanis, sweets.", "#388BFD"),
        ("🌺 Navratri (Oct)", "Organic/satvik products, puja items, traditional clothing — 9-day celebration. Women's ethnic wear peaks.", "#3FB950"),
        ("🎭 Lucknow Mahotsav (Nov)", "Tourism spike — hospitality, food, handicrafts, chikankari peak. Great for local brand visibility.", "#BC8CFF"),
        ("📚 Back to School (Jun-Jul)", "Stationery, uniforms, books, bags — coaching institutes run at full capacity. Parents spend heavily.", "#F78166"),
        ("🎓 Admission Season (Jul-Aug)", "Education sector peak — colleges, coaching classes, hostels. Fees collection highest.", "#56D364"),
    ]
    for event, tip, color in tips:
        st.markdown(f"""
        <div class="insight-card ins-info" style="border-color:{color}44; background:{color}11;">
            <b style="color:{color};">{event}</b><br>
            <span style="color:#8B949E;">{tip}</span>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════
init_db()

# Initialize session state
defaults = {"page": "login", "df": None, "kpis": {}, "charts": {}, "insights": [], "industry": None, "ac": None, "ai_insight": None}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Login gate
if not is_logged_in():
    page_login()
    st.stop()

# Render sidebar
render_sidebar()

# Route pages
page = st.session_state.get("page", "upload")

# Clients can't access admin pages
if is_client() and page in ("clients", "users", "festival"):
    page = "dashboard"
    st.session_state["page"] = page

if   page == "upload":    page_upload()
elif page == "dashboard": page_dashboard()
elif page == "entry":     page_entry()
elif page == "clients":   page_clients()
elif page == "users":     page_users()
elif page == "chatbot":   page_chatbot()
elif page == "profile":   page_profile()
elif page == "festival":  page_festival()
else:                     page_upload()