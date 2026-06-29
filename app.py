from datetime import datetime
from db_connection import get_db_connection
import mysql.connector

def run_slot_booking(user_id, charger_id, start_str, end_str):
    """Executes safe concurrent slot reservation using MySQL Stored Procedure."""
    conn = get_db_connection()
    if not conn:
        print("System execution halted: Database offline.")
        return
    cursor = conn.cursor()
    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
        
        # Out parameter (p_success_flag) is initialized to 0
        args = [user_id, charger_id, start_dt, end_dt, 0]
        result_args = cursor.callproc('BookChargingSlot', args)
        
        # In MySQL connector Python, callproc returns the arguments list with modified OUT params
        success_status = result_args[4]
        
        if success_status == 1:
            print(f"✨ Booking Confirmed! Charger {charger_id} locked for User {user_id}.")
        else:
            print("❌ Booking Failed: Charger occupied or timing conflict.")
            
    except mysql.connector.Error as err:
        print(f"Execution Error occurred: {err}")
    except ValueError as val_err:
        print(f"Datetime formatting error: {val_err}. Please use YYYY-MM-DD HH:MM:SS format.")
    finally:
        cursor.close()
        conn.close()

def view_live_tariffs():
    """Queries the LiveTariffGrid view to show current dynamic prices."""
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM LiveTariffGrid")
        rows = cursor.fetchall()
        print("\n--- Live Grid Tariffs (Dynamic Pricing) ---")
        print(f"{'Station ID':<12} | {'City':<15} | {'Location':<20} | {'Tariff (PKR/kWh)':<18}")
        print("-" * 72)
        for row in rows:
            print(f"{row[0]:<12} | {row[1]:<15} | {row[2]:<20} | {row[3]:<18}")
    except mysql.connector.Error as err:
        print(f"Failed to query LiveTariffGrid view: {err}")
    finally:
        cursor.close()
        conn.close()

def check_charging_stations():
    """Displays charging stations and current real-time load management."""
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT station_id, city, location_area, max_grid_capacity_kw, current_load_kw FROM charging_stations")
        rows = cursor.fetchall()
        print("\n--- Charging Station Grid Load & Capacity ---")
        print(f"{'ID':<4} | {'City':<15} | {'Location Area':<20} | {'Max Cap (kW)':<12} | {'Current Load (kW)':<17}")
        print("-" * 77)
        for row in rows:
            print(f"{row[0]:<4} | {row[1]:<15} | {row[2]:<20} | {row[3]:<12} | {row[4]:<17}")
    except mysql.connector.Error as err:
        print(f"Failed to fetch charging stations: {err}")
    finally:
        cursor.close()
        conn.close()

def display_menu():
    print("\n=============================================")
    print("      EV GRID OPTIMIZER TEST INTERFACE       ")
    print("=============================================")
    print("1. Book a Charging Slot (Stored Procedure)")
    print("2. View Live Dynamic Tariffs (LiveTariffGrid View)")
    print("3. Check Station Grid Loads & Capacities")
    print("4. Quick Test (Run default slot booking check)")
    print("5. Exit")
    print("=============================================")

if __name__ == "__main__":
    while True:
        display_menu()
        choice = input("Select an option (1-5): ").strip()
        
        if choice == '1':
            try:
                user_id = int(input("Enter User ID (e.g. 1): "))
                charger_id = int(input("Enter Charger ID (e.g. 1): "))
                start_str = input("Enter Start Time (YYYY-MM-DD HH:MM:SS) (e.g. 2026-06-29 18:00:00): ").strip()
                end_str = input("Enter End Time (YYYY-MM-DD HH:MM:SS) (e.g. 2026-06-29 19:00:00): ").strip()
                print("\nExecuting booking transaction...")
                run_slot_booking(user_id, charger_id, start_str, end_str)
            except ValueError:
                print("Invalid input format. User ID and Charger ID must be integers.")
                
        elif choice == '2':
            view_live_tariffs()
            
        elif choice == '3':
            check_charging_stations()
            
        elif choice == '4':
            print("\nRunning quick test from project blueprint: Booking default slot...")
            run_slot_booking(1, 1, "2026-06-26 18:00:00", "2026-06-26 19:00:00")
            
        elif choice == '5':
            print("Exiting EV Grid Optimizer interface. Goodbye!")
            break
        else:
            print("Invalid selection. Please choose an option between 1 and 5.")
