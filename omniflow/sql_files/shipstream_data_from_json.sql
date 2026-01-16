-- =====================================================
-- ShipStream Data Import from JSON
-- Generated on: 2026-01-16 13:43:26
-- =====================================================

-- Insert forward shipments
INSERT INTO shipments (order_id, tracking_number, estimated_arrival, customer_name, shipment_date, status, amount, notes) VALUES
(1, 'FWD-1001', '2023-10-01', 'Aarav Patel', '2023-10-01', 'Delivered', 1200, NULL),
(2, 'FWD-1002', '2023-10-01', 'Vihaan Reddy', '2023-10-01', 'Delivered', 850, NULL),
(3, 'FWD-1003', '2023-10-02', 'Aditya Sharma', '2023-10-02', 'Delivered', 2100, NULL),
(4, 'FWD-1004', '2023-10-02', 'Sai Kumar', '2023-10-02', 'Delivered', 450, NULL),
(5, 'FWD-1005', '2023-10-03', 'Reyansh Singh', '2023-10-03', 'Delivered', 3200, NULL),
(6, 'FWD-1006', '2023-10-03', 'Arjun Gupta', '2023-10-03', 'Delivered', 1500, NULL),
(7, 'FWD-1007', '2023-10-04', 'Kiara Advani', '2023-10-04', 'Delivered', 900, NULL),
(8, 'FWD-1008', '2023-10-04', 'Ishaan Verma', '2023-10-04', 'Delivered', 2500, NULL),
(9, 'FWD-1009', '2023-10-05', 'Saanvi Mehta', '2023-10-05', 'Delivered', 600, NULL),
(10, 'FWD-1010', '2023-10-05', 'Ayaan Khan', '2023-10-05', 'Delivered', 1100, 'Had NDR, but Success'),
(11, 'FWD-1011', '2023-10-06', 'Zara Siddiqui', '2023-10-06', 'Delivered', 3400, 'Had NDR, but Success'),
(12, 'FWD-1012', '2023-10-06', 'Kabir Das', '2023-10-06', 'Delivered', 550, 'Had NDR, but Success'),
(13, 'FWD-1013', '2023-10-07', 'Ananya Roy', '2023-10-07', 'RTO_Initiated', 1800, 'NDR -> Return'),
(14, 'FWD-1014', '2023-10-07', 'Rohan Joshi', '2023-10-07', 'RTO_Initiated', 950, 'NDR -> Return'),
(15, 'FWD-1015', '2023-10-08', 'Meera Nair', '2023-10-08', 'RTO_Initiated', 2200, 'NDR -> Return'),
(16, 'FWD-1016', '2023-10-08', 'Dhruv Malhotra', '2023-10-08', 'RTO_Initiated', 300, 'NDR -> Return'),
(17, 'FWD-1017', '2023-10-09', 'Naira Kapoor', '2023-10-09', 'RTO_Initiated', 4100, 'NDR -> Return'),
(18, 'FWD-1018', '2023-10-09', 'Arnav Singh', '2023-10-09', 'Exchanged', 1250, NULL),
(19, 'FWD-1019', '2023-10-10', 'Pari Chopra', '2023-10-10', 'Exchanged', 2700, NULL),
(20, 'FWD-1020', '2023-10-10', 'Vivaan Jain', '2023-10-10', 'Exchanged', 890, NULL);

-- Insert NDR events
INSERT INTO ndr_events (shipment_id, ndr_number, ndr_date, issue, attempts, final_outcome) VALUES
(11, 'NDR-501', '2023-10-06', 'Customer Unreachable', 1, 'Delivered'),
(17, 'NDR-502', '2023-10-07', 'Door Locked', 2, 'Delivered'),
(16, 'NDR-503', '2023-10-07', 'Entry Restricted', 1, 'Delivered'),
(1, 'NDR-504', '2023-10-08', 'Customer Refused', 3, 'RTO'),
(7, 'NDR-505', '2023-10-09', 'Address Incomplete', 3, 'RTO'),
(17, 'NDR-506', '2023-10-10', 'Customer Not Available', 3, 'RTO'),
(8, 'NDR-507', '2023-10-11', 'Damaged in Transit', 1, 'RTO'),
(6, 'NDR-508', '2023-10-12', 'COD Amount Mismatch', 2, 'RTO');

-- Insert reverse shipments
INSERT INTO reverse_shipments (original_shipment_id, reverse_number, return_date, reason, refund_status) VALUES
(1, 'REV-9001', '2023-10-12', 'Customer Refused', 'Processed'),
(7, 'REV-9002', '2023-10-13', 'Address Incomplete', 'Pending'),
(17, 'REV-9003', '2023-10-14', 'Customer Not Available', 'Processed'),
(8, 'REV-9004', '2023-10-15', 'Damaged in Transit', 'Processed'),
(6, 'REV-9005', '2023-10-16', 'COD Amount Mismatch', 'Pending');

-- Insert exchange shipments
INSERT INTO exchange_shipments (original_shipment_id, exchange_number, exchange_date, new_item, status) VALUES
(9, 'EXC-201', '2023-10-12', 'Size M -> Size L', 'Dispatched'),
(1, 'EXC-202', '2023-10-14', 'Blue -> Black', 'In Transit'),
(19, 'EXC-203', '2023-10-15', 'Defective -> Replacement', 'Delivered');

-- =====================================================
-- Summary Queries
-- =====================================================

-- Total shipments by status
SELECT status, COUNT(*) as count FROM shipments GROUP BY status;

-- NDR events by outcome
SELECT final_outcome, COUNT(*) as count FROM ndr_events GROUP BY final_outcome;

-- Reverse shipments by refund status
SELECT refund_status, COUNT(*) as count FROM reverse_shipments GROUP BY refund_status;

-- Exchange shipments by status
SELECT status, COUNT(*) as count FROM exchange_shipments GROUP BY status;