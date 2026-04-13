import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import base64
import json
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


def ocr_extract(image_bytes, industry, api_key):
    """Use Claude Vision to extract data from bill/receipt image"""
    try:
        import anthropic
        
        industry_prompts = {
            "hospital": """Extract from this medical bill/receipt:
- Patient name
- Date
- Department
- Doctor name  
- Total amount (Rs)
- Payment mode (Cash/Card/UPI/Insurance)
- Diagnosis/Treatment if visible

Return ONLY valid JSON like:
{"date": "", "department": "", "total_amount": 0, "payment_mode": "", "notes": ""}""",

            "ecommerce": """Extract from this sales receipt/invoice:
- Date
- Items sold
- Total amount (Rs)
- Payment mode
- Customer info if visible

Return ONLY valid JSON like:
{"date": "", "total_revenue": 0, "total_orders": 1, "payment_mode": "", "top_category": "", "notes": ""}""",

            "logistics": """Extract from this shipping/delivery receipt:
- Date
- Origin and destination
- Weight/dimensions if visible
- Shipping cost (Rs)
- Delivery status

Return ONLY valid JSON like:
{"date": "", "total_revenue": 0, "total_shipments": 1, "top_route": "", "notes": ""}""",

            "education": """Extract from this fee receipt/document:
- Student name
- Date
- Fee amount (Rs)
- Course/Department
- Receipt number

Return ONLY valid JSON like:
{"date": "", "fee_collected": 0, "department": "", "new_admissions": 0, "notes": ""}""",

            "generic": """Extract key information from this receipt/bill:
- Date
- Total amount
- Description

Return ONLY valid JSON like:
{"date": "", "amount": 0, "description": ""}"""
        }

        prompt = industry_prompts.get(industry, industry_prompts["generic"])
        
        img_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img_b64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )
        
        response = msg.content[0].text.strip()
        # Clean JSON
        if "```" in response:
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()
        
        return json.loads(response)
    except Exception as e:
        return {"error": str(e)}


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

    industry = str(client.get("industry", "generic")).lower().strip()
    # Normalize industry names
    if industry not in ("hospital", "ecommerce", "logistics", "education"):
        industry = "generic"
    client_id = client["id"]
    client_name = client["name"]

    ind_icons = {"hospital": "🏥", "ecommerce": "🛒", "logistics": "🚚", "education": "🎓"}
    icon = ind_icons.get(industry, "📊")

    st.markdown(f"""
    <div class="hero">
        <div class="hero-badge">{icon} Data Entry Portal</div>
        <div class="hero-title">Daily Data Entry</div>
        <div class="hero-sub">{client_name} · {industry.title()} · Manual ya Photo se entry karo</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📸 Photo/Bill Upload", "✏️ Manual Entry", "📋 Previous Entries"])

    # ── TAB 1: OCR ──────────────────────────────────────────
    with tab1:
        st.markdown('<div class="section-title">📸 BILL / RECEIPT PHOTO UPLOAD</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background:#0D2818;border:1px solid #1A4731;border-radius:10px;padding:1rem;margin-bottom:1rem;">
            <div style="color:#3FB950;font-weight:600;">📱 Kaise Use Karein:</div>
            <div style="color:#8B949E;font-size:0.85rem;margin-top:0.5rem;">
                1. Bill ya receipt ki photo lo<br>
                2. Neeche upload karo<br>
                3. Claude AI automatically data read karega<br>
                4. Check karo aur save karo
            </div>
        </div>
        """, unsafe_allow_html=True)

        api_key = st.text_input("Claude API Key", type="password", 
                                placeholder="sk-ant-... (required for OCR)",
                                key="ocr_api_key")
        
        uploaded_img = st.file_uploader(
            "Bill/Receipt Photo Upload Karo",
            type=["jpg", "jpeg", "png"],
            key="ocr_image"
        )

        if uploaded_img and api_key:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.image(uploaded_img, caption="Uploaded Image", use_container_width=True)
            
            with col2:
                if st.button("🤖 Claude se Extract Karo", type="primary", use_container_width=True, key="btn_ocr"):
                    with st.spinner("Claude bill read kar raha hai..."):
                        img_bytes = uploaded_img.read()
                        result = ocr_extract(img_bytes, industry, api_key)
                        
                        if "error" in result:
                            st.error(f"Error: {result['error']}")
                        else:
                            st.session_state["ocr_result"] = result
                            st.success("✅ Data extract ho gaya!")

            # Show extracted data
            if "ocr_result" in st.session_state:
                result = st.session_state["ocr_result"]
                st.markdown('<div class="section-title">📋 EXTRACTED DATA — CHECK KARO</div>', unsafe_allow_html=True)
                
                # Editable fields
                edited_data = {}
                cols = st.columns(2)
                for i, (k, v) in enumerate(result.items()):
                    with cols[i % 2]:
                        if isinstance(v, (int, float)):
                            edited_data[k] = st.number_input(k, value=float(v), key=f"ocr_{k}")
                        else:
                            edited_data[k] = st.text_input(k, value=str(v) if v else "", key=f"ocr_{k}")

                entry_date = st.date_input("Date", value=datetime.now().date(), key="ocr_date")
                
                _, col, _ = st.columns([1, 2, 1])
                with col:
                    if st.button("💾 Save Entry", type="primary", use_container_width=True, key="btn_save_ocr"):
                        save_entry(client_id, industry, str(entry_date), edited_data, u["id"])
                        st.success(f"✅ Entry saved!")
                        st.session_state.pop("ocr_result", None)
                        st.balloons()
                        st.rerun()

        elif uploaded_img and not api_key:
            st.warning("⚠️ Claude API key daalo OCR ke liye.")
        
        st.markdown("""
        <div style="background:#161B22;border:1px solid #21262D;border-radius:8px;padding:0.8rem;margin-top:1rem;">
            <div style="color:#8B949E;font-size:0.8rem;">
                💡 <b style="color:#E6EDF3;">Tips:</b><br>
                • Achhi lighting mein photo lo<br>
                • Bill seedha rakho, teda nahi<br>
                • Poora bill frame mein aana chahiye<br>
                • Hindi aur English dono supported hain
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── TAB 2: MANUAL ENTRY ─────────────────────────────────
    with tab2:
        entry_date = st.date_input("Date", value=datetime.now().date(), key="manual_date")
        st.markdown('<div class="section-title">📝 DATA FILL KARO</div>', unsafe_allow_html=True)

        data = {}

        if industry == "hospital":
            c1, c2 = st.columns(2)
            with c1:
                data["Total Patients"]     = st.number_input("Total Patients", min_value=0, value=0, key="h1")
                data["OPD Patients"]       = st.number_input("OPD Patients", min_value=0, value=0, key="h2")
                data["IPD Patients"]       = st.number_input("IPD Patients", min_value=0, value=0, key="h3")
                data["Emergency Cases"]    = st.number_input("Emergency Cases", min_value=0, value=0, key="h4")
            with c2:
                data["Total Revenue (Rs)"]     = st.number_input("Total Revenue (Rs)", min_value=0, value=0, key="h5")
                data["Cash Revenue (Rs)"]      = st.number_input("Cash Revenue (Rs)", min_value=0, value=0, key="h6")
                data["Insurance Revenue (Rs)"] = st.number_input("Insurance Revenue (Rs)", min_value=0, value=0, key="h7")
                data["UPI Revenue (Rs)"]       = st.number_input("UPI Revenue (Rs)", min_value=0, value=0, key="h8")
            c1, c2 = st.columns(2)
            with c1:
                data["Surgeries"]  = st.number_input("Surgeries", min_value=0, value=0, key="h9")
                data["Discharges"] = st.number_input("Discharges", min_value=0, value=0, key="h10")
            with c2:
                data["Admissions"]     = st.number_input("New Admissions", min_value=0, value=0, key="h11")
                data["Top Department"] = st.selectbox("Busiest Department", ["Cardiology","Neurology","Orthopedic","Emergency","General Medicine","ICU","Pediatrics","Gynecology"], key="h12")
            data["Notes"] = st.text_area("Notes", placeholder="Koi observation...", key="h13")

        elif industry == "ecommerce":
            c1, c2 = st.columns(2)
            with c1:
                data["Total Orders"]     = st.number_input("Total Orders", min_value=0, value=0, key="e1")
                data["Delivered Orders"] = st.number_input("Delivered", min_value=0, value=0, key="e2")
                data["Cancelled Orders"] = st.number_input("Cancelled/Returned", min_value=0, value=0, key="e3")
                data["New Customers"]    = st.number_input("New Customers", min_value=0, value=0, key="e4")
            with c2:
                data["Total Revenue (Rs)"]  = st.number_input("Total Revenue (Rs)", min_value=0, value=0, key="e5")
                data["Online Revenue (Rs)"] = st.number_input("Online Revenue (Rs)", min_value=0, value=0, key="e6")
                data["COD Revenue (Rs)"]    = st.number_input("COD Revenue (Rs)", min_value=0, value=0, key="e7")
                data["Avg Order Value (Rs)"]= st.number_input("Avg Order Value (Rs)", min_value=0, value=0, key="e8")
            data["Top Category"] = st.selectbox("Top Category", ["Electronics","Fashion","Grocery","Home Decor","Books","Beauty","Sports","Other"], key="e9")
            data["Notes"] = st.text_area("Notes", placeholder="Sale, offers, issues...", key="e10")

        elif industry == "logistics":
            c1, c2 = st.columns(2)
            with c1:
                data["Total Shipments"] = st.number_input("Total Shipments", min_value=0, value=0, key="l1")
                data["Delivered"]       = st.number_input("Delivered", min_value=0, value=0, key="l2")
                data["Delayed"]         = st.number_input("Delayed", min_value=0, value=0, key="l3")
                data["Pending"]         = st.number_input("Pending", min_value=0, value=0, key="l4")
            with c2:
                data["Total Revenue (Rs)"] = st.number_input("Total Revenue (Rs)", min_value=0, value=0, key="l5")
                data["Fuel Cost (Rs)"]     = st.number_input("Fuel Cost (Rs)", min_value=0, value=0, key="l6")
                data["Total KM"]           = st.number_input("Total KM", min_value=0, value=0, key="l7")
                data["Vehicles Used"]      = st.number_input("Vehicles Used", min_value=0, value=0, key="l8")
            data["Top Route"] = st.text_input("Busiest Route", placeholder="e.g. Lucknow to Delhi", key="l9")
            data["Notes"]     = st.text_area("Notes", placeholder="Issues, weather...", key="l10")

        elif industry == "education":
            c1, c2 = st.columns(2)
            with c1:
                data["Students Present"]   = st.number_input("Students Present", min_value=0, value=0, key="ed1")
                data["Total Students"]     = st.number_input("Total Students", min_value=0, value=0, key="ed2")
                data["New Admissions"]     = st.number_input("New Admissions", min_value=0, value=0, key="ed3")
                data["Fee Collected (Rs)"] = st.number_input("Fee Collected (Rs)", min_value=0, value=0, key="ed4")
            with c2:
                data["Classes Conducted"]  = st.number_input("Classes Conducted", min_value=0, value=0, key="ed5")
                data["Tests Conducted"]    = st.number_input("Tests Conducted", min_value=0, value=0, key="ed6")
                data["Placements Today"]   = st.number_input("Placements Today", min_value=0, value=0, key="ed7")
                data["Internship Offers"]  = st.number_input("Internship Offers", min_value=0, value=0, key="ed8")
            data["Department"] = st.selectbox("Department", ["CSE","IT","ECE","ME","Civil","BBA","All"], key="ed9")
            data["Notes"]      = st.text_area("Notes", placeholder="Events, exams...", key="ed10")

        else:
            for i, field in enumerate(["Value 1", "Value 2", "Value 3"]):
                data[field] = st.number_input(field, min_value=0, value=0, key=f"g{i}")

        st.markdown("")
        _, col, _ = st.columns([1, 2, 1])
        with col:
            if st.button("💾 Save Entry", type="primary", use_container_width=True, key="btn_save_manual"):
                if any(v not in (0, "", None) for k, v in data.items() if k not in ("Notes","Top Department","Top Category","Top Route","Department")):
                    save_entry(client_id, industry, str(entry_date), data, u["id"])
                    st.success(f"✅ Entry saved for {entry_date}!")
                    st.balloons()
                else:
                    st.warning("Koi data enter karo pehle.")

    # ── TAB 3: PREVIOUS ENTRIES ──────────────────────────────
    with tab3:
        st.markdown('<div class="section-title">📋 RECENT ENTRIES</div>', unsafe_allow_html=True)
        entries = get_entries(client_id, industry, limit=30)

        if not entries:
            st.info("Abhi koi entry nahi hai.")
        else:
            df_e = entries_to_df(entries)
            if df_e is not None:
                st.dataframe(df_e, use_container_width=True)

                if len(entries) >= 2:
                    num_cols = [c for c in df_e.columns if c not in ("Date","Notes","Top Department","Top Category","Top Route","Department")]
                    if num_cols:
                        sel = st.selectbox("Trend dekhna hai", num_cols, key="trend_sel")
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
                                height=300, margin=dict(l=10,r=10,t=30,b=10),
                                xaxis=dict(gridcolor="#21262D"),
                                yaxis=dict(gridcolor="#21262D"),
                                title=dict(text=sel, font=dict(color="#E6EDF3"))
                            )
                            st.plotly_chart(fig, use_container_width=True)

                c1, c2 = st.columns(2)
                with c1:
                    csv = df_e.to_csv(index=False).encode()
                    st.download_button("⬇️ Download CSV", csv, f"{client_name}_entries.csv", "text/csv", key="dl_csv")
                with c2:
                    st.markdown("**🗑️ Entry Delete Karo:**")
                    entry_ids = [e["id"] for e in entries]
                    del_id = st.selectbox("Entry select karo", entry_ids, key="del_sel")
                    if st.button("🗑️ Delete", key="btn_del_entry", type="secondary"):
                        c = get_db()
                        c.execute("DELETE FROM entries WHERE id=? AND client_id=?", (int(del_id), client_id))
                        c.commit(); c.close()
                        st.success("Deleted!")
                        st.rerun()
