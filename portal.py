import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from auth import get_user, is_admin, is_client, get_db, save_entry, get_entries

def entries_to_df(entries, industry):
    if not entries: return None
    rows = []
    for e in entries:
        row = {"Date": e["entry_date"]}
        row.update(e["data"])
        rows.append(row)
    return pd.DataFrame(rows)

def page_entry():
    u = get_user()
    ac = st.session_state.get("ac", {}) or {}
    
    # Determine client
    if is_admin():
        clients = get_clients()
        if not clients:
            st.warning("Pehle client add karo.")
            return
        if ac:
            client = ac
        else:
            st.info("Sidebar se client select karo.")
            return
    else:
        if not u.get("client_id"):
            st.error("Account client se linked nahi hai.")
            return
        c = get_db()
        cl = c.execute("SELECT * FROM clients WHERE id=?", (u["client_id"],)).fetchone()
        c.close()
        client = dict(cl) if cl else {}

    if not client:
        st.warning("Client select karo.")
        return

    industry = client.get("industry", "generic")
    client_id = client["id"]
    client_name = client["name"]

    ind_icons = {"hospital": "🏥", "ecommerce": "🛒", "logistics": "🚚", "education": "🎓"}
    icon = ind_icons.get(industry, "📊")

    st.markdown(f"""
    <div class="hero">
        <div class="hero-badge">{icon} Data Entry Portal</div>
        <div class="hero-title">Daily Data Entry</div>
        <div class="hero-sub">{client_name} · {industry.title()} · Enter karo aur dashboard update ho jayega</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["✏️ Naya Entry", "📋 Previous Entries"])

    with tab1:
        st.markdown('<div class="section-title">📅 ENTRY DETAILS</div>', unsafe_allow_html=True)
        entry_date = st.date_input("Date", value=datetime.now().date())

        st.markdown('<div class="section-title">📝 DATA FILL KARO</div>', unsafe_allow_html=True)

        data = {}

        if industry == "hospital":
            c1, c2 = st.columns(2)
            with c1:
                data["Total Patients"] = st.number_input("Aaj Total Patients", min_value=0, value=0)
                data["OPD Patients"] = st.number_input("OPD Patients", min_value=0, value=0)
                data["IPD Patients"] = st.number_input("IPD Patients", min_value=0, value=0)
                data["Emergency Cases"] = st.number_input("Emergency Cases", min_value=0, value=0)
            with c2:
                data["Total Revenue (Rs)"] = st.number_input("Total Revenue (₹)", min_value=0, value=0)
                data["Cash Revenue (Rs)"] = st.number_input("Cash Revenue (₹)", min_value=0, value=0)
                data["Insurance Revenue (Rs)"] = st.number_input("Insurance Revenue (₹)", min_value=0, value=0)
                data["UPI Revenue (Rs)"] = st.number_input("UPI Revenue (₹)", min_value=0, value=0)
            c1, c2 = st.columns(2)
            with c1:
                data["Surgeries"] = st.number_input("Surgeries Today", min_value=0, value=0)
                data["Discharges"] = st.number_input("Patient Discharges", min_value=0, value=0)
            with c2:
                data["Admissions"] = st.number_input("New Admissions", min_value=0, value=0)
                data["Top Department"] = st.selectbox("Busiest Department", ["Cardiology","Neurology","Orthopedic","Emergency","General Medicine","ICU","Pediatrics","Gynecology"])
            data["Notes"] = st.text_area("Notes (optional)", placeholder="Koi special observation...")

        elif industry == "ecommerce":
            c1, c2 = st.columns(2)
            with c1:
                data["Total Orders"] = st.number_input("Total Orders", min_value=0, value=0)
                data["Delivered Orders"] = st.number_input("Delivered Orders", min_value=0, value=0)
                data["Cancelled Orders"] = st.number_input("Cancelled/Returned", min_value=0, value=0)
                data["New Customers"] = st.number_input("New Customers", min_value=0, value=0)
            with c2:
                data["Total Revenue (Rs)"] = st.number_input("Total Revenue (₹)", min_value=0, value=0)
                data["Online Revenue (Rs)"] = st.number_input("Online Revenue (₹)", min_value=0, value=0)
                data["COD Revenue (Rs)"] = st.number_input("COD Revenue (₹)", min_value=0, value=0)
                data["Avg Order Value (Rs)"] = st.number_input("Avg Order Value (₹)", min_value=0, value=0)
            data["Top Category"] = st.selectbox("Top Selling Category", ["Electronics","Fashion","Grocery","Home Decor","Books","Beauty","Sports","Other"])
            data["Notes"] = st.text_area("Notes", placeholder="Sale, offers, issues...")

        elif industry == "logistics":
            c1, c2 = st.columns(2)
            with c1:
                data["Total Shipments"] = st.number_input("Total Shipments Today", min_value=0, value=0)
                data["Delivered"] = st.number_input("Delivered", min_value=0, value=0)
                data["Delayed"] = st.number_input("Delayed", min_value=0, value=0)
                data["Pending"] = st.number_input("Pending", min_value=0, value=0)
            with c2:
                data["Total Revenue (Rs)"] = st.number_input("Total Revenue (₹)", min_value=0, value=0)
                data["Fuel Cost (Rs)"] = st.number_input("Fuel Cost (₹)", min_value=0, value=0)
                data["Total KM"] = st.number_input("Total KM Covered", min_value=0, value=0)
                data["Vehicles Used"] = st.number_input("Vehicles Used", min_value=0, value=0)
            data["Top Route"] = st.text_input("Busiest Route Today", placeholder="e.g. Lucknow → Delhi")
            data["Notes"] = st.text_area("Notes", placeholder="Issues, weather, driver notes...")

        elif industry == "education":
            c1, c2 = st.columns(2)
            with c1:
                data["Students Present"] = st.number_input("Students Present", min_value=0, value=0)
                data["Total Students"] = st.number_input("Total Students", min_value=0, value=0)
                data["New Admissions"] = st.number_input("New Admissions Today", min_value=0, value=0)
                data["Fee Collected (Rs)"] = st.number_input("Fee Collected (₹)", min_value=0, value=0)
            with c2:
                data["Classes Conducted"] = st.number_input("Classes Conducted", min_value=0, value=0)
                data["Tests Conducted"] = st.number_input("Tests Conducted", min_value=0, value=0)
                data["Placements Today"] = st.number_input("Placements Today", min_value=0, value=0)
                data["Internship Offers"] = st.number_input("Internship Offers", min_value=0, value=0)
            data["Department"] = st.selectbox("Main Department", ["CSE","IT","ECE","ME","Civil","BBA","All"])
            data["Notes"] = st.text_area("Notes", placeholder="Events, exams, special activities...")

        else:
            # Generic entry
            st.info("Generic data entry form")
            cols_input = st.text_input("Fields (comma separated)", placeholder="Sales, Customers, Revenue")
            if cols_input:
                for field in [f.strip() for f in cols_input.split(",")]:
                    if field:
                        data[field] = st.number_input(field, min_value=0, value=0)

        st.markdown("")
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("💾 Entry Save Karo", type="primary", use_container_width=True):
                if any(v != 0 and v != "" for k, v in data.items() if k != "Notes"):
                    save_entry(client_id, industry, str(entry_date), data, u["id"])
                    st.success(f"✅ {entry_date} ki entry save ho gayi!")
                    st.balloons()
                else:
                    st.warning("Koi data enter karo pehle.")

    with tab2:
        st.markdown('<div class="section-title">📋 RECENT ENTRIES</div>', unsafe_allow_html=True)
        entries = get_entries(client_id, industry, limit=30)
        
        if not entries:
            st.info("Abhi tak koi entry nahi hai. Pehle entry karo.")
        else:
            # Show as table
            df_entries = entries_to_df(entries, industry)
            if df_entries is not None:
                st.dataframe(df_entries, use_container_width=True)
                
                # Quick charts from entries
                if len(entries) >= 3:
                    st.markdown('<div class="section-title">📈 ENTRY TRENDS</div>', unsafe_allow_html=True)
                    num_cols = [c for c in df_entries.columns if c != "Date" and c != "Notes" and c != "Top Department" and c != "Top Category" and c != "Top Route" and c != "Department"]
                    
                    if num_cols and "Date" in df_entries.columns:
                        sel_metric = st.selectbox("Metric dekhna hai", num_cols)
                        df_plot = df_entries[["Date", sel_metric]].copy()
                        df_plot[sel_metric] = pd.to_numeric(df_plot[sel_metric], errors="coerce")
                        df_plot = df_plot.dropna()
                        
                        if len(df_plot) > 0:
                            fig = go.Figure(go.Scatter(
                                x=df_plot["Date"], y=df_plot[sel_metric],
                                fill="tozeroy",
                                fillcolor="rgba(56,139,253,0.08)",
                                line=dict(color="#388BFD", width=2.5),
                                mode="lines+markers",
                                marker=dict(size=8, color="#388BFD")
                            ))
                            fig.update_layout(
                                plot_bgcolor="#161B22", paper_bgcolor="#161B22",
                                font=dict(color="#8B949E"),
                                height=300, margin=dict(l=10,r=10,t=30,b=10),
                                xaxis=dict(gridcolor="#21262D"),
                                yaxis=dict(gridcolor="#21262D"),
                                title=dict(text=sel_metric, font=dict(color="#E6EDF3"))
                            )
                            st.plotly_chart(fig, use_container_width=True)

                # Download
                csv = df_entries.to_csv(index=False).encode()
                st.download_button("⬇️ Download Entries CSV", csv, f"{client_name}_entries.csv", "text/csv")