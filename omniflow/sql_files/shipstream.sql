-- =====================================================
-- ShipStream Database Setup
-- =====================================================
-- This script creates tables for the ShipStream module

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
    capacity INT DEFAULT 1000,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_location (location),
    INDEX idx_is_active (is_active)
);

-- Create shipments table
CREATE TABLE shipments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,                  -- reference to shopcore.Order.id
    tracking_number VARCHAR(50) NOT NULL UNIQUE,
    estimated_arrival DATE NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(20),
    customer_email VARCHAR(100),
    shipping_address TEXT,
    shipment_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Pending',
    amount DECIMAL(10, 2) NOT NULL,
    weight DECIMAL(8, 2),
    dimensions VARCHAR(50),                  -- LxWxH format
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_order_id (order_id),
    INDEX idx_tracking_number (tracking_number),
    INDEX idx_status (status),
    INDEX idx_shipment_date (shipment_date),
    INDEX idx_customer_name (customer_name)
);

-- Create tracking events table
CREATE TABLE tracking_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shipment_id INT NOT NULL,               -- reference to Shipments.id
    warehouse_id INT NOT NULL,              -- reference to Warehouses.id
    timestamp TIMESTAMP NOT NULL,
    status_update VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE,
    INDEX idx_shipment_id (shipment_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_status_update (status_update)
);

-- Create NDR (Non-Delivery Report) table
CREATE TABLE ndr_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shipment_id INT NOT NULL,               -- reference to Shipments.id
    ndr_number VARCHAR(50) NOT NULL UNIQUE,
    ndr_date DATE NOT NULL,
    issue VARCHAR(200) NOT NULL,
    attempts INT NOT NULL DEFAULT 1,
    final_outcome VARCHAR(50) NOT NULL,
    resolution_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    INDEX idx_ndr_number (ndr_number),
    INDEX idx_shipment_id (shipment_id),
    INDEX idx_ndr_date (ndr_date),
    INDEX idx_final_outcome (final_outcome)
);

-- Create reverse shipments table
CREATE TABLE reverse_shipments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    original_shipment_id INT NOT NULL,       -- reference to Shipments.id
    reverse_number VARCHAR(50) NOT NULL UNIQUE,
    return_date DATE NOT NULL,
    reason VARCHAR(200) NOT NULL,
    refund_status VARCHAR(50) NOT NULL,
    refund_amount DECIMAL(10, 2),
    refund_reference VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (original_shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    INDEX idx_reverse_number (reverse_number),
    INDEX idx_original_shipment_id (original_shipment_id),
    INDEX idx_return_date (return_date),
    INDEX idx_refund_status (refund_status)
);

-- Create exchange shipments table
CREATE TABLE exchange_shipments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    original_shipment_id INT NOT NULL,       -- reference to Shipments.id
    exchange_number VARCHAR(50) NOT NULL UNIQUE,
    exchange_date DATE NOT NULL,
    new_item VARCHAR(200) NOT NULL,
    status VARCHAR(50) NOT NULL,
    exchange_reason VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (original_shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    INDEX idx_exchange_number (exchange_number),
    INDEX idx_original_shipment_id (original_shipment_id),
    INDEX idx_exchange_date (exchange_date),
    INDEX idx_status (status)
);

-- =====================================================
-- Insert sample data
-- =====================================================

-- Insert sample warehouses
INSERT INTO warehouses (location, manager_name, capacity) VALUES
('Mumbai Hub', 'Rajesh Kumar', 2000),
('Delhi Center', 'Amit Sharma', 1500),
('Bangalore Warehouse', 'Priya Nair', 1800),
('Chennai Facility', 'Suresh Reddy', 1200),
('Kolkata Depot', 'Anjali Gupta', 1000),
('Hyderabad Center', 'Vikram Singh', 1600),
('Pune Warehouse', 'Meera Deshmukh', 1400),
('Jaipur Facility', 'Rohit Sharma', 900),
('Ahmedabad Hub', 'Anita Patel', 1100),
('Lucknow Center', 'Rahul Verma', 800);

-- Insert forward shipments data
INSERT INTO shipments (order_id, tracking_number, estimated_arrival, customer_name, customer_phone, customer_email, shipping_address, shipment_date, status, amount, notes) VALUES
(1, 'FWD-1001', '2023-10-05', 'Aarav Patel', '9876543210', 'aarav.patel@email.com', '123 Main St, Mumbai, Maharashtra 400001', '2023-10-01', 'Delivered', 1200.00, NULL),
(2, 'FWD-1002', '2023-10-05', 'Vihaan Reddy', '9876543211', 'vihaan.reddy@email.com', '456 Park Ave, Delhi, Delhi 110001', '2023-10-01', 'Delivered', 850.00, NULL),
(3, 'FWD-1003', '2023-10-06', 'Aditya Sharma', '9876543212', 'aditya.sharma@email.com', '789 Market Rd, Bangalore, Karnataka 560001', '2023-10-02', 'Delivered', 2100.00, NULL),
(4, 'FWD-1004', '2023-10-06', 'Sai Kumar', '9876543213', 'sai.kumar@email.com', '321 College St, Chennai, Tamil Nadu 600001', '2023-10-02', 'Delivered', 450.00, NULL),
(5, 'FWD-1005', '2023-10-07', 'Reyansh Singh', '9876543214', 'reyansh.singh@email.com', '654 Station Rd, Hyderabad, Telangana 500001', '2023-10-03', 'Delivered', 3200.00, NULL),
(6, 'FWD-1006', '2023-10-07', 'Arjun Gupta', '9876543215', 'arjun.gupta@email.com', '987 Temple St, Kolkata, West Bengal 700001', '2023-10-03', 'Delivered', 1500.00, NULL),
(7, 'FWD-1007', '2023-10-08', 'Kiara Advani', '9876543216', 'kiara.advani@email.com', '147 Beach Rd, Pune, Maharashtra 411001', '2023-10-04', 'Delivered', 900.00, NULL),
(8, 'FWD-1008', '2023-10-08', 'Ishaan Verma', '9876543217', 'ishaan.verma@email.com', '258 Mountain View, Jaipur, Rajasthan 302001', '2023-10-04', 'Delivered', 2500.00, NULL),
(9, 'FWD-1009', '2023-10-09', 'Saanvi Mehta', '9876543218', 'saanvi.mehta@email.com', '369 River Side, Lucknow, Uttar Pradesh 226001', '2023-10-05', 'Delivered', 600.00, NULL),
(10, 'FWD-1010', '2023-10-09', 'Ayaan Khan', '9876543219', 'ayaan.khan@email.com', '741 Garden Ave, Ahmedabad, Gujarat 380001', '2023-10-05', 'Delivered', 1100.00, 'Had NDR, but Success'),
(11, 'FWD-1011', '2023-10-10', 'Zara Siddiqui', '9876543220', 'zara.siddiqui@email.com', '852 Business Park, Gurgaon, Haryana 122001', '2023-10-06', 'Delivered', 3400.00, 'Had NDR, but Success'),
(12, 'FWD-1012', '2023-10-10', 'Kabir Das', '9876543221', 'kabir.das@email.com', '963 Tech Hub, Noida, Uttar Pradesh 201301', '2023-10-06', 'Delivered', 550.00, 'Had NDR, but Success'),
(13, 'FWD-1013', '2023-10-11', 'Ananya Roy', '9876543222', 'ananya.roy@email.com', '159 Shopping Mall, Chandigarh 160001', '2023-10-07', 'RTO_Initiated', 1800.00, 'NDR -> Return'),
(14, 'FWD-1014', '2023-10-11', 'Rohan Joshi', '9876543223', 'rohan.joshi@email.com', '753 Industrial Area, Coimbatore, Tamil Nadu 641001', '2023-10-07', 'RTO_Initiated', 950.00, 'NDR -> Return'),
(15, 'FWD-1015', '2023-10-12', 'Meera Nair', '9876543224', 'meera.nair@email.com', '456 Residential Complex, Kochi, Kerala 682001', '2023-10-08', 'RTO_Initiated', 2200.00, 'NDR -> Return'),
(16, 'FWD-1016', '2023-10-12', 'Dhruv Malhotra', '9876543225', 'dhruv.malhotra@email.com', '821 IT Park, Indore, Madhya Pradesh 452001', '2023-10-08', 'RTO_Initiated', 300.00, 'NDR -> Return'),
(17, 'FWD-1017', '2023-10-13', 'Naira Kapoor', '9876543226', 'naira.kapoor@email.com', '369 Corporate Tower, Nagpur, Maharashtra 440001', '2023-10-09', 'RTO_Initiated', 4100.00, 'NDR -> Return'),
(18, 'FWD-1018', '2023-10-13', 'Arnav Singh', '9876543227', 'arnav.singh@email.com', '147 Service Center, Visakhapatnam, Andhra Pradesh 530001', '2023-10-09', 'Exchanged', 1250.00, NULL),
(19, 'FWD-1019', '2023-10-14', 'Pari Chopra', '9876543228', 'pari.chopra@email.com', '258 Repair Shop, Bhopal, Madhya Pradesh 462001', '2023-10-10', 'Exchanged', 2700.00, NULL),
(20, 'FWD-1020', '2023-10-14', 'Vivaan Jain', '9876543229', 'vivaan.jain@email.com', '741 Outlet, Guwahati, Assam 781001', '2023-10-10', 'Exchanged', 890.00, NULL);

-- Insert NDR events
INSERT INTO ndr_events (shipment_id, ndr_number, ndr_date, issue, attempts, final_outcome, resolution_details) VALUES
(10, 'NDR-501', '2023-10-06', 'Customer Unreachable', 1, 'Delivered', 'Customer contacted on second attempt and delivery completed'),
(11, 'NDR-502', '2023-10-07', 'Door Locked', 2, 'Delivered', 'Customer provided alternative delivery time'),
(12, 'NDR-503', '2023-10-07', 'Entry Restricted', 1, 'Delivered', 'Security clearance obtained and delivery completed'),
(13, 'NDR-504', '2023-10-08', 'Customer Refused', 3, 'RTO', 'Customer refused delivery due to wrong product'),
(14, 'NDR-505', '2023-10-09', 'Address Incomplete', 3, 'RTO', 'Address could not be verified after multiple attempts'),
(15, 'NDR-506', '2023-10-10', 'Customer Not Available', 3, 'RTO', 'Customer unavailable despite multiple delivery attempts'),
(16, 'NDR-507', '2023-10-11', 'Damaged in Transit', 1, 'RTO', 'Package damaged during handling, return initiated'),
(17, 'NDR-508', '2023-10-12', 'COD Amount Mismatch', 2, 'RTO', 'Customer disputed COD amount, return processed');

-- Insert reverse shipments
INSERT INTO reverse_shipments (original_shipment_id, reverse_number, return_date, reason, refund_status, refund_amount, refund_reference) VALUES
(13, 'REV-9001', '2023-10-12', 'Customer Refused', 'Processed', 1800.00, 'REF-001'),
(14, 'REV-9002', '2023-10-13', 'Address Incomplete', 'Pending', 950.00, 'REF-002'),
(15, 'REV-9003', '2023-10-14', 'Customer Not Available', 'Processed', 2200.00, 'REF-003'),
(16, 'REV-9004', '2023-10-15', 'Damaged in Transit', 'Processed', 300.00, 'REF-004'),
(17, 'REV-9005', '2023-10-16', 'COD Amount Mismatch', 'Pending', 4100.00, 'REF-005');

-- Insert exchange shipments
INSERT INTO exchange_shipments (original_shipment_id, exchange_number, exchange_date, new_item, status, exchange_reason) VALUES
(18, 'EXC-201', '2023-10-12', 'Size M -> Size L', 'Dispatched', 'Size mismatch - customer requested larger size'),
(19, 'EXC-202', '2023-10-14', 'Blue -> Black', 'In Transit', 'Color preference change'),
(20, 'EXC-203', '2023-10-15', 'Defective -> Replacement', 'Delivered', 'Product defective, replacement sent');

-- Insert sample tracking events
INSERT INTO tracking_events (shipment_id, warehouse_id, timestamp, status_update, location, remarks) VALUES
-- Tracking for first few shipments
(1, 1, '2023-10-01 10:00:00', 'Order Confirmed', 'Mumbai Hub', 'Order received and processed'),
(1, 1, '2023-10-02 14:30:00', 'Shipped', 'Mumbai Hub', 'Package handed over to courier'),
(1, 2, '2023-10-04 09:15:00', 'In Transit', 'Delhi Center', 'Package arrived at destination facility'),
(1, 2, '2023-10-05 16:45:00', 'Delivered', 'Delhi Center', 'Successfully delivered to customer'),

(2, 1, '2023-10-01 11:30:00', 'Order Confirmed', 'Mumbai Hub', 'Order received and processed'),
(2, 1, '2023-10-02 16:00:00', 'Shipped', 'Mumbai Hub', 'Package handed over to courier'),
(2, 2, '2023-10-04 11:20:00', 'In Transit', 'Delhi Center', 'Package arrived at destination facility'),
(2, 2, '2023-10-05 14:30:00', 'Delivered', 'Delhi Center', 'Successfully delivered to customer'),

(13, 1, '2023-10-07 09:00:00', 'Order Confirmed', 'Mumbai Hub', 'Order received and processed'),
(13, 1, '2023-10-08 12:00:00', 'Shipped', 'Mumbai Hub', 'Package handed over to courier'),
(13, 3, '2023-10-08 18:00:00', 'NDR Attempt 1', 'Bangalore Warehouse', 'Customer unreachable'),
(13, 3, '2023-10-09 14:00:00', 'NDR Attempt 2', 'Bangalore Warehouse', 'Customer refused delivery'),
(13, 3, '2023-10-10 16:00:00', 'NDR Attempt 3', 'Bangalore Warehouse', 'Customer unavailable, initiating return'),
(13, 1, '2023-10-11 10:00:00', 'RTO Initiated', 'Mumbai Hub', 'Return to origin initiated');

-- =====================================================
-- Create views for easy querying
-- =====================================================

-- View for shipment summary with NDR info
CREATE VIEW shipment_summary AS
SELECT 
    s.id,
    s.tracking_number,
    s.customer_name,
    s.customer_phone,
    s.customer_email,
    s.shipment_date,
    s.estimated_arrival,
    s.status,
    s.amount,
    s.notes,
    COALESCE(nd.ndr_number, 'N/A') as ndr_number,
    COALESCE(nd.issue, 'N/A') as ndr_issue,
    COALESCE(nd.attempts, 0) as ndr_attempts,
    COALESCE(nd.final_outcome, 'N/A') as ndr_outcome,
    CASE 
        WHEN s.status = 'Delivered' THEN DATEDIFF(s.estimated_arrival, s.shipment_date)
        ELSE NULL
    END as delivery_days
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
    rs.refund_amount,
    rs.refund_reference,
    s.tracking_number as original_tracking,
    s.customer_name,
    s.amount as original_amount,
    DATEDIFF(rs.return_date, s.shipment_date) as days_to_return
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
    es.exchange_reason,
    s.tracking_number as original_tracking,
    s.customer_name,
    s.amount as original_amount,
    DATEDIFF(es.exchange_date, s.shipment_date) as days_to_exchange
FROM exchange_shipments es
JOIN shipments s ON es.original_shipment_id = s.id;

-- View for warehouse performance
CREATE VIEW warehouse_performance AS
SELECT 
    w.id as warehouse_id,
    w.location,
    w.manager_name,
    w.capacity,
    COUNT(te.id) as total_events,
    COUNT(DISTINCT te.shipment_id) as unique_shipments,
    MAX(te.timestamp) as last_activity
FROM warehouses w
LEFT JOIN tracking_events te ON w.id = te.warehouse_id
GROUP BY w.id, w.location, w.manager_name, w.capacity;

-- View for NDR analytics
CREATE VIEW ndr_analytics AS
SELECT 
    nd.issue,
    COUNT(*) as total_ndr,
    COUNT(CASE WHEN nd.final_outcome = 'Delivered' THEN 1 END) as resolved_delivered,
    COUNT(CASE WHEN nd.final_outcome = 'RTO' THEN 1 END) as resolved_rto,
    AVG(nd.attempts) as avg_attempts,
    AVG(DATEDIFF(nd.ndr_date, s.shipment_date)) as avg_days_to_ndr
FROM ndr_events nd
JOIN shipments s ON nd.shipment_id = s.id
GROUP BY nd.issue
ORDER BY total_ndr DESC;

-- =====================================================
-- Display summary
-- =====================================================
SELECT 'ShipStream Database Setup Complete!' as status;
SELECT COUNT(*) as total_shipments FROM shipments;
SELECT COUNT(*) as total_ndr_events FROM ndr_events;
SELECT COUNT(*) as total_reverse_shipments FROM reverse_shipments;
SELECT COUNT(*) as total_exchange_shipments FROM exchange_shipments;
SELECT COUNT(*) as total_warehouses FROM warehouses;
SELECT COUNT(*) as total_tracking_events FROM tracking_events;