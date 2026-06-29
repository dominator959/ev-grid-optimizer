-- =================================================================
-- 1. DATABASE INITIATION & TABLES CREATION
-- =================================================================
CREATE DATABASE IF NOT EXISTS EV_Grid_Optimizer;
USE EV_Grid_Optimizer;

-- A. Table: Charging Stations
CREATE TABLE IF NOT EXISTS charging_stations (
 station_id INT AUTO_INCREMENT PRIMARY KEY,
 city VARCHAR(50) NOT NULL,
 location_area VARCHAR(100) NOT NULL,
 max_grid_capacity_kw INT NOT NULL,
 current_load_kw INT DEFAULT 0
) ENGINE=InnoDB;

-- B. Table: Chargers
CREATE TABLE IF NOT EXISTS chargers (
 charger_id INT AUTO_INCREMENT PRIMARY KEY,
 station_id INT NOT NULL,
 connector_type ENUM('GB/T', 'CCS_Type2', 'AC_Type2') NOT NULL,
 power_output_kw INT NOT NULL,
 status ENUM('Available', 'Occupied', 'Load_Shedding', 'Maintenance') DEFAULT 'Available',
 FOREIGN KEY (station_id) REFERENCES charging_stations(station_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- C. Table: Users and EVs
CREATE TABLE IF NOT EXISTS users_and_evs (
 user_id INT AUTO_INCREMENT PRIMARY KEY,
 owner_name VARCHAR(100) NOT NULL,
 car_model VARCHAR(50) NOT NULL,
 battery_capacity_kwh INT NOT NULL,
 wallet_balance_pkr DECIMAL(10, 2) NOT NULL DEFAULT 0.00
) ENGINE=InnoDB;

-- D. Table: Charging Slots (With Performance Indexes)
CREATE TABLE IF NOT EXISTS charging_slots (
 slot_id INT AUTO_INCREMENT PRIMARY KEY,
 charger_id INT NOT NULL,
 user_id INT NOT NULL,
 start_time DATETIME NOT NULL,
 end_time DATETIME NOT NULL,
 status ENUM('Booked', 'Active', 'Completed', 'Cancelled') DEFAULT 'Booked',
 FOREIGN KEY (charger_id) REFERENCES chargers(charger_id),
 FOREIGN KEY (user_id) REFERENCES users_and_evs(user_id)
) ENGINE=InnoDB;

-- Create indexes for rapid scheduling lookups via Python
CREATE INDEX idx_booking_time ON charging_slots(start_time, end_time);

-- E. Table: Billing Ledger
CREATE TABLE IF NOT EXISTS billing_ledger (
 bill_id INT AUTO_INCREMENT PRIMARY KEY,
 slot_id INT NOT NULL,
 units_consumed_kwh DECIMAL(6,2) NOT NULL,
 tariff_rate_pkr DECIMAL(6,2) NOT NULL,
 total_amount_pkr DECIMAL(10,2) NOT NULL,
 payment_status ENUM('Unpaid', 'Paid') DEFAULT 'Unpaid',
 FOREIGN KEY (slot_id) REFERENCES charging_slots(slot_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =================================================================
-- 2. ADVANCED DBMS FEATURES (VIEWS, TRIGGERS, PROCEDURES)
-- =================================================================

-- VIEW: Pakistan Dynamic Peak/Off-Peak Tariff Calculator
CREATE OR REPLACE VIEW LiveTariffGrid AS
SELECT 
 station_id,
 city,
 location_area,
 CASE 
 WHEN HOUR(NOW()) BETWEEN 17 AND 23 THEN 75.00 
 ELSE 50.00 
 END AS current_cost_per_kwh
FROM charging_stations;

-- TRIGGER: Automatic Grid Load Mitigation Engine
DROP TRIGGER IF EXISTS TrackGridLoadStatus;
DELIMITER $$
CREATE TRIGGER TrackGridLoadStatus
AFTER UPDATE ON chargers
FOR EACH ROW
BEGIN
 DECLARE total_load INT;
 DECLARE max_cap INT;
 SELECT SUM(power_output_kw) INTO total_load FROM chargers 
 WHERE station_id = NEW.station_id AND status = 'Occupied';
 SELECT max_grid_capacity_kw INTO max_cap FROM charging_stations 
 WHERE station_id = NEW.station_id;
 UPDATE charging_stations SET current_load_kw = IFNULL(total_load, 0) 
 WHERE station_id = NEW.station_id;
END$$
DELIMITER ;

-- STORED PROCEDURE WITH ACID TRANSACTION: Safe Concurrent Slot Booking Engine
DROP PROCEDURE IF EXISTS BookChargingSlot;
DELIMITER $$
CREATE PROCEDURE BookChargingSlot(
 IN p_user_id INT, 
 IN p_charger_id INT, 
 IN p_start DATETIME, 
 IN p_end DATETIME,
 OUT p_success_flag INT
)
BEGIN
 DECLARE v_status VARCHAR(20);
 DECLARE EXIT HANDLER FOR SQLEXCEPTION
 BEGIN
 ROLLBACK;
 SET p_success_flag = 0;
 END;
 
 START TRANSACTION;
 SELECT status INTO v_status FROM chargers WHERE charger_id = p_charger_id FOR UPDATE;
 IF v_status = 'Available' AND NOT EXISTS (
 SELECT 1 FROM charging_slots 
 WHERE charger_id = p_charger_id 
 AND status = 'Booked'
 AND (p_start < end_time AND p_end > start_time)
 ) THEN
 INSERT INTO charging_slots(charger_id, user_id, start_time, end_time, status)
 VALUES(p_charger_id, p_user_id, p_start, p_end, 'Booked');
 COMMIT;
 SET p_success_flag = 1;
 ELSE
 ROLLBACK;
 SET p_success_flag = 0;
 END IF;
END$$
DELIMITER ;

-- =================================================================
-- 3. SEED DATA (For Testing Purposes)
-- =================================================================
INSERT INTO charging_stations (city, location_area, max_grid_capacity_kw, current_load_kw) VALUES
('Lahore', 'DHA Phase 6', 150, 0),
('Karachi', 'Clifton Block 5', 200, 0),
('Islamabad', 'F-7 Markaz', 120, 0);

INSERT INTO chargers (station_id, connector_type, power_output_kw, status) VALUES
(1, 'GB/T', 60, 'Available'),
(1, 'CCS_Type2', 80, 'Available'),
(2, 'GB/T', 120, 'Available'),
(2, 'AC_Type2', 22, 'Available'),
(3, 'GB/T', 60, 'Available');

INSERT INTO users_and_evs (owner_name, car_model, battery_capacity_kwh, wallet_balance_pkr) VALUES
('Muhammad Usman', 'MG ZS EV', 44, 15000.00),
('Ali Khan', 'Audi e-tron', 95, 25000.00),
('Zara Ahmed', 'Hyundai Kona', 39, 8000.00);
