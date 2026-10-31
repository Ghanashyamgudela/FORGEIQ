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

API_URL = "http://127.0.0.1:8000"

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


# --------------------------------
# HEADER
# --------------------------------

st.title("🏭 FORGEIQ")
st.subheader("Manufacturing Production Intelligence")
st.caption("Production scheduling | Machine allocation | Operations monitoring")

st.divider()

# --------------------------------
# FETCH DATA
# --------------------------------

try:
    metrics = get_metrics()
    schedules = get_schedules()

except requests.exceptions.RequestException as error:
    st.error("Cannot connect to the FORGEIQ API.")
    st.write("Make sure your FastAPI server is running.")
    st.code("uvicorn api.main:app --reload")
    st.caption(f"Connection details: {error}")
    st.stop()

    schedule_df = pd.DataFrame(schedules)

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

                    # --------------------------------
                    # MACHINE WORKLOAD CHART
                    # --------------------------------

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

                        timeline.update_yaxes(autorange="reversed")

                        timeline.update_layout(
                            xaxis_title="Production Time",
                            yaxis_title="Machine",
                            legend_title="Schedule Status"
                        )

                        st.plotly_chart(timeline, use_container_width=True)

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

                        # --------------------------------
                        # FOOTER
                        # --------------------------------

                        st.divider()

                        st.caption(
                            "FORGEIQ | Manufacturing Scheduling Intelligence | "
                            "Powered by Python, OR-Tools, FastAPI and Streamlit"
                        )
