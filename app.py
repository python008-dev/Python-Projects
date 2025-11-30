#This is a menu driven Expense Tracker System
import streamlit as st
import pandas as pd
import os
import json
import io
import csv
import hashlib
from datetime import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt

# -------------------------
# Config / Filenames
# -------------------------
USERS_FILE = "users.json"            # stores username -> {password_hash}
DATA_DIR = "."                       # workspace (Streamlit Cloud writable)
DATE_FMT = "%Y-%m-%d %H:%M:%S"

# -------------------------
# Utility helpers
# -------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_users(users: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def user_expense_path(username: str) -> str:
    return os.path.join(DATA_DIR, f"expenses_{username}.csv")

def user_budget_path(username: str) -> str:
    return os.path.join(DATA_DIR, f"budgets_{username}.json")

def ensure_user_files(username: str):
    p = user_expense_path(username)
    if not os.path.exists(p):
        pd.DataFrame(columns=["Date","Category","Description","Amount"]).to_csv(p, index=False)
    b = user_budget_path(username)
    if not os.path.exists(b):
        with open(b, "w", encoding="utf-8") as f:
            json.dump({}, f)

def load_expenses(username: str) -> pd.DataFrame:
    p = user_expense_path(username)
    if not os.path.exists(p):
        return pd.DataFrame(columns=["Date","Category","Description","Amount"])
    df = pd.read_csv(p)
    if "Amount" in df.columns:
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    return df

def save_expenses(username: str, df: pd.DataFrame):
    p = user_expense_path(username)
    df.to_csv(p, index=False)

def load_budgets(username: str) -> dict:
    p = user_budget_path(username)
    if not os.path.exists(p):
        return {}
    with open(p, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_budgets(username: str, budgets: dict):
    p = user_budget_path(username)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(budgets, f, indent=2)

def add_expense(username: str, category: str, description: str, amount: float):
    ensure_user_files(username)
    df = load_expenses(username)
    date = datetime.now().strftime(DATE_FMT)
    df = pd.concat([df, pd.DataFrame([[date, category, description, float(amount)]], columns=df.columns)], ignore_index=True)
    save_expenses(username, df)
    # check budget
    warn = budget_check(username, category)
    return warn

def budget_check(username: str, category: str):
    """Return (exceeded_bool, current_sum, budget_value) if budget exists; else None"""
    budgets = load_budgets(username)
    if not budgets or category not in budgets:
        return None
    budget_val = float(budgets.get(category, 0))
    df = load_expenses(username)
    # monthly total of this category for current month
    try:
        df["Date_dt"] = pd.to_datetime(df["Date"])
    except Exception:
        return None
    cur_month = datetime.now().month
    month_sum = df[(df["Date_dt"].dt.month == cur_month) & (df["Category"] == category)]["Amount"].sum()
    exceeded = month_sum > budget_val
    return (exceeded, month_sum, budget_val)

# Export helpers
def export_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def export_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Expenses")
    return buffer.getvalue()

def export_pdf_bytes(df: pd.DataFrame, username: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Expense Report - {username}", ln=True, align="C")
    pdf.ln(4)
    col_w = [40, 30, 90, 30]
    headers = ["Date", "Category", "Description", "Amount"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, border=1)
    pdf.ln()
    for _, row in df.iterrows():
        pdf.cell(col_w[0], 7, str(row.get("Date","")), border=1)
        pdf.cell(col_w[1], 7, str(row.get("Category",""))[:18], border=1)
        pdf.cell(col_w[2], 7, str(row.get("Description",""))[:45], border=1)
        pdf.cell(col_w[3], 7, f"₹{row.get('Amount',0):.2f}", border=1, ln=1)
    return pdf.output(dest="S").encode("latin-1")

# -------------------------
# Streamlit App UI
# -------------------------
st.set_page_config(page_title="Expense Tracker — Secure Pro", layout="wide")

# Add branding (header)
st.markdown("""
    <div style="text-align:center;">
        <h1>💸 Expense Tracker — Secure Pro</h1>
        <p style="color:gray">Made with ❤ by <b>Mayank</b></p>
    </div>
""", unsafe_allow_html=True)

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# --------- Admin credentials (from Streamlit Secrets) ----------
# In Streamlit Cloud: set secrets named ADMIN_USER and ADMIN_PASS
ADMIN_USER = None
ADMIN_PASS = None
try:
    # st.secrets may not exist locally; use .get to avoid errors
    ADMIN_USER = st.secrets.get("ADMIN_USER")
    ADMIN_PASS = st.secrets.get("ADMIN_PASS")
except Exception:
    ADMIN_USER = None
    ADMIN_PASS = None

# -------------------------
# Auth sidebar (Sign up / Login / Admin login)
# -------------------------
st.sidebar.header("Account")

users = load_users()

auth_mode = st.sidebar.radio("Mode", ("Login", "Sign up", "Admin login"))

if auth_mode == "Sign up":
    st.sidebar.subheader("Create an account")
    new_user = st.sidebar.text_input("Username", key="su_user")
    new_pass = st.sidebar.text_input("Password", type="password", key="su_pass")
    if st.sidebar.button("Create account"):
        if not new_user or not new_pass:
            st.sidebar.error("Provide username & password")
        elif new_user in users:
            st.sidebar.error("Username exists — choose another")
        else:
            users[new_user] = {"password": hash_password(new_pass)}
            save_users(users)
            ensure_user_files(new_user)
            st.sidebar.success("Account created — login now")
elif auth_mode == "Login":
    st.sidebar.subheader("User login")
    login_user = st.sidebar.text_input("Username", key="li_user")
    login_pass = st.sidebar.text_input("Password", type="password", key="li_pass")
    if st.sidebar.button("Login"):
        if login_user in users and users[login_user]["password"] == hash_password(login_pass):
            st.session_state.user = login_user
            st.session_state.is_admin = False
            st.sidebar.success(f"Signed in as {login_user}")
        else:
            st.sidebar.error("Invalid credentials")
elif auth_mode == "Admin login":
    st.sidebar.subheader("Admin (secure)")
    st.sidebar.markdown("**Note:** Admin credentials are stored securely using Streamlit Secrets (not in repo).")
    admin_user_in = st.sidebar.text_input("Admin username", key="ad_user")
    admin_pass_in = st.sidebar.text_input("Admin password", type="password", key="ad_pass")
    if st.sidebar.button("Admin Login"):
        if ADMIN_USER is None or ADMIN_PASS is None:
            st.sidebar.error("Admin credentials not set on server. Go to Streamlit Cloud > Settings > Secrets and add ADMIN_USER & ADMIN_PASS.")
        else:
            if admin_user_in == ADMIN_USER and admin_pass_in == ADMIN_PASS:
                st.session_state.user = ADMIN_USER
                st.session_state.is_admin = True
                st.sidebar.success("Admin logged in")
            else:
                st.sidebar.error("Invalid admin credentials")

# If user logged in, show Logout button
if st.session_state.user:
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.is_admin = False
        st.experimental_rerun()

# -------------------------
# If not logged in, show welcome / instructions
# -------------------------
if not st.session_state.user:
    st.info("Please sign up or login from the sidebar to use the app.")
    st.markdown("""
        **Quick steps**
        1. Create an account (Sign up).  
        2. Login and add expenses.  
        3. Admin can login via Streamlit Secrets to manage & view all users.
    """)
    st.markdown("**To deploy on Streamlit Cloud:** set `ADMIN_USER` and `ADMIN_PASS` in *Secrets* (Settings → Secrets*).")
    st.stop()

# -------------------------
# Authenticated area
# -------------------------
username = st.session_state.user
is_admin = st.session_state.is_admin

# If admin, show admin panel with special tools
if is_admin:
    st.header("🛠 Admin Dashboard (Secure)")
    st.subheader("Manage users & view aggregate data")

    all_users = load_users()
    st.write(f"Total registered users: **{len(all_users)}**")
    user_list = list(all_users.keys())
    st.write(user_list)

    # View aggregated expenses across users
    agg_dfs = []
    for u in user_list:
        p = user_expense_path(u)
        if os.path.exists(p):
            dfu = pd.read_csv(p)
            if not dfu.empty:
                dfu["user"] = u
                agg_dfs.append(dfu)
    if agg_dfs:
        agg = pd.concat(agg_dfs, ignore_index=True)
        agg["Amount"] = pd.to_numeric(agg["Amount"], errors="coerce").fillna(0)
        st.write("### Aggregated data preview (latest 20 rows)")
        st.dataframe(agg.tail(20))
        st.write("### Overall stats")
        st.metric("Total records", len(agg))
        st.metric("Total amount (all users)", f"₹{agg['Amount'].sum():.2f}")

        # Simple admin charts
        st.write("#### Top categories overall")
        top_cat = agg.groupby("Category")["Amount"].sum().sort_values(ascending=False).head(10)
        fig1, ax1 = plt.subplots(figsize=(6,4))
        top_cat.plot.bar(ax=ax1)
        ax1.set_ylabel("Amount")
        st.pyplot(fig1)
    else:
        st.info("No user expense data yet.")

    st.markdown("---")
    st.write("### Admin actions")
    sel_user = st.selectbox("Select user to inspect", [""] + user_list)
    if sel_user:
        dfu = load_expenses(sel_user)
        st.write(f"Expenses for **{sel_user}** (rows: {len(dfu)})")
        st.dataframe(dfu)
        if st.button(f"Delete all data for {sel_user}"):
            pd.DataFrame(columns=["Date","Category","Description","Amount"]).to_csv(user_expense_path(sel_user), index=False)
            st.success(f"Deleted data for {sel_user}")
    st.markdown("<br>", unsafe_allow_html=True)
    st.stop()

# -------------------------
# Regular user UI
# -------------------------
ensure_user_files(username)

st.sidebar.markdown("---")
st.sidebar.write(f"Signed in as: **{username}**")
menu = st.sidebar.selectbox("Navigate", ["Add Expense", "History & Export", "Analytics", "Budgets", "Settings"])
st.sidebar.markdown("👨‍💻 Developed by Mayank")

# Add Expense
if menu == "Add Expense":
    st.header("➕ Add Expense")
    categories = ["Food","Transport","Shopping","Bills","Entertainment","Investment","Other"]
    cat = st.selectbox("Category", categories)
    desc = st.text_input("Description")
    amt = st.number_input("Amount (₹)", min_value=0.01, format="%.2f")
    if st.button("Add"):
        if amt <= 0:
            st.error("Enter amount > 0")
        else:
            warn = add_expense(username, cat, desc, amt)
            st.success(f"Added ₹{amt:.2f} to {cat}")
            if warn:
                exceeded, cur_sum, budget_val = warn
                if exceeded:
                    st.warning(f"⚠ Budget exceeded for {cat}! Current month total: ₹{cur_sum:.2f} / Budget: ₹{budget_val:.2f}")
                else:
                    # show progress
                    pct = (cur_sum / budget_val) * 100 if budget_val > 0 else 0
                    st.info(f"Budget for {cat}: ₹{cur_sum:.2f} / ₹{budget_val:.2f} ({pct:.0f}%)")

# History & Export
elif menu == "History & Export":
    st.header("📜 Expense History & Export")
    df = load_expenses(username)
    if df.empty:
        st.info("No expenses yet.")
    else:
        # date handling
        try:
            df["Date_dt"] = pd.to_datetime(df["Date"])
        except Exception:
            df["Date_dt"] = pd.to_datetime(df["Date"], errors="coerce")
        min_date = df["Date_dt"].min().date()
        max_date = df["Date_dt"].max().date()
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("From", value=min_date)
        with col2:
            end = st.date_input("To", value=max_date)

        cat_filter = st.text_input("Category contains (optional)")
        desc_search = st.text_input("Search description (optional)")

        df_view = df.copy()
        df_view = df_view[(df_view["Date_dt"].dt.date >= start) & (df_view["Date_dt"].dt.date <= end)]
        if cat_filter:
            df_view = df_view[df_view["Category"].str.contains(cat_filter, case=False, na=False)]
        if desc_search:
            df_view = df_view[df_view["Description"].str.contains(desc_search, case=False, na=False)]

        st.write(f"Showing {len(df_view)} rows")
        st.dataframe(df_view.drop(columns=["Date_dt"]))

        st.download_button("Download CSV", data=export_csv_bytes(df_view.drop(columns=["Date_dt"])), file_name=f"expenses_{username}.csv", mime="text/csv")
        st.download_button("Download Excel", data=export_excel_bytes(df_view.drop(columns=["Date_dt"])), file_name=f"expenses_{username}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Download PDF", data=export_pdf_bytes(df_view.drop(columns=["Date_dt"])), file_name=f"expenses_{username}.pdf", mime="application/pdf")

# Analytics
elif menu == "Analytics":
    st.header("📊 Analytics")
    df = load_expenses(username)
    if df.empty:
        st.info("Add some expenses first.")
    else:
        try:
            df["Date_dt"] = pd.to_datetime(df["Date"])
        except Exception:
            df["Date_dt"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Month"] = df["Date_dt"].dt.to_period("M").astype(str)
        # Monthly selection
        months = df["Month"].unique().tolist()
        months.sort(reverse=True)
        sel_month = st.selectbox("Select Month", ["All"] + months)
        if sel_month != "All":
            dfm = df[df["Month"] == sel_month]
        else:
            dfm = df.copy()

        st.subheader("Summary")
        total_amt = dfm["Amount"].sum()
        st.metric("Total Spent", f"₹{total_amt:.2f}")
        st.metric("Transactions", len(dfm))

        st.subheader("Category breakdown")
        cat_sum = dfm.groupby("Category")["Amount"].sum().sort_values(ascending=False)
        if not cat_sum.empty:
            fig2, ax2 = plt.subplots(figsize=(6,4))
            cat_sum.plot(kind="bar", ax=ax2)
            ax2.set_ylabel("Amount (₹)")
            st.pyplot(fig2)

            # Pie
            fig3, ax3 = plt.subplots(figsize=(5,5))
            cat_sum.plot.pie(autopct="%1.1f%%", ax=ax3)
            ax3.set_ylabel("")
            st.pyplot(fig3)

        st.subheader("Top 5 expenses")
        st.table(dfm.sort_values("Amount", ascending=False).head(5)[["Date","Category","Description","Amount"]])

        st.subheader("Monthly trend (last 6 months)")
        monthly = df.groupby("Month")["Amount"].sum().reset_index().sort_values("Month")
        # take last 6
        if len(monthly) > 6:
            monthly = monthly.tail(6)
        fig4, ax4 = plt.subplots(figsize=(7,3))
        ax4.plot(monthly["Month"], monthly["Amount"], marker="o")
        ax4.set_xlabel("Month")
        ax4.set_ylabel("Amount (₹)")
        plt.xticks(rotation=45)
        st.pyplot(fig4)

# Budgets
elif menu == "Budgets":
    st.header("🏷 Budgets (monthly per-category)")
    budgets = load_budgets(username)
    st.write("Current budgets (monthly):")
    st.write(budgets if budgets else "No budgets set")

    st.markdown("**Set / Update budget for a category**")
    b_cat = st.text_input("Category for budget", value="")
    b_val = st.number_input("Monthly budget amount (₹)", min_value=0.0, format="%.2f", value=0.0)
    if st.button("Save budget"):
        if not b_cat:
            st.error("Enter a category")
        else:
            budgets[b_cat] = float(b_val)
            save_budgets(username, budgets)
            st.success(f"Saved budget ₹{b_val:.2f} for {b_cat}")

    if budgets:
        # show progress for each category
        st.markdown("### Budget progress (current month)")
        df = load_expenses(username)
        try:
            df["Date_dt"] = pd.to_datetime(df["Date"])
        except Exception:
            df["Date_dt"] = pd.to_datetime(df["Date"], errors="coerce")
        cur_month = datetime.now().month
        for c, val in budgets.items():
            cur_sum = df[(df["Date_dt"].dt.month == cur_month) & (df["Category"] == c)]["Amount"].sum()
            pct = (cur_sum / val * 100) if val > 0 else 0
            st.write(f"**{c}** — ₹{cur_sum:.2f} / ₹{val:.2f} ({pct:.0f}%)")
            st.progress(min(int(pct if pct>0 else 0), 100))

# Settings
elif menu == "Settings":
    st.header("⚙ Settings")
    st.write("Account: ", username)
    if st.button("Delete my data (expenses)"):
        pd.DataFrame(columns=["Date","Category","Description","Amount"]).to_csv(user_expense_path(username), index=False)
        st.success("Your expense data cleared.")
    if st.button("Delete my account (includes data)"):
        users = load_users()
        if username in users:
            users.pop(username)
            save_users(users)
        # delete files
        try:
            os.remove(user_expense_path(username))
        except Exception:
            pass
        try:
            os.remove(user_budget_path(username))
        except Exception:
            pass
        st.success("Account & data deleted. Logging out...")
        st.session_state.user = None
        st.experimental_rerun()

# Footer
st.markdown("<hr><p style='text-align:center;color:gray'>© 2025 Expense Tracker | Built by <b>Mayank</b></p>", unsafe_allow_html=True)

