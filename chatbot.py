import streamlit as st
import pandas as pd
import json
from datetime import datetime


def get_data_summary(df, kpis, industry):
    """Create a detailed data summary for Claude"""
    summary = f"Industry: {industry}\n"
    summary += f"Total Records: {len(df):,}\n"
    summary += f"Columns: {', '.join(df.columns.tolist())}\n\n"

    # KPIs
    summary += "=== KEY METRICS ===\n"
    for k, v in kpis.items():
        if v is not None:
            summary += f"{k}: {v}\n"

    # Numeric stats
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if num_cols:
        summary += "\n=== NUMERIC STATS ===\n"
        desc = df[num_cols[:8]].describe().round(2)
        summary += desc.to_string()

    # Categorical
    cat_cols = [c for c in df.columns if df[c].dtype == object and df[c].nunique() <= 20]
    if cat_cols:
        summary += "\n\n=== CATEGORIES ===\n"
        for col in cat_cols[:5]:
            vc = df[col].value_counts().head(5)
            summary += f"\n{col}:\n"
            for val, cnt in vc.items():
                summary += f"  {val}: {cnt} ({cnt/len(df)*100:.1f}%)\n"

    return summary


def ask_claude(question, data_summary, chat_history, api_key, industry, client_name):
    """Ask Claude about the data"""
    import anthropic

    system_prompt = f"""You are InsightFlow AI, a smart data analyst for {client_name} in Lucknow, India.
You have access to their {industry} business data.

DATA SUMMARY:
{data_summary}

Your job:
- Answer questions about this specific data
- Give precise numbers from the data
- Use Indian currency format (Rs, lakh, crore)
- Be concise but helpful
- If asked about trends, reference the actual data
- Give actionable business advice based on data
- Keep responses under 150 words
- Use emojis where appropriate

Always base your answers on the actual data provided. If you don't know something from the data, say so."""

    messages = []
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

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
        st.warning("⚠️ Pehle data upload karo — phir chatbot use karo!")
        if st.button("→ Upload Data", type="primary"):
            st.session_state["page"] = "upload"
            st.rerun()
        return

    # API Key
    api_key = st.text_input(
        "Claude API Key",
        type="password",
        placeholder="sk-ant-...",
        key="chatbot_api_key"
    )

    if not api_key:
        st.info("💡 Claude API key daalo chatbot use karne ke liye.")

        # Show sample questions
        st.markdown('<div class="section-title">💬 SAMPLE QUESTIONS</div>', unsafe_allow_html=True)
        samples = {
            "hospital": [
                "Sabse zyada revenue konse department se aa raha hai?",
                "Average treatment cost kitna hai?",
                "Kitne percent patients critical hain?",
                "Konsa doctor sabse zyada patients dekh raha hai?",
            ],
            "ecommerce": [
                "Total net revenue kitna hai after discount?",
                "Sabse zyada bikne wali category kaun si hai?",
                "Return rate kitna hai?",
                "Konse city se sabse zyada orders aa rahe hain?",
            ],
            "logistics": [
                "Average transit time kitna hai?",
                "Delay rate kitni hai?",
                "Fuel cost revenue ka kitna percent hai?",
                "Sabse busy route kaun sa hai?",
            ],
            "education": [
                "Placement rate kitna hai?",
                "Average CGPA kitna hai?",
                "Kitne students ki attendance 75% se kam hai?",
                "Sabse zyada placements konse department mein hain?",
            ],
            "generic": [
                "Data mein kya interesting trends hain?",
                "Sabse important numbers kya hain?",
                "Kya improvements suggest karoge?",
            ]
        }

        q_list = samples.get(industry, samples["generic"])
        for q in q_list:
            st.markdown(f'<div class="insight-card ins-info">💬 {q}</div>', unsafe_allow_html=True)
        return

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Data summary
    if "data_summary" not in st.session_state:
        st.session_state["data_summary"] = get_data_summary(df, kpis, industry)

    # Chat display
    st.markdown('<div class="section-title">💬 CONVERSATION</div>', unsafe_allow_html=True)

    chat_container = st.container()
    with chat_container:
        if not st.session_state["chat_history"]:
            st.markdown(f"""
            <div style="background:#0D2818;border:1px solid #1A4731;border-radius:10px;padding:1rem;margin:0.5rem 0;">
                <div style="color:#3FB950;font-weight:600;">🤖 InsightFlow AI</div>
                <div style="color:#8B949E;margin-top:0.3rem;">
                    Namaste! Main aapke {industry} data ka analyst hoon.<br>
                    <b style="color:#E6EDF3;">{len(df):,} records</b> analyze kar chuka hoon.<br>
                    Koi bhi sawaal poochho apne business data ke baare mein!
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
                    <div style="color:#3FB950;font-weight:600;font-size:0.8rem;">🤖 InsightFlow AI</div>
                    <div style="color:#E6EDF3;margin-top:0.2rem;">{msg["content"]}</div>
                </div>
                """, unsafe_allow_html=True)

    # Quick question buttons
    st.markdown('<div class="section-title">⚡ QUICK QUESTIONS</div>', unsafe_allow_html=True)
    quick_q = {
        "hospital": ["Revenue kitna hai?", "Top department?", "Critical patients?"],
        "ecommerce": ["Net revenue?", "Top category?", "Return rate?"],
        "logistics": ["Delivery rate?", "Avg transit?", "Top route?"],
        "education": ["Placement rate?", "Avg CGPA?", "Low attendance?"],
        "generic": ["Key insights?", "Best metric?", "Improvements?"]
    }
    qs = quick_q.get(industry, quick_q["generic"])
    qcols = st.columns(len(qs))
    for i, q in enumerate(qs):
        with qcols[i]:
            if st.button(q, key=f"quick_{i}", use_container_width=True):
                st.session_state["pending_q"] = q

    # Input
    st.markdown("")
    col_inp, col_btn = st.columns([5, 1])
    with col_inp:
        user_input = st.text_input(
            "Sawaal poochho",
            placeholder="Jaise: Is mahine ka revenue kitna tha?",
            key="chat_input",
            label_visibility="collapsed"
        )
    with col_btn:
        send = st.button("Send", type="primary", use_container_width=True, key="btn_send")

    # Handle pending quick question
    if "pending_q" in st.session_state:
        user_input = st.session_state.pop("pending_q")
        send = True

    if send and user_input:
        with st.spinner("🤖 Soch raha hoon..."):
            try:
                response = ask_claude(
                    user_input,
                    st.session_state["data_summary"],
                    st.session_state["chat_history"],
                    api_key,
                    industry,
                    client_name
                )
                st.session_state["chat_history"].append({"role": "user", "content": user_input})
                st.session_state["chat_history"].append({"role": "assistant", "content": response})
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)[:100]}")

    # Clear chat
    if st.session_state["chat_history"]:
        if st.button("🗑️ Clear Chat", key="btn_clear_chat"):
            st.session_state["chat_history"] = []
            st.rerun()
