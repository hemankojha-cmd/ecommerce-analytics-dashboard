import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import hashlib
import sqlite3

st.set_page_config(page_title="AI Data Dashboard", layout="wide")

# ---------------- THEME (FIXED) ----------------
theme = st.sidebar.selectbox("🎨 Theme", ["Light", "Dark"])

if theme == "Dark":
    st.markdown("""
        <style>
        .stApp {
            background-color: #0E1117;
            color: white;
        }

        section[data-testid="stSidebar"] {
            background-color: #161A25;
        }

        h1, h2, h3, h4, h5, h6, p, div {
            color: white !important;
        }

        .stMetric {
            color: white;
        }

        div[data-testid="stMetricValue"] {
            color: #00FFAA;
        }

        .stDataFrame, .stTable {
            background-color: #111;
        }

        input, textarea {
            background-color: #222 !important;
            color: white !important;
        }

        div[data-baseweb="select"] {
            background-color: #222 !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT
)
""")
conn.commit()

# ---------------- AUTH ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def user_exists(username):
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    return c.fetchone()

def create_user(username, password):
    if user_exists(username):
        return "exists"
    c.execute("INSERT INTO users VALUES (?, ?)", (username, hash_password(password)))
    conn.commit()
    return "success"

def login_user(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", 
              (username, hash_password(password)))
    return c.fetchone()

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:

    st.title("🔐 Login / Register")

    menu = st.radio("Select", ["Login", "Register"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if menu == "Register":
        if st.button("Create Account"):
            if len(username) < 3:
                st.warning("Username too short")
            elif len(password) < 4:
                st.warning("Weak password")
            else:
                res = create_user(username, password)
                if res == "success":
                    st.success("✅ Account Created")
                else:
                    st.warning("⚠ User already exists")

    else:
        if st.button("Login"):
            if login_user(username, password):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ Invalid credentials")

    st.stop()

# ---------------- UNIVERSAL FILE LOADER ----------------
def load_file(file):
    try:
        if file.name.endswith(".xlsx"):
            return pd.read_excel(file)
    except:
        pass

    encodings = ["utf-8", "latin1", "cp1252", "ISO-8859-1"]

    for enc in encodings:
        try:
            return pd.read_csv(file, encoding=enc, sep=None, engine="python")
        except:
            file.seek(0)

    raise ValueError("File not supported")

# ---------------- PDF FIX ----------------
def clean_text(text):
    return text.encode("latin-1", "ignore").decode("latin-1")

# ---------------- MAIN APP ----------------
st.title("📊 AI-Powered Universal Data Dashboard")

uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

if uploaded_file is not None:

    try:
        df = load_file(uploaded_file)
    except:
        st.error("❌ Could not read file")
        st.stop()

    # CLEANING
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", case=False)]
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = df.columns.str.strip()
    df = df.reset_index(drop=True)

    st.success("✅ Data Loaded Successfully")

    # COLUMN SELECT
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()

    date_col = st.selectbox("Date Column", ["None"] + all_cols)
    value_col = st.selectbox("Numeric Column", num_cols if num_cols else all_cols)
    category_col = st.selectbox("Category Column", cat_cols if cat_cols else all_cols)

    # TYPE FIX
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

    if date_col != "None":
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    df = df.dropna(subset=[value_col])

    if date_col != "None":
        df = df.dropna(subset=[date_col])

    # KPIs
    st.subheader("📌 KPIs")

    total = df[value_col].sum()
    avg = df[value_col].mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", f"{total:,.0f}")
    c2.metric("Average", f"{avg:,.2f}")
    c3.metric("Records", len(df))

    # CHARTS
    st.subheader("📈 Charts")

    if date_col != "None":
        ts = df.groupby(date_col, as_index=False)[value_col].sum()
        st.plotly_chart(px.line(ts, x=date_col, y=value_col), use_container_width=True)

    cat_df = df.groupby(category_col, as_index=False)[value_col].sum()

    st.plotly_chart(px.bar(cat_df, x=category_col, y=value_col), use_container_width=True)
    st.plotly_chart(px.pie(cat_df, names=category_col, values=value_col), use_container_width=True)

    # ADVANCED
    if date_col != "None":
        df["Month"] = df[date_col].dt.to_period("M").astype(str)
        monthly = df.groupby("Month", as_index=False)[value_col].sum()
        st.plotly_chart(px.area(monthly, x="Month", y=value_col), use_container_width=True)

    if len(num_cols) > 1:
        corr = df[num_cols].corr()
        st.plotly_chart(px.imshow(corr, text_auto=True), use_container_width=True)

    # TOP
    st.subheader("🔝 Top Records")
    st.dataframe(df.sort_values(by=value_col, ascending=False).head(10))

    # AI INSIGHTS
    st.subheader("🤖 AI Insights")

    insights = []

    if len(df) > 1:
        trend = df[value_col].pct_change().mean() * 100
        insights.append(f"Average growth: {trend:.2f}%")

    if len(cat_df) > 0:
        top = cat_df.sort_values(by=value_col, ascending=False).iloc[0][category_col]
        insights.append(f"Top category: {top}")

    insights.append(f"Total value: {total:,.0f}")

    for i in insights:
        st.write("👉", i)

    # PDF
    st.subheader("📄 Export Report")

    if st.button("Generate PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, "AI Data Report", ln=True)

        for i in insights:
            pdf.cell(200, 10, clean_text(i), ln=True)

        pdf.output("report.pdf")

        with open("report.pdf", "rb") as f:
            st.download_button("Download PDF", f, "report.pdf")

else:
    st.info("👆 Upload CSV or Excel to begin")