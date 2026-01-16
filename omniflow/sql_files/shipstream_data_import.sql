-- =====================================================
-- ShipStream Database Setup and Data Import
-- =====================================================
-- This script creates tables and imports dummy shipment data

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS shipstream;
USE shipstream;

-- Drop existing tables if they exist (for clean import)
DROP TABLE IF EXISTS tracking_events;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS warehouses;

-- Create warehouses table
CREATE TABLE warehouses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location VARCHAR(100) NOT NULL,
    manager_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create shipments table
CREATE TABLE shipments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    tracking_number VARCHAR(50) NOT NULL UNIQUE,
    estimated_arrival DATE NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    shipment_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tracking_number (tracking_number),
    INDEX idx_status (status),
    INDEX idx_shipment_date (shipment_date)
);

-- Create tracking events table
CREATE TABLE tracking_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shipment_id INT NOT NULL,
    warehouse_id INT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    status_update VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE,
    INDEX idx_shipment_id (shipment_id),
    INDEX idx_timestamp (timestamp)
);

-- Create NDR (Non-Delivery Report) table
CREATE TABLE ndr_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shipment_id INT NOT NULL,
    ndr_number VARCHAR(50) NOT NULL UNIQUE,
    ndr_date DATE NOT NULL,
    issue VARCHAR(200) NOT NULL,
    attempts INT NOT NULL DEFAULT 1,
    final_outcome VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    INDEX idx_ndr_number (ndr_number),
    INDEX idx_shipment_id (shipment_id)
);

-- Create reverse shipments table
CREATE TABLE reverse_shipments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    original_shipment_id INT NOT NULL,
    reverse_number VARCHAR(50) NOT NULL UNIQUE,
    return_date DATE NOT NULL,
    reason VARCHAR(200) NOT NULL,
    refund_status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (original_shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    INDEX idx_reverse_number (reverse_number),
    INDEX idx_original_shipment_id (original_shipment_id)
);

-- Create exchange shipments table
CREATE TABLE exchange_shipments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    original_shipment_id INT NOT NULL,
    exchange_number VARCHAR(50) NOT NULL UNIQUE,
    exchange_date DATE NOT NULL,
    new_item VARCHAR(200) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (original_shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    INDEX idx_exchange_number (exchange_number),
    INDEX idx_original_shipment_id (original_shipment_id)
);

-- =====================================================
-- Insert sample warehouses
-- =====================================================
INSERT INTO warehouses (location, manager_name) VALUES
('Mumbai Hub', 'Rajesh Kumar'),
('Delhi Center', 'Amit Sharma'),
('Bangalore Warehouse', 'Priya Nair'),
('Chennai Facility', 'Suresh Reddy'),
('Kolkata Depot', 'Anjali Gupta');

-- =====================================================
-- Insert forward shipments data
-- =====================================================
INSERT INTO shipments (order_id, tracking_number, estimated_arrival, customer_name, shipment_date, status, amount, notes) VALUES
(1, 'FWD-1001', '2023-10-05', 'Aarav Patel', '2023-10-01', 'Delivered', 1200.00, NULL),
(2, 'FWD-1002', '2023-10-05', 'Vihaan Reddy', '2023-10-01', 'Delivered', 850.00, NULL),
(3, 'FWD-1003', '2023-10-06', 'Aditya Sharma', '2023-10-02', 'Delivered', 2100.00, NULL),
(4, 'FWD-1004', '2023-10-06', 'Sai Kumar', '2023-10-02', 'Delivered', 450.00, NULL),
(5, 'FWD-1005', '2023-10-07', 'Reyansh Singh', '2023-10-03', 'Delivered', 3200.00, NULL),
(6, 'FWD-1006', '2023-10-07', 'Arjun Gupta', '2023-10-03', 'Delivered', 1500.00, NULL),
(7, 'FWD-1007', '2023-10-08', 'Kiara Advani', '2023-10-04', 'Delivered', 900.00, NULL),
(8, 'FWD-1008', '2023-10-08', 'Ishaan Verma', '2023-10-04', 'Delivered', 2500.00, NULL),
(9, 'FWD-1009', '2023-10-09', 'Saanvi Mehta', '2023-10-05', 'Delivered', 600.00, NULL),
(10, 'FWD-1010', '2023-10-09', 'Ayaan Khan', '2023-10-05', 'Delivered', 1100.00, 'Had NDR, but Success'),
(11, 'FWD-1011', '2023-10-10', 'Zara Siddiqui', '2023-10-06', 'Delivered', 3400.00, 'Had NDR, but Success'),
(12, 'FWD-1012', '2023-10-10', 'Kabir Das', '2023-10-06', 'Delivered', 550.00, 'Had NDR, but Success'),
(13, 'FWD-1013', '2023-10-11', 'Ananya Roy', '2023-10-07', 'RTO_Initiated', 1800.00, 'NDR -> Return'),
(14, 'FWD-1014', '2023-10-11', 'Rohan Joshi', '2023-10-07', 'RTO_Initiated', 950.00, 'NDR -> Return'),
(15, 'FWD-1015', '2023-10-12', 'Meera Nair', '2023-10-08', 'RTO_Initiated', 2200.00, 'NDR -> Return'),
(16, 'FWD-1016', '2023-10-12', 'Dhruv Malhotra', '2023-10-08', 'RTO_Initiated', 300.00, 'NDR -> Return'),
(17, 'FWD-1017', '2023-10-13', 'Naira Kapoor', '2023-10-09', 'RTO_Initiated', 4100.00, 'NDR -> Return'),
(18, 'FWD-1018', '2023-10-13', 'Arnav Singh', '2023-10-09', 'Exchanged', 1250.00, NULL),
(19, 'FWD-1019', '2023-10-14', 'Pari Chopra', '2023-10-10', 'Exchanged', 2700.00, NULL),
(20, 'FWD-1020', '2023-10-14', 'Vivaan Jain', '2023-10-10', 'Exchanged', 890.00, NULL);

-- =====================================================
-- Insert NDR events
-- =====================================================
INSERT INTO ndr_events (shipment_id, ndr_number, ndr_date, issue, attempts, final_outcome) VALUES
(10, 'NDR-501', '2023-10-06', 'Customer Unreachable', 1, 'Delivered'),
(11, 'NDR-502', '2023-10-07', 'Door Locked', 2, 'Delivered'),
(12, 'NDR-503', '2023-10-07', 'Entry Restricted', 1, 'Delivered'),
(13, 'NDR-504', '2023-10-08', 'Customer Refused', 3, 'RTO'),
(14, 'NDR-505', '2023-10-09', 'Address Incomplete', 3, 'RTO'),
(15, 'NDR-506', '2023-10-10', 'Customer Not Available', 3, 'RTO'),
(16, 'NDR-507', '2023-10-11', 'Damaged in Transit', 1, 'RTO'),
(17, 'NDR-508', '2023-10-12', 'COD Amount Mismatch', 2, 'RTO');

-- =====================================================
-- Insert reverse shipments
-- =====================================================
INSERT INTO reverse_shipments (original_shipment_id, reverse_number, return_date, reason, refund_status) VALUES
(13, 'REV-9001', '2023-10-12', 'Customer Refused', 'Processed'),
(14, 'REV-9002', '2023-10-13', 'Address Incomplete', 'Pending'),
(15, 'REV-9003', '2023-10-14', 'Customer Not Available', 'Processed'),
(16, 'REV-9004', '2023-10-15', 'Damaged in Transit', 'Processed'),
(17, 'REV-9005', '2023-10-16', 'COD Amount Mismatch', 'Pending');

-- =====================================================
-- Insert exchange shipments
-- =====================================================
INSERT INTO exchange_shipments (original_shipment_id, exchange_number, exchange_date, new_item, status) VALUES
(18, 'EXC-201', '2023-10-12', 'Size M -> Size L', 'Dispatched'),
(19, 'EXC-202', '2023-10-14', 'Blue -> Black', 'In Transit'),
(20, 'EXC-203', '2023-10-15', 'Defective -> Replacement', 'Delivered');

-- =====================================================
-- Insert sample tracking events
-- =====================================================
INSERT INTO tracking_events (shipment_id, warehouse_id, timestamp, status_update, location) VALUES
-- Sample tracking for first few shipments
(1, 1, '2023-10-01 10:00:00', 'Order Confirmed', 'Mumbai Hub'),
(1, 1, '2023-10-02 14:30:00', 'Shipped', 'Mumbai Hub'),
(1, 2, '2023-10-04 09:15:00', 'In Transit', 'Delhi Center'),
(1, 2, '2023-10-05 16:45:00', 'Delivered', 'Delhi Center'),

(2, 1, '2023-10-01 11:30:00', 'Order Confirmed', 'Mumbai Hub'),
(2, 1, '2023-10-02 16:00:00', 'Shipped', 'Mumbai Hub'),
(2, 2, '2023-10-04 11:20:00', 'In Transit', 'Delhi Center'),
(2, 2, '2023-10-05 14:30:00', 'Delivered', 'Delhi Center'),

(13, 1, '2023-10-07 09:00:00', 'Order Confirmed', 'Mumbai Hub'),
(13, 1, '2023-10-08 12:00:00', 'Shipped', 'Mumbai Hub'),
(13, 3, '2023-10-08 18:00:00', 'NDR Attempt 1', 'Bangalore Warehouse'),
(13, 3, '2023-10-09 14:00:00', 'NDR Attempt 2', 'Bangalore Warehouse'),
(13, 3, '2023-10-10 16:00:00', 'NDR Attempt 3', 'Bangalore Warehouse'),
(13, 1, '2023-10-11 10:00:00', 'RTO Initiated', 'Mumbai Hub');

-- =====================================================
-- Create views for easy querying
-- =====================================================

-- View for shipment summary with NDR info
CREATE VIEW shipment_summary AS
SELECT 
    s.id,
    s.tracking_number,
    s.customer_name,
    s.shipment_date,
    s.estimated_arrival,
    s.status,
    s.amount,
    s.notes,
    COALESCE(nd.ndr_number, 'N/A') as ndr_number,
    COALESCE(nd.issue, 'N/A') as ndr_issue,
    COALESCE(nd.attempts, 0) as ndr_attempts,
    COALESCE(nd.final_outcome, 'N/A') as ndr_outcome
FROM shipments s
LEFT JOIN ndr_events nd ON s.id = nd.shipment_id;

-- View for reverse shipment summary
CREATE VIEW reverse_shipment_summary AS
SELECT 
    rs.id,
    rs.reverse_number,
    rs.return_date,
    rs.reason,
    rs.refund_status,
    s.tracking_number as original_tracking,
    s.customer_name,
    s.amount as original_amount
FROM reverse_shipments rs
JOIN shipments s ON rs.original_shipment_id = s.id;

-- View for exchange shipment summary
CREATE VIEW exchange_shipment_summary AS
SELECT 
    es.id,
    es.exchange_number,
    es.exchange_date,
    es.new_item,
    es.status,
    s.tracking_number as original_tracking,
    s.customer_name,
    s.amount as original_amount
FROM exchange_shipments es
JOIN shipments s ON es.original_shipment_id = s.id;

-- =====================================================
-- Display summary
-- =====================================================
SELECT 'ShipStream Database Setup Complete!' as status;
SELECT COUNT(*) as total_shipments FROM shipments;
SELECT COUNT(*) as total_ndr_events FROM ndr_events;
SELECT COUNT(*) as total_reverse_shipments FROM reverse_shipments;
SELECT COUNT(*) as total_exchange_shipments FROM exchange_shipments;
SELECT COUNT(*) as total_warehouses FROM warehouses;
