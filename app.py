import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import hashlib
import sqlite3

st.set_page_config(page_title="Universal Data Dashboard", layout="wide")

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

# ---------------- LOGIN UI ----------------
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
                st.warning("Password too weak")
            else:
                result = create_user(username, password)
                if result == "success":
                    st.success("✅ Account Created")
                else:
                    st.warning("⚠ Username already exists")

    else:
        if st.button("Login"):
            if login_user(username, password):
                st.session_state.logged_in = True
                st.success("✅ Logged in")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")

    st.stop()

# ---------------- MAIN APP ----------------

st.title("📊 Universal CSV Analytics Dashboard")

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)

    # ---------------- CLEANING ----------------
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", case=False)]
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = df.columns.str.strip()
    df = df.reset_index(drop=True)

    st.success("✅ Data Loaded")

    # ---------------- COLUMN SELECT ----------------
    all_cols = df.columns.tolist()

    date_col = st.selectbox("Select Date Column (optional)", ["None"] + all_cols)
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()

    revenue_col = st.selectbox("Select Revenue Column", num_cols if num_cols else all_cols)
    category_col = st.selectbox("Select Category Column", cat_cols if cat_cols else all_cols)

    # ---------------- TYPE FIX ----------------
    df[revenue_col] = pd.to_numeric(df[revenue_col], errors="coerce")
    df = df.dropna(subset=[revenue_col])

    if date_col != "None":
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])

        if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
            st.warning("⚠ Invalid date column")
            date_col = "None"

    # ---------------- KPIs ----------------
    st.subheader("📌 Key Metrics")

    total_rev = df[revenue_col].sum()
    avg_rev = df[revenue_col].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"{total_rev:,.0f}")
    col2.metric("Average Revenue", f"{avg_rev:,.2f}")
    col3.metric("Total Records", len(df))

    # ---------------- CHARTS ----------------
    st.subheader("📈 Visual Analysis")

    # Revenue Over Time
    if date_col != "None":
        rev_time_df = (
            df.groupby(date_col, as_index=False)[revenue_col]
            .sum()
            .rename(columns={revenue_col: "Revenue"})
        )
        st.plotly_chart(px.line(rev_time_df, x=date_col, y="Revenue"), use_container_width=True)

    # Category Bar
    cat_df = (
        df.groupby(category_col, as_index=False)[revenue_col]
        .sum()
    )
    st.plotly_chart(px.bar(cat_df, x=category_col, y=revenue_col), use_container_width=True)

    # Pie Chart
    st.plotly_chart(px.pie(cat_df, names=category_col, values=revenue_col), use_container_width=True)

    # ---------------- ADVANCED ----------------
    if date_col != "None" and pd.api.types.is_datetime64_any_dtype(df[date_col]):

        df["Month"] = df[date_col].dt.to_period("M").astype(str)

        monthly = (
            df.groupby("Month", as_index=False)[revenue_col]
            .sum()
        )

        st.plotly_chart(px.area(monthly, x="Month", y=revenue_col), use_container_width=True)

    if len(num_cols) > 1:
        corr = df[num_cols].corr()
        st.plotly_chart(px.imshow(corr, text_auto=True), use_container_width=True)

    st.subheader("🔝 Top Records")
    st.dataframe(df.sort_values(by=revenue_col, ascending=False).head(10))

    # ---------------- AI INSIGHTS ----------------
    st.subheader("🤖 AI Insights")

    insights = []

    if date_col != "None":
        growth = rev_time_df["Revenue"].pct_change().mean() * 100
        insights.append(f"Average revenue growth: {growth:.2f}%")

    top_cat = cat_df.sort_values(by=revenue_col, ascending=False).iloc[0][category_col]
    insights.append(f"Top category: {top_cat}")
    insights.append(f"Total revenue: {total_rev:,.0f}")

    for i in insights:
        st.write("👉", i)

    # ---------------- PDF EXPORT ----------------
    st.subheader("📄 Export Report")

    if st.button("Generate PDF Report"):

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt="Data Analysis Report", ln=True)

        for i in insights:
            pdf.cell(200, 10, txt=i, ln=True)

        file_path = "report.pdf"
        pdf.output(file_path)

        with open(file_path, "rb") as f:
            st.download_button("Download PDF", f, file_name="report.pdf")

else:
    st.info("👆 Upload a CSV file to start")