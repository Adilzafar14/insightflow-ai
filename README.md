# 📊 InsightFlow AI
### Lucknow's AI-Powered Data Analytics Platform

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://insightflow-adil.streamlit.app)

---

## 🚀 Live Demo
**[insightflow-adil.streamlit.app](https://insightflow-adil.streamlit.app)**

---

## 📌 About
InsightFlow AI is a complete data analytics platform built for small and medium businesses in Lucknow. Upload your CSV or Excel data and get instant AI-powered insights, dashboards, and predictions.

---

## ✅ Features

### 📊 Industry Dashboards
- **Hospital** — Patient analytics, revenue, department performance
- **E-Commerce** — Orders, revenue, returns, top categories
- **Logistics** — Shipments, delivery rate, fuel costs, routes
- **Education** — Attendance, CGPA, placements, fee collection

### 🔍 Analysis Types
- Univariate Analysis
- Bivariate Analysis
- Multivariate Analysis
- Predictive Analysis (Trend + Forecast)

### 🤖 AI Features
- **AI Chatbot** — Ask questions about your data (Groq free / Claude)
- **Claude AI Insights** — Automatic business insights
- **OCR Bill Scanner** — Upload bill photo → auto data entry

### 📄 Reports
- PDF Report generation
- Excel export

### 🔐 Security
- Secure login system
- Each client gets private dashboard
- Role-based access (Admin / Client)
- Password change from profile

### 📱 Data Entry Portal
- Manual daily data entry
- Photo/bill OCR upload
- Entry history with trends

### 🎉 Other
- Festival Calendar (Lucknow 2026)
- Client management
- User management

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Backend |
| Streamlit | Frontend / UI |
| Supabase | Cloud Database |
| Plotly | Charts & Visualizations |
| Groq AI | Free AI Chatbot |
| Claude AI | OCR + Insights |
| ReportLab | PDF Generation |
| Pandas / NumPy | Data Processing |

---

## 🚀 Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/Adilzafar14/insightflow-ai.git
cd insightflow-ai
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Streamlit Secrets
Create `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_anon_key"
GROQ_API_KEY = "your_groq_api_key"
```

### 4. Run the app
```bash
streamlit run main.py
```

---

## 📁 Project Structure

```
insightflow-ai/
├── main.py          # Main app router + UI pages
├── auth.py          # Authentication + Database
├── pipeline.py      # Industry detection + data processing
├── dashboard.py     # Charts + visualizations
├── portal.py        # Data entry portal
├── chatbot.py       # AI Chatbot
├── reports.py       # PDF report generator
├── requirements.txt
└── runtime.txt
```

---


## 👨‍💻 Built By
**Adil** — Solo developer from Lucknow, India

🔗 [LinkedIn](https://linkedin.com) | 📧 Contact for demo

---

## 📝 License
This project is proprietary. All rights reserved.
