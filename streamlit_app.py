import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import mysql.connector
from db_connection import get_db_connection

# Page Configuration
st.set_page_config(
    page_title="EV Grid Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
    <style>
    .main {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #4facfe, #00f2fe);
    }
    .metric-card {
        background-color: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- Helper Functions -----------------

def run_slot_booking_db(user_id, charger_id, start_dt, end_dt):
    conn = get_db_connection()
    if not conn:
        return False, "Database connection offline."
    cursor = conn.cursor()
    try:
        args = [int(user_id), int(charger_id), start_dt, end_dt, 0]
        result_args = cursor.callproc('BookChargingSlot', args)
        success_status = result_args[4]
        if success_status == 1:
            # Re-update the charger status to 'Occupied' for immediate load visualization test
            cursor.execute("UPDATE chargers SET status = 'Occupied' WHERE charger_id = %s", (charger_id,))
            conn.commit()
            return True, "Booking Confirmed successfully!"
        else:
            return False, "Booking Failed: Charger occupied or timing conflict."
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        cursor.close()
        conn.close()

# ----------------- Header Section -----------------
st.title("⚡ Smart EV Charging Network & Grid Optimizer")
st.caption("Pakistan Power Grid Optimization & Load Management (NEPRA / K-Electric / WAPDA)")

# ----------------- Database Status Check -----------------
conn_test = get_db_connection()
if conn_test:
    st.sidebar.success("🟢 Connected to Cloud MySQL Database")
    conn_test.close()
else:
    st.sidebar.error("🔴 Database Offline")
    st.sidebar.info("""
    **To configure the database on Streamlit Cloud:**
    1. Go to your Streamlit Share Dashboard settings for this app.
    2. Open **Secrets** and paste your credentials:
    ```toml
    DB_HOST = "your-cloud-host"
    DB_NAME = "EV_Grid_Optimizer"
    DB_USER = "your-user"
    DB_PASS = "your-password"
    DB_PORT = "3306"
    ```
    """)

# ----------------- Current Tariff Calculation -----------------
current_hour = datetime.now().hour
is_peak = 17 <= current_hour < 23
current_rate = 75.00 if is_peak else 50.00

# Sidebar Metrics
st.sidebar.header("Grid Status")
st.sidebar.metric(
    label="Current Tariff Rate", 
    value=f"PKR {current_rate:.2f} / kWh", 
    delta="PEAK RATE ACTIVE" if is_peak else "Off-Peak Hours",
    delta_color="inverse" if is_peak else "normal"
)

# ----------------- Main Dashboard Tabs -----------------
tab1, tab2 = st.tabs(["📊 Live Monitoring", "📅 Book Charging Slot"])

with tab1:
    col1, col2 = st.columns([1.2, 0.8])
    
    with col1:
        st.subheader("Station Grid Load Management")
        conn = get_db_connection()
        if conn:
            try:
                # Query stations with dynamic load aggregation
                query_stations = """
                    SELECT s.station_id, s.city, s.location_area, s.max_grid_capacity_kw,
                           COALESCE(SUM(CASE WHEN c.status = 'Occupied' THEN c.power_output_kw ELSE 0 END), 0) AS current_load_kw
                    FROM charging_stations s
                    LEFT JOIN chargers c ON s.station_id = c.station_id
                    GROUP BY s.station_id, s.city, s.location_area, s.max_grid_capacity_kw
                """
                df_stations = pd.read_sql(query_stations, conn)
                for index, row in df_stations.iterrows():
                    load_pct = min(100, int((row['current_load_kw'] / row['max_grid_capacity_kw']) * 100))
                    
                    with st.container():
                        st.markdown(f"**{row['location_area']} ({row['city']})**")
                        st.progress(load_pct / 100.0)
                        st.write(f"Capacity: {row['current_load_kw']} kW / {row['max_grid_capacity_kw']} kW ({load_pct}% load)")
                        st.markdown("---")
            except Exception as e:
                st.error(f"Error fetching stations: {e}")
            finally:
                conn.close()
        else:
            st.warning("Connect a database to view live stations grid load.")

    with col2:
        st.subheader("Charger Status Board")
        conn = get_db_connection()
        if conn:
            try:
                df_chargers = pd.read_sql("""
                    SELECT c.charger_id, c.connector_type, c.power_output_kw, c.status, s.location_area
                    FROM chargers c
                    JOIN charging_stations s ON c.station_id = s.station_id
                """, conn)
                
                for index, row in df_chargers.iterrows():
                    status_emoji = "🟢" if row['status'] == 'Available' else "🟡" if row['status'] == 'Occupied' else "🔴"
                    st.markdown(f"{status_emoji} **Charger #{row['charger_id']}** ({row['connector_type']})")
                    st.caption(f"{row['location_area']} | {row['power_output_kw']} kW | Status: {row['status']}")
            except Exception as e:
                st.error(f"Error fetching chargers: {e}")
            finally:
                conn.close()
        else:
            st.warning("Connect a database to view charger status.")

with tab2:
    st.subheader("Schedule an EV Reservation")
    
    conn = get_db_connection()
    if conn:
        try:
            # Load dropdown selections
            df_users = pd.read_sql("SELECT user_id, owner_name, car_model FROM users_and_evs", conn)
            df_available_chargers = pd.read_sql("""
                SELECT c.charger_id, c.connector_type, s.location_area 
                FROM chargers c 
                JOIN charging_stations s ON c.station_id = s.station_id
                WHERE c.status = 'Available'
            """, conn)
            
            user_options = {row['user_id']: f"{row['owner_name']} ({row['car_model']})" for idx, row in df_users.iterrows()}
            charger_options = {row['charger_id']: f"Charger #{row['charger_id']} [{row['connector_type']}] - {row['location_area']}" for idx, row in df_available_chargers.iterrows()}
            
            if not charger_options:
                st.warning("No chargers are currently available for booking.")
            else:
                with st.form("booking_form"):
                    selected_user = st.selectbox("Select EV Owner", options=list(user_options.keys()), format_func=lambda x: user_options[x])
                    selected_charger = st.selectbox("Select Charger", options=list(charger_options.keys()), format_func=lambda x: charger_options[x])
                    
                    col_start, col_end = st.columns(2)
                    with col_start:
                        start_date = st.date_input("Start Date", datetime.now().date())
                        start_time = st.time_input("Start Time", datetime.now().time())
                    with col_end:
                        end_date = st.date_input("End Date", datetime.now().date())
                        end_time = st.time_input("End Time", (datetime.now() + timedelta(hours=1)).time())
                    
                    submit_button = st.form_submit_button("Confirm Booking")
                    
                    if submit_button:
                        start_dt = datetime.combine(start_date, start_time)
                        end_dt = datetime.combine(end_date, end_time)
                        
                        if start_dt >= end_dt:
                            st.error("End time must be after start time.")
                        else:
                            success, msg = run_slot_booking_db(selected_user, selected_charger, start_dt, end_dt)
                            if success:
                                st.success(msg)
                                st.balloons()
                            else:
                                st.error(msg)
        except Exception as e:
            st.error(f"Error loading booking form data: {e}")
        finally:
            conn.close()
    else:
        st.warning("Please connect a database to submit a booking slot reservation.")
