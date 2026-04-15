import streamlit as st
import pandas as pd


def get_data_summary(df, kpis, industry):
    summary = f"Industry: {industry}\n"
    summary += f"Total Records: {len(df):,}\n"
    summary += f"Columns: {', '.join(df.columns.tolist())}\n\n"
    summary += "=== KEY METRICS ===\n"
    for k, v in kpis.items():
        if v is not None:
            summary += f"{k}: {v}\n"
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if num_cols:
        summary += "\n=== NUMERIC STATS ===\n"
        desc = df[num_cols[:8]].describe().round(2)
        summary += desc.to_string()
    cat_cols = [c for c in df.columns if df[c].dtype == object and df[c].nunique() <= 20]
    if cat_cols:
        summary += "\n\n=== CATEGORIES ===\n"
        for col in cat_cols[:5]:
            vc = df[col].value_counts().head(5)
            summary += f"\n{col}:\n"
            for val, cnt in vc.items():
                summary += f"  {val}: {cnt} ({cnt/len(df)*100:.1f}%)\n"
    return summary


def ask_ai(question, data_summary, chat_history, api_key, api_type, industry, client_name):
    system_prompt = f"""You are InsightFlow AI, a smart data analyst for {client_name} in Lucknow, India.
You have access to their {industry} business data.

DATA SUMMARY:
{data_summary}

Rules:
- Answer questions based on this specific data only
- Use Indian currency format (Rs, lakh, crore)
- Be concise - under 150 words
- Use emojis where appropriate
- Give actionable business advice"""

    messages = []
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    if api_type == "groq":
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}] + messages,
            max_tokens=400
        )
        return response.choices[0].message.content
    else:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text


def page_chatbot():
    u = st.session_state.get("insightflow_v2", {})
    df = st.session_state.get("df")
    kpis = st.session_state.get("kpis", {})
    industry = st.session_state.get("industry", "generic")
    ac = st.session_state.get("ac", {}) or {}
    client_name = ac.get("name", "") or (u.get("cn") or "Client")

    st.markdown(f"""
    <div class="hero">
        <div class="hero-badge">🤖 AI Chatbot</div>
        <div class="hero-title">Data Assistant</div>
        <div class="hero-sub">Apne data ke baare mein kuch bhi poochho · {client_name}</div>
    </div>
    """, unsafe_allow_html=True)

    if df is None:
        st.warning("Pehle data upload karo — phir chatbot use karo!")
        if st.button("Upload Data", type="primary", key="btn_chat_upload"):
            st.session_state["page"] = "upload"
            st.rerun()
        return

    # API Settings
    st.markdown('<div class="section-title">⚙️ AI SETTINGS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    with c1:
        default_key = st.secrets.get("GROQ_API_KEY", "") if api_type == "groq" else ""
        api_type = "groq" if "groq" in api_type else "claude"
    with c2:
        placeholder = "Auto-loaded!" if default_key else ("gsk_... Groq key" if api_type == "groq" else "sk-ant-...")
        api_key = st.text_input("API Key", value=default_key, type="password", placeholder=placeholder, key="chat_api_key")

    if not api_key:
        st.info("💡 API key daalo — Groq free hai! console.groq.com pe jaake banao.")
        st.markdown('<div class="section-title">💬 SAMPLE QUESTIONS</div>', unsafe_allow_html=True)
        samples = {
            "hospital": ["Revenue kitna hai?", "Top department?", "Critical patients %?", "Avg treatment cost?"],
            "ecommerce": ["Net revenue?", "Top category?", "Return rate?", "Top city?"],
            "logistics": ["Delivery rate?", "Avg transit days?", "Fuel cost %?", "Top route?"],
            "education": ["Placement rate?", "Avg CGPA?", "Low attendance count?", "Top company?"],
            "generic": ["Key insights?", "Best metric?", "Trends?"]
        }
        for q in samples.get(industry, samples["generic"]):
            st.markdown(f'<div class="insight-card ins-info">💬 {q}</div>', unsafe_allow_html=True)
        return

    # Init chat
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    if "data_summary" not in st.session_state:
        st.session_state["data_summary"] = get_data_summary(df, kpis, industry)

    # Display chat
    st.markdown('<div class="section-title">💬 CONVERSATION</div>', unsafe_allow_html=True)

    if not st.session_state["chat_history"]:
        st.markdown(f"""
        <div style="background:#0D2818;border:1px solid #1A4731;border-radius:10px;padding:1rem;margin:0.5rem 0;">
            <div style="color:#3FB950;font-weight:600;">🤖 InsightFlow AI</div>
            <div style="color:#8B949E;margin-top:0.3rem;">
                Namaste! Main aapke <b style="color:#E6EDF3;">{industry}</b> data ka analyst hoon.<br>
                <b style="color:#E6EDF3;">{len(df):,} records</b> analyze kar chuka hoon.<br>
                Koi bhi sawaal poochho!
            </div>
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f"""
            <div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:0.8rem 1rem;margin:0.4rem 0;margin-left:2rem;">
                <div style="color:#388BFD;font-weight:600;font-size:0.8rem;">YOU</div>
                <div style="color:#E6EDF3;margin-top:0.2rem;">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:#0D1F3C;border:1px solid #1E3A5C;border-radius:10px;padding:0.8rem 1rem;margin:0.4rem 0;margin-right:2rem;">
                <div style="color:#3FB950;font-weight:600;font-size:0.8rem;">🤖 AI</div>
                <div style="color:#E6EDF3;margin-top:0.2rem;">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True)

    # Quick questions
    st.markdown('<div class="section-title">⚡ QUICK QUESTIONS</div>', unsafe_allow_html=True)
    quick = {
        "hospital": ["Revenue kitna?", "Top department?", "Critical %?"],
        "ecommerce": ["Net revenue?", "Top category?", "Return rate?"],
        "logistics": ["Delivery rate?", "Avg transit?", "Top route?"],
        "education": ["Placement %?", "Avg CGPA?", "Low attendance?"],
        "generic": ["Key insights?", "Best metric?", "Improvements?"]
    }
    qs = quick.get(industry, quick["generic"])
    qcols = st.columns(len(qs))
    for i, q in enumerate(qs):
        with qcols[i]:
            if st.button(q, key=f"qbtn_{i}", use_container_width=True):
                st.session_state["pending_q"] = q

    # Input
    col_inp, col_btn = st.columns([5, 1])
    with col_inp:
        user_input = st.text_input("Sawaal", placeholder="Jaise: Revenue kitna tha is mahine?",
                                   key="chat_input", label_visibility="collapsed")
    with col_btn:
        send = st.button("Send", type="primary", use_container_width=True, key="btn_send_chat")

    if "pending_q" in st.session_state:
        user_input = st.session_state.pop("pending_q")
        send = True

    if send and user_input:
        with st.spinner("🤖 Soch raha hoon..."):
            try:
                response = ask_ai(user_input, st.session_state["data_summary"],
                                  st.session_state["chat_history"], api_key, api_type,
                                  industry, client_name)
                st.session_state["chat_history"].append({"role": "user", "content": user_input})
                st.session_state["chat_history"].append({"role": "assistant", "content": response})
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)[:150]}")

    if st.session_state["chat_history"]:
        if st.button("🗑️ Clear Chat", key="btn_clr"):
            st.session_state["chat_history"] = []
            st.rerun()
