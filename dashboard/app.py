import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# --------------------------------
# PAGE CONFIGURATION
# --------------------------------

st.set_page_config(
    page_title="FORGEIQ | Manufacturing Dashboard",
    page_icon="🏭",
    layout="wide"
)

API_URL = "http://127.0.0.1:8001"

st.markdown(
    """
    <style>
    :root {
        --forge-bg: #0b1115;
        --forge-panel: #121b21;
        --forge-panel-raised: #172229;
        --forge-line: #293840;
        --forge-text: #e3ebef;
        --forge-muted: #93a4ad;
        --forge-teal: #39b6a2;
        --forge-amber: #e9ad4a;
    }

    .stApp {
        color: var(--forge-text);
        background:
            radial-gradient(ellipse at 12% 0%, rgba(57, 182, 162, 0.09), transparent 34%),
            var(--forge-bg);
    }

    [data-testid="stHeader"] {
        background: rgba(11, 17, 21, 0.82);
    }

    .main .block-container {
        max-width: 1540px;
        padding: 2rem 2rem 3rem;
    }

    h1, h2, h3 {
        color: var(--forge-text);
        font-family: Bahnschrift, "Aptos Display", "Segoe UI", sans-serif;
        font-weight: 650;
    }

    h1 {
        padding-bottom: 0.55rem;
        border-bottom: 1px solid var(--forge-line);
    }

    h2 {
        margin-top: 0.35rem;
        padding-left: 0.7rem;
        border-left: 3px solid var(--forge-teal);
    }

    

    [data-testid="stSidebar"] {
        background: #10181d;
        border-right: 1px solid var(--forge-line);
    }

    [data-testid="stSidebar"] h1 {
        border-bottom: 0;
        padding-bottom: 0;
    }

    [data-testid="stSidebar"] a[href^="#"] {
        display: block;
        padding: 0.58rem 0.7rem;
        color: #c6d3d9;
        text-decoration: none;
        border: 1px solid transparent;
        border-radius: 5px;
        transition: background-color 140ms ease, color 140ms ease, border-color 140ms ease;
    }

    [data-testid="stSidebar"] a[href^="#"]:hover {
        color: #f1f7f8;
        background: #19272d;
        border-color: #31514f;
    }

    [data-testid="stMetric"] {
        min-height: 104px;
        padding: 0.9rem 1rem;
        background: linear-gradient(145deg, var(--forge-panel-raised), var(--forge-panel));
        border: 1px solid var(--forge-line);
        border-radius: 6px;
    }

    [data-testid="stMetricLabel"] {
        color: var(--forge-muted);
        font-size: 0.84rem;
    }

    [data-testid="stMetricValue"] {
        color: var(--forge-text);
        font-family: Bahnschrift, "Aptos Display", "Segoe UI", sans-serif;
        font-variant-numeric: tabular-nums;
    }

    [data-testid="stPlotlyChart"] {
        overflow: hidden;
        border: 1px solid var(--forge-line);
        border-radius: 6px;
        background: #111820;
    }

    [data-testid="stDataFrame"] {
        overflow: hidden;
        border: 1px solid var(--forge-line);
        border-radius: 6px;
    }

    [data-baseweb="select"] > div {
        background: var(--forge-panel);
        border-color: var(--forge-line);
    }

    [data-testid="stButton"] > button {
        min-height: 2.7rem;
        border-radius: 5px;
        font-weight: 650;
    }

    [data-testid="stButton"] > button[kind="primary"] {
        color: #10201e;
        background: var(--forge-teal);
        border-color: var(--forge-teal);
    }

    [data-testid="stButton"] > button[kind="primary"]:hover {
        color: #081412;
        background: #54cbb7;
        border-color: #54cbb7;
    }

    [data-testid="stAlert"] {
        border: 1px solid var(--forge-line);
        border-left: 3px solid var(--forge-amber);
        border-radius: 5px;
        background: var(--forge-panel);
    }

    hr {
        border-color: var(--forge-line);
    }

    @media (max-width: 700px) {
        .main .block-container {
            padding: 1.2rem 1rem 2rem;
        }

        [data-testid="stMetric"] {
            min-height: 90px;
            padding: 0.7rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

px.defaults.template = "plotly_dark"
px.defaults.color_discrete_sequence = [
    "#39B6A2",
    "#E9AD4A",
    "#4F91C9",
    "#E06B60",
    "#9AAAB3",
]
px.defaults.color_continuous_scale = [
    "#174D48",
    "#39B6A2",
    "#E9AD4A",
]

# --------------------------------
# DATA LOADING
# --------------------------------

@st.cache_data(ttl=30)
def get_metrics():
    response = requests.get(f"{API_URL}/metrics", timeout=10)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30)
def get_schedules():
    response = requests.get(
        f"{API_URL}/schedules",
        params={"limit": 500, "offset": 0},
        timeout=15
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30)
def get_violations():
    response = requests.get(
        f"{API_URL}/violations",
        timeout=15
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30)
def get_decision_trace(status=None):
    params = {
        "limit": 25000,
        "offset": 0,
    }
    if status:
        params["status"] = status
    response = requests.get(
        f"{API_URL}/decision-trace",
        params=params,
        timeout=30
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30)
def get_schedule_runs():
    response = requests.get(
        f"{API_URL}/schedule-runs",
        timeout=15
    )
    response.raise_for_status()
    return response.json()


# --------------------------------
# HEADER
# --------------------------------

st.title("🏭 FORGEIQ")
st.subheader("Manufacturing Production Intelligence")
st.caption("Production scheduling | Machine allocation | Operations monitoring")

st.divider()

# --------------------------------
# SIDEBAR
# --------------------------------
with st.sidebar:
    st.title("🏭 FORGEIQ")
    st.caption("Manufacturing Intelligence")
    st.divider()
    st.subheader("Navigation")
    st.markdown(
        """
        <div style="display:flex; flex-direction:column; gap:12px;">
            <a href="#production-overview">📊 Production Overview</a>
            <a href="#scheduling-summary">⚙️ Scheduling Summary</a>
            <a href="#production-schedule-timeline">📅 Production Timeline</a>
            <a href="#machine-utilization-analytics">🏭 Machine Utilization</a>
            <a href="#schedule-explainability-center">🔍 Schedule Explainability</a>
            <a href="#constraint-monitoring-center">🚨 Constraint Monitoring</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.subheader("System Status")
    st.success("Dashboard interface active")
    st.info("API: http://127.0.0.1:8001")
    st.divider()
    st.subheader("Optimization Control")
    if st.button(
        "▶ Run Pilot Optimization",
        use_container_width=True,
        type="primary"
    ):
        try:
            with st.spinner(
                "OR-Tools is optimizing the production schedule..."
            ):
                response = requests.post(
                    f"{API_URL}/optimize",
                    timeout=600
                )
                response.raise_for_status()
                result = response.json()

            get_metrics.clear()
            get_schedules.clear()
            get_violations.clear()
            get_decision_trace.clear()
            get_schedule_runs.clear()
            st.success("Optimization request completed.")
            get_schedules.clear()
            get_decision_trace.clear()
            get_schedule_runs.clear()

            st.rerun()
            st.write("**Solver Status:**", result.get("status"))
            st.write(
                "**Scheduled Operations:**",
                result.get("scheduled_operations")
            )
            st.write(
                "**Makespan:**",
                result.get("makespan_minutes"),
                "minutes"
            )
            st.write(
                "**Solver Time:**",
                result.get("solver_time_seconds"),
                "seconds"
            )
        except requests.exceptions.RequestException as error:
            st.error(f"Optimization request failed: {error}")

    st.divider()
    st.caption("FORGEIQ | Pilot Version")
    st.caption("Powered by Python · OR-Tools · FastAPI")

# --------------------------------
# FETCH DATA
# --------------------------------

try:
    metrics = get_metrics()
    schedules = get_schedules()
    violations_data = get_violations()
    decision_trace_data = get_decision_trace()
    schedule_runs = get_schedule_runs()

except requests.exceptions.RequestException as error:
    st.error("Cannot connect to the FORGEIQ API.")
    st.write("Make sure your FastAPI server is running.")
    st.code("uvicorn api.main:app --reload")
    st.caption(f"Connection details: {error}")
    st.stop()

st.write("Schedule runs loaded:", len(schedule_runs))

schedule_df = pd.DataFrame(schedules)

# Calculate predicted completion time for each production order.
schedule_df["end_time"] = pd.to_datetime(schedule_df["end_time"])
order_completion = (
    schedule_df.groupby("order_id", as_index=False)
    .agg(predicted_completion=("end_time", "max"))
)
orders_df = pd.read_csv(
    "data/raw/production_orders.csv"
)
orders_df["due_date"] = pd.to_datetime(orders_df["due_date"])
delivery_df = orders_df.merge(
    order_completion,
    on="order_id",
    how="inner",
)
delivery_df["delay_hours"] = (
    delivery_df["predicted_completion"] - delivery_df["due_date"]
).dt.total_seconds() / 3600
delivery_df["delivery_status"] = delivery_df["delay_hours"].apply(
    lambda hours: "LATE" if hours > 0 else "ON TIME"
)


def classify_delivery_risk(hours):
    if hours <= 0:
        return "ON TRACK"
    elif hours <= 24:
        return "LOW"
    elif hours <= 72:
        return "MEDIUM"
    else:
        return "HIGH"


delivery_df["risk_level"] = delivery_df["delay_hours"].apply(
    classify_delivery_risk
)

st.markdown("---")
st.subheader("📚 Schedule Run History")
if schedule_runs:
    complete_runs = sum(
        run["import_status"] == "COMPLETE"
        for run in schedule_runs
    )
    partial_runs = sum(
        run["import_status"] == "PARTIAL"
        for run in schedule_runs
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Runs", len(schedule_runs))
    col2.metric("Complete Runs", complete_runs)
    col3.metric("Partial Runs", partial_runs)

    status_filter = st.selectbox(
        "Filter runs by import status",
        ["ALL", "COMPLETE", "PARTIAL", "PENDING"],
    )
    filtered_runs = [
        run for run in schedule_runs
        if status_filter == "ALL"
        or run["import_status"] == status_filter
    ]

    run_history_df = pd.DataFrame(filtered_runs)
    st.caption(f"Total optimization runs: {len(schedule_runs)}")
    st.dataframe(
        run_history_df[
            [
                "run_id",
                "created_at",
                "solver_status",
                "makespan_minutes",
                "scheduled_operations",
                "imported_operations",
                "import_status",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    if filtered_runs:
        comparison_df = pd.DataFrame(filtered_runs)
        st.markdown("#### Run Makespan Comparison")
        comparison_df = comparison_df.dropna(
            subset=["makespan_minutes"]
        )
        if not comparison_df.empty:
            chart_df = comparison_df[
                ["run_id", "makespan_minutes"]
            ].set_index("run_id")
            st.bar_chart(chart_df)

        if schedule_runs:
            st.markdown("#### Inspect an Optimization Run")
            run_options = {
                run["run_id"]: run
                for run in schedule_runs
            }
            selected_run_id = st.selectbox(
                "Select a run",
                list(run_options.keys()),
            )
            selected_run = run_options[selected_run_id]
            col1, col2, col3 = st.columns(3)
            col1.metric(
                "Solver Status",
                selected_run["solver_status"],
            )
            col2.metric(
                "Planned Operations",
                selected_run["scheduled_operations"],
            )
            col3.metric(
                "Imported Operations",
                selected_run["imported_operations"],
            )
            st.write("Import Status:", selected_run["import_status"])

            planned = selected_run["scheduled_operations"]
            imported = selected_run["imported_operations"]
            import_percentage = (
                imported / planned * 100
                if planned > 0
                else 0
            )
            st.progress(
                int(import_percentage),
                text=f"Import completion: {import_percentage:.1f}%",
            )

            if schedule_runs:
                export_df = pd.DataFrame(schedule_runs)
                csv_data = export_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Run History (CSV)",
                    data=csv_data,
                    file_name="forgeiq_schedule_run_history.csv",
                    mime="text/csv",
                )
else:
    st.info("No schedule runs found yet.")

# --------------------------------
# DATA PREPARATION
# --------------------------------

if not schedule_df.empty:
    schedule_df["start_time"] = pd.to_datetime(
        schedule_df["start_time"]
    )

    schedule_df["end_time"] = pd.to_datetime(
        schedule_df["end_time"]
    )

    # --------------------------------
    # KPI SECTION
    # --------------------------------

    st.header("Production Overview")

    scheduled_operations = len(schedule_df)
    total_pilot_operations = 80
    scheduling_efficiency = (
        scheduled_operations / total_pilot_operations * 100
        if total_pilot_operations > 0
        else 0
    )
    average_operation_duration = (
        schedule_df["duration_minutes"].mean()
        if not schedule_df.empty
        else 0
    )
    total_scheduled_minutes = (
        schedule_df["duration_minutes"].sum()
        if not schedule_df.empty
        else 0
    )
    total_scheduled_hours = total_scheduled_minutes / 60
    if not schedule_df.empty:
        production_makespan_hours = (
            schedule_df["end_time"].max()
            - schedule_df["start_time"].min()
        ).total_seconds() / 3600
    else:
        production_makespan_hours = 0

    scheduled_orders = (
        schedule_df["order_id"].nunique()
        if not schedule_df.empty else 0
    )

    machines_used = (
        schedule_df["machine_id"].nunique()
        if not schedule_df.empty else 0
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Products", metrics["total_products"])
    col2.metric("Production Orders", metrics["total_orders"])
    col3.metric("Machines", metrics["total_machines"])
    col4.metric("Materials", metrics["total_materials"])

    col5, col6, col7 = st.columns(3)

    col5.metric("Total Operations", metrics["total_operations"])
    col6.metric("Scheduled Operations", scheduled_operations)
    col7.metric("Orders in Schedule", scheduled_orders)

    col8, col9, col10, col11 = st.columns(4)
    col8.metric(
        "Scheduling Efficiency",
        f"{scheduling_efficiency:.1f}%",
    )
    col8.progress(
        min(100, max(0, int(scheduling_efficiency))),
        text=f"Scheduling Coverage: {scheduling_efficiency:.1f}%",
    )
    col9.metric(
        "Average Operation Duration",
        f"{average_operation_duration:.1f} min",
    )
    col10.metric(
        "Total Scheduled Processing Time",
        f"{total_scheduled_hours:.1f} hours",
    )
    col11.metric(
        "Production Makespan",
        f"{production_makespan_hours:.1f} hours",
    )

    st.divider()

    # --------------------------------
    # SCHEDULE SUMMARY
    # --------------------------------

    st.header("Scheduling Summary")

    if schedule_df.empty:

        st.warning("No scheduled operations are available yet.")

    else:

        left, right = st.columns(2)

        with left:
            st.metric("Machines Allocated", machines_used)
        with right:
            st.metric(
                "Unscheduled Operations (Pilot)",
                max(0, 80 - scheduled_operations)
            )

        st.subheader("Operations Assigned per Machine")
        machine_counts = (
            schedule_df.groupby("machine_id")
            .size()
            .reset_index(name="operations")
            .sort_values("operations", ascending=False)
        )

        machine_chart = px.bar(
            machine_counts,
            x="machine_id",
            y="operations",
            color="operations",
            title="Scheduled Operations by Machine",
            labels={
                "machine_id": "Machine",
                "operations": "Number of Operations"
            }
        )

        machine_chart.update_layout(
            xaxis_title="Machine",
            yaxis_title="Scheduled Operations",
            showlegend=False
        )
        st.plotly_chart(machine_chart, use_container_width=True)

        st.divider()

        # --------------------------------
        # PRODUCTION TIMELINE
        # --------------------------------

        st.header("Production Schedule Timeline")

        machine_options = ["All Machines"] + sorted(
            schedule_df["machine_id"].dropna().unique().tolist()
        )

        selected_machine = st.selectbox(
            "Filter by Machine",
            machine_options
        )

        timeline_df = schedule_df.copy()
        if selected_machine != "All Machines":
            timeline_df = timeline_df[
                timeline_df["machine_id"] == selected_machine
            ]

        if not timeline_df.empty:
            timeline = px.timeline(
                timeline_df,
                x_start="start_time",
                x_end="end_time",
                y="machine_id",
                color="status",
                hover_data=[
                    "operation_id",
                    "order_id",
                    "machine_id",
                    "status"
                ],
                title="Machine-wise Production Schedule"
            )

            timeline.update_layout(
                height=680,
                paper_bgcolor="#0E1117",
                plot_bgcolor="#11151D",
                title=dict(
                    text="Machine-wise Production Schedule",
                    x=0.02,
                    xanchor="left",
                    y=0.98,
                    yanchor="top",
                    font=dict(size=15),
                ),
                font=dict(
                    family="Arial",
                    size=12,
                    color="#DCE4EE",
                ),
                margin=dict(l=30, r=25, t=85, b=35),
                xaxis=dict(
                    title="Production Time",
                    showgrid=True,
                    gridcolor="rgba(150, 170, 190, 0.15)",
                    zeroline=False,
                ),
                yaxis=dict(
                    title="Machine",
                    showgrid=True,
                    gridcolor="rgba(150, 170, 190, 0.08)",
                    autorange="reversed",
                    automargin=True,
                ),
                legend=dict(
                    title="Schedule Status",
                    orientation="h",
                    yanchor="bottom",
                    y=1.08,
                    xanchor="right",
                    x=1,
                ),
            )
            timeline.update_traces(
                marker_line_width=0,
                opacity=0.95,
            )
            st.plotly_chart(
                timeline,
                use_container_width=True,
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                },
            )

        st.divider()

        # --------------------------------
        # SCHEDULE TABLE
        # --------------------------------

        st.header("Scheduled Operations")

        st.dataframe(
            schedule_df.sort_values("start_time"),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        st.subheader("🚚 Predicted Delivery Performance")
        total_orders = len(delivery_df)
        late_orders = (delivery_df["delivery_status"] == "LATE").sum()
        on_time_orders = (delivery_df["delivery_status"] == "ON TIME").sum()
        on_time_percentage = (
            on_time_orders / total_orders * 100
            if total_orders > 0
            else 0
        )
        col1, col2, col3 = st.columns(3)
        col1.metric("Orders Evaluated", total_orders)
        col2.metric("Predicted On-Time", int(on_time_orders))
        col3.metric("Predicted Late", int(late_orders))
        st.metric(
            "Predicted On-Time Rate",
            f"{on_time_percentage:.1f}%",
        )

        st.markdown("#### Delivery Risk Summary")
        risk_counts = delivery_df["risk_level"].value_counts()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("On Track", int(risk_counts.get("ON TRACK", 0)))
        col2.metric("Low Risk", int(risk_counts.get("LOW", 0)))
        col3.metric("Medium Risk", int(risk_counts.get("MEDIUM", 0)))
        col4.metric("High Risk", int(risk_counts.get("HIGH", 0)))

        st.markdown("#### Delivery Risk by Priority")
        priority_risk = (
            delivery_df.groupby(["priority", "delivery_status"])
            .size()
            .unstack(fill_value=0)
        )
        st.bar_chart(priority_risk)

        st.markdown("#### Delivery Status Breakdown")
        status_counts = (
            delivery_df["delivery_status"]
            .value_counts()
            .reindex(["ON TIME", "LATE"], fill_value=0)
        )
        st.bar_chart(status_counts)

        st.markdown("#### Order Delivery Risk")
        delivery_table = delivery_df[
            [
                "order_id",
                "priority",
                "due_date",
                "predicted_completion",
                "delay_hours",
                "delivery_status",
                "risk_level",
            ]
        ].copy()
        delivery_table["delay_hours"] = (
            delivery_table["delay_hours"].round(2)
        )
        delivery_table = delivery_table.sort_values(
            "delay_hours",
            ascending=False,
        )

        st.markdown("#### Filter Delivery Risks")
        show_late_only = st.checkbox(
            "Show only late orders",
            value=False,
        )
        risk_filter = st.selectbox(
            "Filter by risk level",
            ["ALL", "ON TRACK", "LOW", "MEDIUM", "HIGH"],
        )
        if show_late_only:
            filtered_delivery_df = delivery_table[
                delivery_table["delivery_status"] == "LATE"
            ]
        else:
            filtered_delivery_df = delivery_table
        if risk_filter != "ALL":
            filtered_delivery_df = filtered_delivery_df[
                filtered_delivery_df["risk_level"] == risk_filter
            ]

        st.dataframe(
            filtered_delivery_df,
            use_container_width=True,
            hide_index=True,
        )

        # --------------------------------
        # PRODUCTION ORDER TRACKING
        # --------------------------------

        st.divider()
        st.header("Production Order Tracking")
        total_pilot_orders = schedule_df["order_id"].nunique()
        total_pilot_operations = len(schedule_df)
        completed_operations = (
            schedule_df["status"]
            .astype(str)
            .str.upper()
            .eq("COMPLETED")
            .sum()
        )
        in_progress_operations = (
            schedule_df["status"]
            .astype(str)
            .str.upper()
            .isin(["IN_PROGRESS", "IN PROGRESS"])
            .sum()
        )
        scheduled_count = (
            schedule_df["status"]
            .astype(str)
            .str.upper()
            .eq("SCHEDULED")
            .sum()
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pilot Orders", total_pilot_orders)
        col2.metric("Scheduled Operations", scheduled_count)
        col3.metric("Completed Operations", completed_operations)
        col4.metric("In Progress", in_progress_operations)

        scheduling_coverage = (
            scheduled_count / total_pilot_operations * 100
            if total_pilot_operations else 0
        )
        st.subheader("Pilot Scheduling Coverage")
        st.progress(scheduling_coverage / 100)
        st.caption(
            f"{scheduling_coverage:.1f}% of pilot operations "
            "have been assigned a schedule."
        )
        st.info(
            "Execution progress is not yet available. "
            "All 80 pilot operations currently have SCHEDULED status. "
            "Completion and in-progress figures will update when "
            "shop-floor execution data is integrated."
        )

st.divider()
st.header("Machine Utilization Analytics")

if schedule_df.empty:
    st.info("Machine utilization is unavailable without scheduled operations.")
else:
    machine_workload = (
        schedule_df.groupby("machine_id", as_index=False)
        .agg(
            scheduled_minutes=("duration_minutes", "sum"),
            scheduled_operations=("operation_id", "count"),
        )
    )
    calendar_df = pd.read_csv("data/raw/machine_calendars.csv")
    calendar_df["is_working"] = (
        calendar_df["is_working"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes"])
    )
    calendar_df["available_minutes"] = pd.to_numeric(
        calendar_df["available_minutes"],
        errors="coerce",
    ).fillna(0)
    available_capacity = (
        calendar_df[calendar_df["is_working"]]
        .groupby("machine_id")["available_minutes"]
        .sum()
        .reset_index(name="available_minutes")
    )
    machine_workload = machine_workload.merge(
        available_capacity,
        on="machine_id",
        how="left",
    )
    machine_workload["available_minutes"] = machine_workload[
        "available_minutes"
    ].fillna(0)
    machine_workload["utilization_pct"] = (
        machine_workload["scheduled_minutes"]
        .div(machine_workload["available_minutes"].where(
            machine_workload["available_minutes"] > 0
        ))
        .mul(100)
        .fillna(0)
    )

    def classify_machine_load(utilization):
        if utilization >= 90:
            return "CRITICAL"
        elif utilization >= 75:
            return "HIGH"
        elif utilization >= 50:
            return "MODERATE"
        else:
            return "LOW"

    machine_workload["load_status"] = (
        machine_workload["utilization_pct"]
        .apply(classify_machine_load)
    )
    st.caption(
        "Load thresholds are configurable dashboard settings, "
        "not fixed industry standards."
    )
    utilization_df = machine_workload.sort_values(
        "utilization_pct",
        ascending=False
    )

    if utilization_df.empty:
        st.warning("No working machine capacity was found for the schedule dates.")
    else:
        st.markdown("#### Machine Utilization (%)")
        utilization_chart = (
            machine_workload[
                ["machine_id", "utilization_pct"]
            ]
            .sort_values("utilization_pct", ascending=False)
            .set_index("machine_id")
        )
        st.bar_chart(utilization_chart)

        st.markdown("#### Machine Bottleneck Summary")
        bottleneck_counts = (
            machine_workload["load_status"]
            .value_counts()
            .reindex(
                ["CRITICAL", "HIGH", "MODERATE", "LOW"],
                fill_value=0,
            )
        )
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Critical", int(bottleneck_counts["CRITICAL"]))
        col2.metric("High", int(bottleneck_counts["HIGH"]))
        col3.metric("Moderate", int(bottleneck_counts["MODERATE"]))
        col4.metric("Low", int(bottleneck_counts["LOW"]))

        st.markdown("#### Machine Workload Details")
        machine_details = machine_workload[
            [
                "machine_id",
                "scheduled_operations",
                "scheduled_minutes",
                "available_minutes",
                "utilization_pct",
                "load_status",
            ]
        ].copy()
        machine_details["utilization_pct"] = (
            machine_details["utilization_pct"].round(2)
        )
        machine_details = machine_details.sort_values(
            "utilization_pct",
            ascending=False,
        )
        st.dataframe(
            machine_details,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Filter Machines by Load")
        load_filter = st.selectbox(
            "Select machine load category",
            ["ALL", "CRITICAL", "HIGH", "MODERATE", "LOW"],
        )
        if load_filter == "ALL":
            filtered_machine_df = machine_details
        else:
            filtered_machine_df = machine_details[
                machine_details["load_status"] == load_filter
            ]
        st.dataframe(
            filtered_machine_df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            label="📥 Download Machine Utilization Report",
            data=filtered_machine_df.to_csv(index=False).encode("utf-8"),
            file_name="forgeiq_machine_utilization_report.csv",
            mime="text/csv",
        )

# --------------------------------
# SCHEDULE EXPLAINABILITY CENTER
# --------------------------------
st.divider()
st.header("🔍 Schedule Explainability Center")
st.caption(
    "Explore the machine-shift candidates considered by the optimizer "
    "and inspect the final assignment for each operation."
)

if not schedule_df.empty:
    trace_records = decision_trace_data.get("records", [])
    trace_df = pd.DataFrame(trace_records)
    if trace_df.empty:
        st.warning("No decision-trace records are available.")
    else:
        operation_options = sorted(
            schedule_df["operation_id"]
            .dropna()
            .unique()
            .tolist()
        )
        selected_operation = st.selectbox(
            "Select Production Operation",
            operation_options,
            key="explainability_operation"
        )
        selected_record = schedule_df[
            schedule_df["operation_id"] == selected_operation
        ].iloc[0]
        operation_duration = (
            selected_record["end_time"] - selected_record["start_time"]
        ).total_seconds() / 60
        st.metric(
            "Operation Duration",
            f"{operation_duration:.0f} min"
        )

# --------------------------------
# CONSTRAINT MONITORING CENTER
# --------------------------------
st.divider()
st.header("🚨 Constraint Monitoring Center")
violations = violations_data.get("violations", [])
violations_df = pd.DataFrame(violations)
total_violations = violations_data.get(
    "total_violations", len(violations)
)
st.metric("Total Constraint Violations", total_violations)

if violations_df.empty:
    st.success("No constraint violations detected.")
else:
    # Severity chart
    severity_counts = (
        violations_df["severity"]
        .fillna("UNKNOWN")
        .value_counts()
        .reset_index()
    )
    severity_counts.columns = ["Severity", "Count"]
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Violations by Severity")
        severity_chart = px.pie(
            severity_counts,
            names="Severity",
            values="Count",
            hole=0.5,
            title="Severity Distribution",
        )
        st.plotly_chart(severity_chart, width="stretch")
    with col2:
        st.subheader("Violations by Constraint")
        issue_counts = (
            violations_df.groupby(["issue_type", "severity"])
            .size()
            .reset_index(name="Count")
            .sort_values("Count", ascending=True)
        )
        issue_chart = px.bar(
            issue_counts,
            x="Count",
            y="issue_type",
            color="severity",
            orientation="h",
            title="Violations by Constraint",
            color_discrete_map={
                "CRITICAL": "#DC4444",
                "HIGH": "#E49A36",
                "MEDIUM": "#3987CB",
                "LOW": "#2EAD72",
            },
            text="Count",
        )
        issue_chart.update_layout(
            xaxis_title="Number of Violations",
            yaxis_title="Constraint Type",
            legend_title="Severity",
        )
        st.plotly_chart(issue_chart, width="stretch")

    # --------------------------------
    # INDIVIDUAL VIOLATION DETAILS
    # --------------------------------
    st.divider()
    st.subheader("Violation Details")
    for _, violation in violations_df.iterrows():
        severity = str(violation.get("severity", "UNKNOWN"))
        issue_type = violation.get("issue_type", "Unknown")
        with st.expander(f"{severity} | {issue_type}"):
            st.write(
                "**Violation ID:**",
                violation.get("violation_id") or "Not assigned"
            )
            st.write(
                "**Affected schedules:**",
                violation.get("affected_schedule_ids", "N/A")
            )
            st.write(
                "**Explanation:**",
                violation.get("explanation", "N/A")
            )
            st.write(
                "**Recommended action:**",
                violation.get("recommended_action", "N/A")
            )
            st.write(
                "**Status:**",
                violation.get("status", "N/A")
            )

    # --------------------------------
    # COMPLETE VIOLATION REGISTER
    # --------------------------------
    st.divider()
    st.subheader("Complete Violation Register")
    st.dataframe(
        violations_df,
        width="stretch",
        hide_index=True
    )

# --------------------------------
# FOOTER
# --------------------------------

st.divider()

st.caption(
    "FORGEIQ | Manufacturing Scheduling Intelligence | "
    "Powered by Python, OR-Tools, FastAPI and Streamlit"
)
