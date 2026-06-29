from flask import Flask, jsonify, request, render_template, send_from_directory
import os
from datetime import datetime
from db_connection import get_db_connection
import mysql.connector

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/tariffs', methods=['GET'])
def get_tariffs():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM LiveTariffGrid")
        tariffs = cursor.fetchall()
        return jsonify(tariffs)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/stations', methods=['GET'])
def get_stations():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM charging_stations")
        stations = cursor.fetchall()
        return jsonify(stations)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/chargers', methods=['GET'])
def get_chargers():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.charger_id, c.station_id, c.connector_type, c.power_output_kw, c.status, s.city, s.location_area
            FROM chargers c
            JOIN charging_stations s ON c.station_id = s.station_id
        """)
        chargers = cursor.fetchall()
        return jsonify(chargers)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id, owner_name, car_model, battery_capacity_kwh, wallet_balance_pkr FROM users_and_evs")
        users = cursor.fetchall()
        return jsonify(users)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/book', methods=['POST'])
def book_slot():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    charger_id = data.get('charger_id')
    start_str = data.get('start_time')
    end_str = data.get('end_time')

    if not all([user_id, charger_id, start_str, end_str]):
        return jsonify({'error': 'Missing required booking fields'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database offline'}), 500
    cursor = conn.cursor()
    try:
        # Convert strings to datetime objects
        start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M")
        end_dt = datetime.strptime(end_str, "%Y-%m-%dT%H:%M")
        
        args = [int(user_id), int(charger_id), start_dt, end_dt, 0]
        result_args = cursor.callproc('BookChargingSlot', args)
        success_status = result_args[4]
        
        if success_status == 1:
            return jsonify({'success': True, 'message': 'Booking confirmed successfully!'})
        else:
            return jsonify({'success': False, 'error': 'Booking failed. Charger occupied or timing conflict.'}), 400
            
    except mysql.connector.Error as err:
        return jsonify({'error': f"Database execution error: {err}"}), 500
    except ValueError as val_err:
        return jsonify({'error': f"Invalid date/time format: {val_err}"}), 400
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting EV Optimizer Web Server on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
