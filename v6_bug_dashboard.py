import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="V6 Bug Rescue Dashboard",
    layout="wide"
)

@st.cache_data
def load_data(uploaded_file):
    df = pd.read_csv(uploaded_file)
    # Clean up and prepare key columns
    if "Created" in df.columns:
        df["Created"] = pd.to_datetime(df["Created"], errors="coerce", dayfirst=True)
    if "Updated" in df.columns:
        df["Updated"] = pd.to_datetime(df["Updated"], errors="coerce", dayfirst=True)

    # Strip spaces from Status / Priority / Assignee if they exist
    for col in ["Status", "Priority", "Assignee"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


def main():
    st.title("🐞 V6 Dashboard Bugs – Rescue Operation")
    st.markdown(
        "Monitor blocker, critical and business scenario bugs from the Jira export "
        "and track progress by status, assignee, and priority."
    )

    # --- File upload ---
    st.sidebar.header("1. Upload Bugs File")
    uploaded_file = st.sidebar.file_uploader(
        "Upload V6DBUGS List.csv (Jira export)", type=["csv"]
    )

    if uploaded_file is None:
        st.info("⬅️ Please upload **V6DBUGS List.csv** to see the dashboard.")
        return

    df = load_data(uploaded_file)

    # --- Sidebar Filters ---
    st.sidebar.header("2. Filters")

    status_list = sorted(df["Status"].dropna().unique()) if "Status" in df.columns else []
    priority_list = sorted(df["Priority"].dropna().unique()) if "Priority" in df.columns else []
    assignee_list = sorted(df["Assignee"].dropna().unique()) if "Assignee" in df.columns else []

    selected_status = st.sidebar.multiselect(
        "Status", options=status_list, default=status_list
    ) if status_list else []

    selected_priority = st.sidebar.multiselect(
        "Priority", options=priority_list, default=priority_list
    ) if priority_list else []

    selected_assignee = st.sidebar.multiselect(
        "Assignee", options=assignee_list
    ) if assignee_list else []

    summary_search = st.sidebar.text_input("Search in Summary (contains)")

    # Apply filters
    filtered_df = df.copy()

    if selected_status and "Status" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Status"].isin(selected_status)]

    if selected_priority and "Priority" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Priority"].isin(selected_priority)]

    if selected_assignee and "Assignee" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Assignee"].isin(selected_assignee)]

    if summary_search and "Summary" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Summary"].str.contains(summary_search, case=False, na=False)
        ]

    # --- Top KPIs ---
    st.subheader("📊 Bug Summary")

    total_bugs = len(df)
    filtered_bugs = len(filtered_df)

    open_statuses = ["To Do", "Open", "Reopen", "In Progress"]
    high_priorities = ["Blocker", "Critical"]

    open_bugs = (
        filtered_df[filtered_df["Status"].isin(open_statuses)].shape[0]
        if "Status" in filtered_df.columns
        else None
    )
    high_pri_bugs = (
        filtered_df[filtered_df["Priority"].isin(high_priorities)].shape[0]
        if "Priority" in filtered_df.columns
        else None
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Bugs (All)", total_bugs)
    col2.metric("Bugs in View (Filters)", filtered_bugs)
    if open_bugs is not None:
        col3.metric("Open / Reopen / In Progress", open_bugs)
    if high_pri_bugs is not None:
        col4.metric("High Priority (Blocker + Critical)", high_pri_bugs)

    st.markdown("---")

    # --- Charts Row: By Priority & Status ---
    chart_col1, chart_col2 = st.columns(2)

    if "Priority" in filtered_df.columns:
        with chart_col1:
            st.markdown("#### Bugs by Priority")
            pri_counts = filtered_df["Priority"].value_counts().reset_index()
            pri_counts.columns = ["Priority", "Count"]
            st.bar_chart(pri_counts.set_index("Priority"))

    if "Status" in filtered_df.columns:
        with chart_col2:
            st.markdown("#### Bugs by Status")
            status_counts = filtered_df["Status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            st.bar_chart(status_counts.set_index("Status"))

    # --- Trend Chart: Bugs Created over Time ---
    if "Created" in filtered_df.columns:
        st.markdown("#### Bugs Created Over Time")
        created_df = (
            filtered_df.dropna(subset=["Created"])
            .set_index("Created")
            .resample("D")["Issue key"]
            .count()
            .reset_index()
        )
        created_df.columns = ["Created Date", "Bug Count"]
        if not created_df.empty:
            st.line_chart(created_df.set_index("Created Date"))

    st.markdown("---")

    # --- Detailed Table ---
    st.subheader("📋 Bug Details")

    display_cols = []
    for col in ["Issue key", "Summary", "Status", "Priority", "Assignee", "Environment", "Created", "Updated"]:
        if col in filtered_df.columns:
            display_cols.append(col)

    if display_cols:
        st.dataframe(
            filtered_df[display_cols].sort_values(
                by="Priority" if "Priority" in display_cols else display_cols[0]
            ),
            use_container_width=True,
        )
    else:
        st.write("Could not find standard Jira columns to display. Please check your CSV structure.")

    # --- Download filtered data ---
    st.download_button(
        "📥 Download Filtered Bugs (CSV)",
        data=filtered_df.to_csv(index=False),
        file_name="V6_Bugs_Filtered.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
