-- =====================================================
-- Supervisor Testing Data Setup
-- =====================================================
-- This script creates test data for the supervisor graph to work with

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS omniflow_test;
USE omniflow_test;

-- =====================================================
-- Sample Data for Supervisor Testing
-- =====================================================

-- Create test users with different scenarios
INSERT INTO shopcore.users (name, email, premium_status) VALUES
('Alice Johnson', 'alice@test.com', TRUE),
('Bob Smith', 'bob@test.com', FALSE),
('Charlie Brown', 'charlie@test.com', TRUE),
('Diana Prince', 'diana@test.com', FALSE),
('Eve Wilson', 'eve@test.com', TRUE);

-- Create test products
INSERT INTO shopcore.products (name, category, price, description, stock_quantity) VALUES
('Wireless Mouse', 'Electronics', 999.99, 'Ergonomic wireless mouse with precision tracking', 50),
('Mechanical Keyboard', 'Electronics', 1499.99, 'RGB mechanical keyboard with blue switches', 30),
('USB-C Hub', 'Accessories', 299.99, '7-port USB-C hub with 4K HDMI output', 100),
('Laptop Stand', 'Accessories', 199.99, 'Adjustable aluminum laptop stand', 75),
('Monitor Arm', 'Accessories', 399.99, 'Full-motion monitor arm with cable management', 25);

-- Create test orders with different statuses
INSERT INTO shopcore.orders (user_id, product_id, order_date, status, quantity, total_amount, shipping_address) VALUES
(1, 1, '2023-10-01', 'Delivered', 1, 999.99, '123 Tech Street, Mumbai 400001'),
(2, 2, '2023-10-02', 'Shipped', 1, 1499.99, '456 Innovation Drive, Bangalore 560001'),
(3, 3, '2023-10-03', 'Processing', 2, 599.98, '789 Electronics Blvd, Chennai 600001'),
(4, 4, '2023-10-04', 'Pending', 1, 299.99, '321 Gadget Road, Delhi 110001'),
(5, 5, '2023-10-05', 'Delivered', 1, 399.99, '654 Computer Lane, Hyderabad 500001'),
(2, 1, '2023-10-06', 'Delivered', 1, 999.99, '987 Device Avenue, Pune 411001');

-- Create test shipments
INSERT INTO shipstream.shipments (order_id, tracking_number, estimated_arrival, customer_name, customer_phone, customer_email, shipping_address, shipment_date, status, amount, notes) VALUES
(1, 'SHIP-001', '2023-10-03', 'Alice Johnson', '9876543210', 'alice@test.com', '123 Tech Street, Mumbai 400001', '2023-10-01', 'Delivered', 999.99, 'Delivered successfully'),
(2, 'SHIP-002', '2023-10-04', 'Bob Smith', '9876543211', 'bob@test.com', '456 Innovation Drive, Bangalore 560001', '2023-10-02', 'In Transit', 1499.99, 'Shipped from warehouse'),
(3, 'SHIP-003', '2023-10-05', 'Charlie Brown', '9876543212', 'charlie@test.com', '789 Electronics Blvd, Chennai 600001', '2023-10-03', 'Pending', 599.98, 'Awaiting pickup'),
(4, 'SHIP-004', '2023-10-06', 'Diana Prince', '9876543213', 'diana@test.com', '321 Gadget Road, Delhi 110001', '2023-10-04', 'Delivered', 299.99, 'Delivered to office'),
(5, 'SHIP-005', '2023-10-07', 'Eve Wilson', '9876543214', 'eve@test.com', '654 Computer Lane, Hyderabad 500001', '2023-10-05', 'RTO_Initiated', 399.99, 'Customer refused delivery');

-- Create test support tickets
INSERT INTO caredesk.tickets (user_id, reference_id, issue_type, status, priority, assigned_agent_id, resolution_details, resolved_at) VALUES
(1, 'SHIP-001', 'Delivery Issue', 'Resolved', 'Low', 1, 'Package was delivered on time', '2023-10-03 10:30:00'),
(2, 'SHIP-002', 'Tracking Query', 'In Progress', 'Medium', 2, 'Customer requesting delivery updates', NULL),
(3, 'SHIP-003', 'Payment Issue', 'Open', 'High', 3, 'Customer charged incorrectly', NULL),
(4, 'SHIP-004', 'Product Quality', 'Resolved', 'Medium', 1, 'Product replaced after complaint', '2023-10-06 14:00:00'),
(5, 'SHIP-005', 'Return Request', 'Open', 'High', 2, 'Customer wants to return item', NULL);

-- Create test ticket messages
INSERT INTO caredesk.ticket_messages (ticket_id, sender, content, timestamp, is_internal) VALUES
(1, 'User', 'My package hasn\'t arrived yet. Can you check the tracking?', '2023-10-01 09:00:00', FALSE),
(1, 'Agent', 'I apologize for the delay. Let me check your tracking number.', '2023-10-01 09:05:00', FALSE),
(1, 'Agent', 'Your package is out for delivery and should arrive today by 6 PM.', '2023-10-01 09:10:00', FALSE),
(1, 'User', 'Thank you for the update!', '2023-10-01 09:15:00', FALSE),
(1, 'Agent', 'You\'re welcome! Your package has been delivered.', '2023-10-03 10:30:00', FALSE),
(2, 'User', 'Can you tell me where my order is?', '2023-10-02 14:00:00', FALSE),
(2, 'Agent', 'Your order is currently in transit and expected to arrive tomorrow.', '2023-10-02 14:30:00', FALSE);

-- Create test satisfaction surveys
INSERT INTO caredesk.satisfaction_surveys (ticket_id, rating, comments, survey_date, resolved_by_agent_id) VALUES
(1, 5, 'Quick and helpful response!', '2023-10-04 09:00:00', 1),
(4, 4, 'Issue was resolved but took some time.', '2023-10-07 10:00:00', 1);

-- Create test wallets
INSERT INTO payguard.wallets (user_id, balance, currency, wallet_type) VALUES
(1, 5000.00, 'INR', 'Standard'),
(2, 15000.00, 'INR', 'Premium'),
(3, 2500.00, 'INR', 'Standard'),
(4, 10000.00, 'INR', 'Premium'),
(5, 7500.00, 'INR', 'Business');

-- Create test payment methods
INSERT INTO payguard.payment_methods (wallet_id, provider, method_type, last_four_digits, expiry_date, is_default) VALUES
(1, 'Visa', 'Credit Card', '1234', '2025-12-31', TRUE),
(1, 'Paytm', 'UPI', NULL, NULL, FALSE),
(2, 'Mastercard', 'Credit Card', '5678', '2025-08-31', TRUE),
(2, 'Google Pay', 'UPI', NULL, NULL, FALSE),
(3, 'RuPay', 'Debit Card', '9012', '2024-11-30', TRUE),
(4, 'PhonePe', 'UPI', NULL, NULL, FALSE),
(5, 'American Express', 'Credit Card', '3456', '2025-06-30', TRUE);

-- Create test transactions
INSERT INTO payguard.transactions (wallet_id, order_id, transaction_id, amount, type, status, payment_method_id, description, metadata) VALUES
(1, 1, 'TXN-001', 999.99, 'Debit', 'Completed', 1, 'Payment for order SHIP-001', '{"gateway": "Visa", "auth_code": "123456"}'),
(2, 2, 'TXN-002', 1499.99, 'Debit', 'Completed', 2, 'Payment for order SHIP-002', '{"gateway": "Mastercard", "auth_code": "234567"}'),
(3, 3, 'TXN-003', 599.98, 'Debit', 'Pending', 3, 'Payment for order SHIP-003', '{"gateway": "RuPay", "auth_code": "345678"}'),
(4, 4, 'TXN-004', 299.99, 'Debit', 'Completed', 4, 'Payment for order SHIP-004', '{"gateway": "PhonePe", "auth_code": "456789"}'),
(5, 5, 'TXN-005', 399.99, 'Credit', 'Completed', 5, 'Refund for order SHIP-005', '{"reason": "RTO", "original_txn": "TXN-005"}'),
(1, NULL, 'TXN-006', 100.00, 'Credit', 'Completed', NULL, 'Welcome bonus for new wallet', '{"bonus_type": "welcome", "campaign": "new_user"}');

-- =====================================================
-- Test Queries for Supervisor
-- =====================================================

-- Query 1: Order Status Inquiry
-- Expected: Should route to ShopCore agent
SELECT 'Where is my order SHIP-002?' as user_query;

-- Query 2: Shipment Tracking
-- Expected: Should route to ShipStream agent
SELECT 'Can you track my shipment with tracking number SHIP-003?' as user_query;

-- Query 3: Payment Issue
-- Expected: Should route to PayGuard agent
SELECT 'I was charged twice for my order. Can you help?' as user_query;

-- Query 4: General Support
-- Expected: Should route to CareDesk agent
SELECT 'I need to return an item. What is the process?' as user_query;

-- Query 5: Multi-modal Query
-- Expected: Should involve multiple agents
SELECT 'I ordered a wireless mouse but received a keyboard. Also, the package is damaged.' as user_query;

-- Query 6: Complex Logistics Query
-- Expected: Should involve ShipStream and ShopCore
SELECT 'My order SHIP-004 was delivered but I need to change the delivery address. Also, what\'s the return policy for electronic items?' as user_query;

-- Query 7: Account and Payment
-- Expected: Should involve ShopCore and PayGuard
SELECT 'I want to update my email and check my wallet balance. Also, I want to add a new payment method.' as user_query;

-- Query 8: Refund Status
-- Expected: Should route to PayGuard
SELECT 'What is the status of my refund for order SHIP-005?' as user_query;

-- Query 9: Product Information
-- Expected: Should route to ShopCore
SELECT 'Do you have the mechanical keyboard in stock? What are the specifications?' as user_query;

-- Query 10: Voice/Text Mixed Query
-- Expected: Should be handled by voice system
SELECT 'Can I order the laptop stand using voice command?' as user_query;

-- =====================================================
-- Display Summary
-- =====================================================
SELECT 'Test Data Setup Complete!' as status;
SELECT 'Test Users Created' as description, COUNT(*) as count FROM shopcore.users;
SELECT 'Test Products Created' as description, COUNT(*) as count FROM shopcore.products;
SELECT 'Test Orders Created' as description, COUNT(*) as count FROM shopcore.orders;
SELECT 'Test Shipments Created' as description, COUNT(*) as count FROM shipstream.shipments;
SELECT 'Test Tickets Created' as description, COUNT(*) as count FROM caredesk.tickets;
SELECT 'Test Wallets Created' as description, COUNT(*) as count FROM payguard.wallets;
SELECT 'Test Payment Methods Created' as description, COUNT(*) as count FROM payguard.payment_methods;
SELECT 'Test Transactions Created' as description, COUNT(*) as count FROM payguard.transactions;
