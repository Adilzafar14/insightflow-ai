import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from auth import (get_user, is_admin, is_client, get_db,
                  save_entry, get_entries, get_clients)


def entries_to_df(entries):
    if not entries:
        return None
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
        <div class="hero-sub">{client_name} · {industry.title()} · Enter karo aur save karo</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["✏️ Naya Entry", "📋 Previous Entries"])

    with tab1:
        entry_date = st.date_input("Date", value=datetime.now().date(), key="entry_date")
        st.markdown('<div class="section-title">📝 DATA FILL KARO</div>', unsafe_allow_html=True)

        data = {}

        if industry == "hospital":
            c1, c2 = st.columns(2)
            with c1:
                data["Total Patients"]      = st.number_input("Total Patients", min_value=0, value=0)
                data["OPD Patients"]        = st.number_input("OPD Patients", min_value=0, value=0)
                data["IPD Patients"]        = st.number_input("IPD Patients", min_value=0, value=0)
                data["Emergency Cases"]     = st.number_input("Emergency Cases", min_value=0, value=0)
            with c2:
                data["Total Revenue (Rs)"]      = st.number_input("Total Revenue (Rs)", min_value=0, value=0)
                data["Cash Revenue (Rs)"]       = st.number_input("Cash Revenue (Rs)", min_value=0, value=0)
                data["Insurance Revenue (Rs)"]  = st.number_input("Insurance Revenue (Rs)", min_value=0, value=0)
                data["UPI Revenue (Rs)"]        = st.number_input("UPI Revenue (Rs)", min_value=0, value=0)
            c1, c2 = st.columns(2)
            with c1:
                data["Surgeries"]   = st.number_input("Surgeries", min_value=0, value=0)
                data["Discharges"]  = st.number_input("Discharges", min_value=0, value=0)
            with c2:
                data["Admissions"]      = st.number_input("New Admissions", min_value=0, value=0)
                data["Top Department"]  = st.selectbox("Busiest Department",
                    ["Cardiology","Neurology","Orthopedic","Emergency","General Medicine","ICU","Pediatrics","Gynecology"])
            data["Notes"] = st.text_area("Notes", placeholder="Koi observation...")

        elif industry == "ecommerce":
            c1, c2 = st.columns(2)
            with c1:
                data["Total Orders"]        = st.number_input("Total Orders", min_value=0, value=0)
                data["Delivered Orders"]    = st.number_input("Delivered", min_value=0, value=0)
                data["Cancelled Orders"]    = st.number_input("Cancelled/Returned", min_value=0, value=0)
                data["New Customers"]       = st.number_input("New Customers", min_value=0, value=0)
            with c2:
                data["Total Revenue (Rs)"]      = st.number_input("Total Revenue (Rs)", min_value=0, value=0)
                data["Online Revenue (Rs)"]     = st.number_input("Online Revenue (Rs)", min_value=0, value=0)
                data["COD Revenue (Rs)"]        = st.number_input("COD Revenue (Rs)", min_value=0, value=0)
                data["Avg Order Value (Rs)"]    = st.number_input("Avg Order Value (Rs)", min_value=0, value=0)
            data["Top Category"] = st.selectbox("Top Category",
                ["Electronics","Fashion","Grocery","Home Decor","Books","Beauty","Sports","Other"])
            data["Notes"] = st.text_area("Notes", placeholder="Sale, offers, issues...")

        elif industry == "logistics":
            c1, c2 = st.columns(2)
            with c1:
                data["Total Shipments"] = st.number_input("Total Shipments", min_value=0, value=0)
                data["Delivered"]       = st.number_input("Delivered", min_value=0, value=0)
                data["Delayed"]         = st.number_input("Delayed", min_value=0, value=0)
                data["Pending"]         = st.number_input("Pending", min_value=0, value=0)
            with c2:
                data["Total Revenue (Rs)"]  = st.number_input("Total Revenue (Rs)", min_value=0, value=0)
                data["Fuel Cost (Rs)"]      = st.number_input("Fuel Cost (Rs)", min_value=0, value=0)
                data["Total KM"]            = st.number_input("Total KM", min_value=0, value=0)
                data["Vehicles Used"]       = st.number_input("Vehicles Used", min_value=0, value=0)
            data["Top Route"]   = st.text_input("Busiest Route", placeholder="e.g. Lucknow to Delhi")
            data["Notes"]       = st.text_area("Notes", placeholder="Issues, weather, driver notes...")

        elif industry == "education":
            c1, c2 = st.columns(2)
            with c1:
                data["Students Present"]    = st.number_input("Students Present", min_value=0, value=0)
                data["Total Students"]      = st.number_input("Total Students", min_value=0, value=0)
                data["New Admissions"]      = st.number_input("New Admissions", min_value=0, value=0)
                data["Fee Collected (Rs)"]  = st.number_input("Fee Collected (Rs)", min_value=0, value=0)
            with c2:
                data["Classes Conducted"]   = st.number_input("Classes Conducted", min_value=0, value=0)
                data["Tests Conducted"]     = st.number_input("Tests Conducted", min_value=0, value=0)
                data["Placements Today"]    = st.number_input("Placements Today", min_value=0, value=0)
                data["Internship Offers"]   = st.number_input("Internship Offers", min_value=0, value=0)
            data["Department"]  = st.selectbox("Department", ["CSE","IT","ECE","ME","Civil","BBA","All"])
            data["Notes"]       = st.text_area("Notes", placeholder="Events, exams, activities...")

        else:
            st.info("Generic entry form")
            for field in ["Value 1", "Value 2", "Value 3"]:
                data[field] = st.number_input(field, min_value=0, value=0)

        st.markdown("")
        _, col, _ = st.columns([1, 2, 1])
        with col:
            if st.button("Save Entry", type="primary", use_container_width=True):
                if any(v not in (0, "", None) for k, v in data.items() if k not in ("Notes", "Top Department", "Top Category", "Top Route", "Department")):
                    save_entry(client_id, industry, str(entry_date), data, u["id"])
                    st.success(f"Entry saved for {entry_date}!")
                    st.balloons()
                else:
                    st.warning("Koi data enter karo pehle.")

    with tab2:
        st.markdown('<div class="section-title">RECENT ENTRIES</div>', unsafe_allow_html=True)
        entries = get_entries(client_id, industry, limit=30)

        if not entries:
            st.info("Abhi koi entry nahi hai.")
        else:
            df_e = entries_to_df(entries)
            if df_e is not None:
                st.dataframe(df_e, use_container_width=True)

                if len(entries) >= 2:
                    num_cols = [c for c in df_e.columns
                                if c not in ("Date", "Notes", "Top Department", "Top Category", "Top Route", "Department")]
                    if num_cols:
                        sel = st.selectbox("Trend dekhna hai", num_cols)
                        df_plot = df_e[["Date", sel]].copy()
                        df_plot[sel] = pd.to_numeric(df_plot[sel], errors="coerce")
                        df_plot.dropna(inplace=True)
                        if len(df_plot) > 0:
                            fig = go.Figure(go.Scatter(
                                x=df_plot["Date"], y=df_plot[sel],
                                fill="tozeroy",
                                fillcolor="rgba(56,139,253,0.08)",
                                line=dict(color="#388BFD", width=2.5),
                                mode="lines+markers",
                                marker=dict(size=8, color="#388BFD")
                            ))
                            fig.update_layout(
                                plot_bgcolor="#161B22", paper_bgcolor="#161B22",
                                font=dict(color="#8B949E"),
                                height=300, margin=dict(l=10, r=10, t=30, b=10),
                                xaxis=dict(gridcolor="#21262D"),
                                yaxis=dict(gridcolor="#21262D"),
                                title=dict(text=sel, font=dict(color="#E6EDF3"))
                            )
                            st.plotly_chart(fig, use_container_width=True)

                csv = df_e.to_csv(index=False).encode()
                st.download_button("Download CSV", csv, f"{client_name}_entries.csv", "text/csv")
                st.markdown("---")
                st.markdown("**🗑️ Entry Delete Karo:**")
                del_id = st.number_input("Entry ID", min_value=1, step=1, key="del_id")
                if st.button("Delete", key="btn_del", type="secondary"):
                    c = get_db()
                    c.execute("DELETE FROM entries WHERE id=? AND client_id=?", (int(del_id), client_id))
                    c.commit()
                    c.close()
                    st.success("Deleted!")
                    st.rerun()