import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="SplashBI V6 – Bug Portfolio Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🐞 SplashBI V6 – Bug Portfolio Control Tower")
st.caption("Director view of Jira bug backlog + leadership playbook.")

# ---------------------------------------------------------
# Tabs: 1) Dashboard  2) Director Guide
# ---------------------------------------------------------
tab_dashboard, tab_guide = st.tabs(["📊 Bug Dashboard", "🚀 Director Guide"])

# =========================================================
# TAB 1: BUG DASHBOARD
# =========================================================
with tab_dashboard:
    st.sidebar.header("1️⃣ Upload Jira Export")
    uploaded_file = st.sidebar.file_uploader(
        "Upload Jira CSV export (e.g., V6Bugs List.csv)",
        type=["csv"],
        help="Export from Jira in CSV format with columns like 'Summary', 'Issue key', 'Issue Type', 'Status', 'Priority', 'Assignee', 'Created', etc.",
    )

    @st.cache_data(show_spinner=True)
    def load_data(file):
        df = pd.read_csv(file)
        # Normalize some known columns if present
        for col in ["Created", "Updated", "Resolved"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df

    def normalize_status(series):
        return series.fillna("").astype(str).str.strip().str.lower()

    if uploaded_file is None:
        st.info(
            "⬅️ Please upload your **V6 Jira bug export CSV** using the sidebar to view the dashboard."
        )
    else:
        df = load_data(uploaded_file)

        # Basic safety checks
        required_cols = ["Summary", "Issue key", "Issue Type", "Status"]
        missing = [c for c in required_cols if c not in df.columns]

        if missing:
            st.error(f"Missing required columns in CSV: {', '.join(missing)}")
        else:
            st.sidebar.header("2️⃣ Filters")

            # Sidebar filter options from data
            issue_types = sorted(df["Issue Type"].dropna().unique().tolist())
            statuses = sorted(df["Status"].dropna().unique().tolist())
            priorities = (
                sorted(df["Priority"].dropna().unique().tolist())
                if "Priority" in df.columns
                else []
            )
            assignees = (
                sorted(df["Assignee"].dropna().unique().tolist())
                if "Assignee" in df.columns
                else []
            )

            selected_issue_types = st.sidebar.multiselect(
                "Issue Type",
                options=issue_types,
                default=issue_types,
            )

            selected_statuses = st.sidebar.multiselect(
                "Status",
                options=statuses,
                default=statuses,
            )

            if priorities:
                selected_priorities = st.sidebar.multiselect(
                    "Priority",
                    options=priorities,
                    default=priorities,
                )
            else:
                selected_priorities = []

            if assignees:
                selected_assignees = st.sidebar.multiselect(
                    "Assignee",
                    options=assignees,
                    default=assignees,
                )
            else:
                selected_assignees = []

            # Date filter
            date_col = None
            for cand in ["Created", "Updated"]:
                if cand in df.columns:
                    date_col = cand
                    break

            date_range = None
            if date_col:
                min_date = df[date_col].min()
                max_date = df[date_col].max()
                if pd.notna(min_date) and pd.notna(max_date):
                    st.sidebar.subheader("Date Range")
                    date_range = st.sidebar.date_input(
                        f"Filter by {date_col} date",
                        value=(min_date.date(), max_date.date()),
                        min_value=min_date.date(),
                        max_value=max_date.date(),
                    )

            # Apply filters
            filtered_df = df.copy()

            if selected_issue_types:
                filtered_df = filtered_df[filtered_df["Issue Type"].isin(selected_issue_types)]

            if selected_statuses:
                filtered_df = filtered_df[filtered_df["Status"].isin(selected_statuses)]

            if priorities and selected_priorities:
                filtered_df = filtered_df[filtered_df["Priority"].isin(selected_priorities)]

            if assignees and selected_assignees:
                filtered_df = filtered_df[filtered_df["Assignee"].isin(selected_assignees)]

            if date_col and date_range:
                start_date, end_date = date_range
                mask = (filtered_df[date_col] >= pd.to_datetime(start_date)) & (
                    filtered_df[date_col] <= pd.to_datetime(end_date)
                )
                filtered_df = filtered_df[mask]

            st.write(
                f"Showing **{len(filtered_df)}** of **{len(df)}** issues after filters."
            )

            # ========================
            # Top-level KPIs
            # ========================
            statuses_lower = normalize_status(df["Status"])
            is_closed = statuses_lower.isin(["closed", "done", "resolved"])
            total_issues = len(df)
            open_issues = int((~is_closed).sum())
            closed_issues = int(is_closed.sum())

            today = pd.Timestamp.today().normalize()
            last_30 = today - pd.Timedelta(days=30)

            if "Created" in df.columns:
                created_recent = int(
                    df[(df["Created"] >= last_30) & (df["Created"] <= today)].shape[0]
                )
            else:
                created_recent = np.nan

            if "Resolved" in df.columns:
                resolved_recent = int(
                    df[(df["Resolved"] >= last_30) & (df["Resolved"] <= today)].shape[0]
                )
            else:
                resolved_recent = np.nan

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Issues", f"{total_issues}")
            col2.metric("Open Issues", f"{open_issues}")
            col3.metric("Closed Issues", f"{closed_issues}")
            if not np.isnan(created_recent):
                col4.metric("Issues Created (Last 30 Days)", f"{created_recent}")
            else:
                col4.metric("Issues Created (Last 30 Days)", "N/A")

            # ========================
            # Charts Section
            # ========================
            st.markdown("---")
            st.subheader("📊 Portfolio Overview")

            c1, c2 = st.columns(2)

            # Issue Type distribution
            with c1:
                st.markdown("**By Issue Type**")
                type_counts = (
                    filtered_df["Issue Type"]
                    .value_counts()
                    .rename_axis("Issue Type")
                    .reset_index(name="Count")
                )
                if not type_counts.empty:
                    st.bar_chart(type_counts.set_index("Issue Type"))
                else:
                    st.info("No data for selected filters.")

            # Status distribution
            with c2:
                st.markdown("**By Status**")
                status_counts = (
                    filtered_df["Status"]
                    .value_counts()
                    .rename_axis("Status")
                    .reset_index(name="Count")
                )
                if not status_counts.empty:
                    st.bar_chart(status_counts.set_index("Status"))
                else:
                    st.info("No data for selected filters.")

            st.markdown("### 👥 Top Assignees")
            if "Assignee" in filtered_df.columns:
                top_n = st.slider(
                    "Show Top N Assignees", min_value=5, max_value=20, value=10, step=1
                )
                assignee_counts = (
                    filtered_df["Assignee"]
                    .value_counts()
                    .head(top_n)
                    .rename_axis("Assignee")
                    .reset_index(name="Count")
                    .sort_values("Count", ascending=False)
                )
                if not assignee_counts.empty:
                    st.bar_chart(assignee_counts.set_index("Assignee"))
                else:
                    st.info("No assignee data for selected filters.")
            else:
                st.info("Assignee column not found in CSV.")

            # ========================
            # Trend over time
            # ========================
            st.markdown("---")
            st.subheader("📈 Trend – Issues Created vs Resolved")

            if "Created" in df.columns or "Resolved" in df.columns:
                trend_df = pd.DataFrame()

                if "Created" in df.columns:
                    created_ts = (
                        df.dropna(subset=["Created"])
                        .assign(
                            month=lambda d: d["Created"]
                            .dt.to_period("M")
                            .dt.to_timestamp()
                        )
                        .groupby("month")["Issue key"]
                        .count()
                        .rename("Created")
                    )
                    trend_df = created_ts.to_frame()

                if "Resolved" in df.columns:
                    resolved_ts = (
                        df.dropna(subset=["Resolved"])
                        .assign(
                            month=lambda d: d["Resolved"]
                            .dt.to_period("M")
                            .dt.to_timestamp()
                        )
                        .groupby("month")["Issue key"]
                        .count()
                        .rename("Resolved")
                    )
                    if trend_df.empty:
                        trend_df = resolved_ts.to_frame()
                    else:
                        trend_df = trend_df.join(resolved_ts, how="outer")

                trend_df = trend_df.sort_index()
                if not trend_df.empty:
                    st.line_chart(trend_df)
                else:
                    st.info("No trend data available for Created/Resolved dates.")
            else:
                st.info(
                    "Created/Resolved columns not found. Trend chart is not available."
                )

            # ========================
            # Raw data table
            # ========================
            st.markdown("---")
            st.subheader("📋 Issue Details")

            default_cols = [
                col
                for col in [
                    "Issue key",
                    "Summary",
                    "Issue Type",
                    "Status",
                    "Priority",
                    "Assignee",
                    "Created",
                    "Resolved",
                ]
                if col in filtered_df.columns
            ]

            if default_cols:
                st.dataframe(
                    filtered_df[default_cols].sort_values(default_cols[0]),
                    use_container_width=True,
                    height=400,
                )
            else:
                st.dataframe(
                    filtered_df, use_container_width=True, height=400
                )

            st.caption(
                "Tip: Use the filters on the left to slice by type, status, assignee, "
                "priority, and date. This dashboard is designed to be reused for any Jira "
                "export of SplashBI V6 bugs."
            )

# =========================================================
# TAB 2: DIRECTOR GUIDE (YOUR TEXT)
# =========================================================
with tab_guide:
    st.markdown(
        """
# 🚀 Director-Level Guide to Handling a Large Volume of Product Bugs

Below is a practical framework used by senior product leaders to manage chaos and turn it into predictable progress.

---

## 1️⃣ First 7 Days – Stabilize & Get Clarity

### ✔ 1. Create a Single Source of Truth (SSOT) for All Bugs

Combine all bug lists into one place (Excel, Jira dashboard, or internal tracker).

Categorize each bug:

- **Severity:** Blocker / Critical / Major / Minor  
- **Area:** UI, Backend, ETL, Domain, Engine, APIs, Security  
- **Customer Impact:** High / Medium / Low  
- **Environment:** PROD / UAT / QA / DEV  
- **Team Ownership:** Visualization, ETL, Base Engine, HRMS, Finance, DBA, Cloud  

### ✔ 2. Run a Bug Triage Meeting

Hold a daily 15-minute triage with tech leads:

- Top 10 urgent bugs  
- Reassign owners  
- Remove roadblocks  
- Update ETAs  

This creates **discipline** and **visibility**.

---

## 2️⃣ Next – Build a Strong Execution System

### 2. Prioritize Using a Director-Level Lens

Focus on:

⭐ **Customer-impact first**  
Blockers → high-severity → production.  
Ignore cosmetic issues early.

⭐ **Revenue-impact second**  
Customers who are renewing soon or high-value.

⭐ **Strategic-impact third**  
Anything affecting long-term product roadmap.

---

## 3️⃣ Build a Multi-Team Collaboration Framework

As Director, your power is in **orchestration**, not fixing bugs yourself.

### ✔ 1. Create a “Bug Playbook”

Document:

- When to open a ticket  
- What details to capture  
- SLA for fixing  
- Definition of Ready / Definition of Done  

### ✔ 2. Assign Clear Owners

One bug → One owner → Clear ETA.

### ✔ 3. Weekly Cross-Team Sync

A 30-min meeting with:

- Engineering Manager  
- QA Lead  
- ETL Lead  
- Visualization Lead  
- DBA  
- DevOps  
- Product  
- Support  

**Agenda:**

- Top 5 blockers  
- Risks  
- Escalations  
- Deployment plan  

---

## 4️⃣ Build Dashboards (Director-Level Visibility)

You already have a strong data engineering background. Use that strength.

Create dashboards:

- Bug Aging Dashboard  
- Bug SLA Compliance  
- Module-wise Bug Density  
- Team-wise Productivity  
- Customer Escalation Risk Score  
- Release Readiness Score  

This gives you **leadership-level control**.

---

## 5️⃣ Communication Strategy (Very Important for Directors)

### ✔ Upward communication (CEO, VP, Leadership):

Weekly:

- Summary of progress  
- Top risks  
- What support you need  
- Releases planned  

Use crisp, 3–4 bullet points.

### ✔ Downward communication (Team Leads):

Daily:

- Expectations  
- Priorities  
- Appreciation & motivation  

Directors succeed when teams feel **clarity + support**.

---

## 6️⃣ Build a 60-Day Stabilization Plan

### Phase 1: 0–30 Days – Bug Reduction

**Goal:** Close 30–40% of high-severity bugs  

**Activities:**

- Daily triage  
- Weekly release  
- Dedicated "SWAT team" for critical customers  
- Customer communication plan  

### Phase 2: 30–60 Days – Improve Stability

**Goal:** Reduce incoming new bugs by 50%  

**Activities:**

- Root-cause analysis  
- Enforce coding standards  
- Improve regression suit  
- Strengthen QA automation  

---

## 7️⃣ Leadership Mindset to Follow

- ✔ Don’t jump to fix everything yourself – Directors **delegate and coordinate**.  
- ✔ Push for clarity – **Ambiguity creates bugs**.  
- ✔ Celebrate small wins – Keep morale high during heavy workloads.  
- ✔ Be visible – Communicate with customers and internal teams.  

"""
    )
