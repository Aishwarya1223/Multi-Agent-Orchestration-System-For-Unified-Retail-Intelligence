-- =====================================================
-- PayGuard Database Setup
-- =====================================================
-- This script creates tables for the PayGuard module

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS payguard;
USE payguard;

-- Drop existing tables if they exist (for clean import)
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS payment_methods;
DROP TABLE IF EXISTS wallets;

-- Create wallets table
CREATE TABLE wallets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,                   -- reference to shopcore.User.id
    balance DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    wallet_type VARCHAR(20) DEFAULT 'Standard', -- Standard, Premium, Business
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_currency (currency),
    INDEX idx_wallet_type (wallet_type),
    UNIQUE KEY unique_user_wallet (user_id, currency)
);

-- Create payment methods table
CREATE TABLE payment_methods (
    id INT AUTO_INCREMENT PRIMARY KEY,
    wallet_id INT NOT NULL,                  -- reference to Wallet.id
    provider VARCHAR(50) NOT NULL,            -- Visa, Mastercard, UPI, NetBanking, etc.
    method_type VARCHAR(20) NOT NULL,          -- Credit Card, Debit Card, UPI, NetBanking
    last_four_digits VARCHAR(4),               -- For cards
    expiry_date DATE NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (wallet_id) REFERENCES wallets(id) ON DELETE CASCADE,
    INDEX idx_wallet_id (wallet_id),
    INDEX idx_provider (provider),
    INDEX idx_method_type (method_type)
);

-- Create transactions table
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    wallet_id INT NOT NULL,                   -- reference to Wallet.id
    order_id INT NULL,                        -- reference to shopcore.Order.id
    transaction_id VARCHAR(50) NOT NULL UNIQUE,
    amount DECIMAL(12, 2) NOT NULL,
    type VARCHAR(10) NOT NULL,                -- Debit, Credit, Refund, Cashback
    status VARCHAR(20) NOT NULL DEFAULT 'Pending', -- Pending, Completed, Failed, Cancelled
    payment_method_id INT NULL,                 -- reference to PaymentMethods.id
    description TEXT,
    metadata JSON NULL,                        -- Additional transaction details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (wallet_id) REFERENCES wallets(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id) ON DELETE SET NULL,
    INDEX idx_wallet_id (wallet_id),
    INDEX idx_order_id (order_id),
    INDEX idx_transaction_id (transaction_id),
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- =====================================================
-- Insert sample data
-- =====================================================

-- Insert sample wallets (for users 1-20 from shopcore)
INSERT INTO wallets (user_id, balance, currency, wallet_type) VALUES
(1, 15000.00, 'INR', 'Premium'),
(2, 8500.00, 'INR', 'Standard'),
(3, 25000.00, 'INR', 'Premium'),
(4, 4500.00, 'INR', 'Standard'),
(5, 32000.00, 'INR', 'Business'),
(6, 12000.00, 'INR', 'Standard'),
(7, 9000.00, 'INR', 'Standard'),
(8, 22000.00, 'INR', 'Premium'),
(9, 6000.00, 'INR', 'Standard'),
(10, 11000.00, 'INR', 'Standard'),
(11, 34000.00, 'INR', 'Business'),
(12, 5500.00, 'INR', 'Standard'),
(13, 18000.00, 'INR', 'Premium'),
(14, 9500.00, 'INR', 'Standard'),
(15, 22000.00, 'INR', 'Premium'),
(16, 3000.00, 'INR', 'Standard'),
(17, 41000.00, 'INR', 'Business'),
(18, 12500.00, 'INR', 'Standard'),
(19, 27000.00, 'INR', 'Premium'),
(20, 8900.00, 'INR', 'Standard');

-- Insert sample payment methods
INSERT INTO payment_methods (wallet_id, provider, method_type, last_four_digits, expiry_date, is_default) VALUES
-- User 1 - Multiple payment methods
(1, 'Visa', 'Credit Card', '4567', '2025-12-31', TRUE),
(1, 'Mastercard', 'Debit Card', '8901', '2024-08-31', FALSE),
(1, 'PhonePe', 'UPI', NULL, NULL, FALSE),

-- User 2
(2, 'RuPay', 'Debit Card', '2345', '2025-06-30', TRUE),
(2, 'Google Pay', 'UPI', NULL, NULL, FALSE),

-- User 3
(3, 'American Express', 'Credit Card', '7890', '2025-03-31', TRUE),
(3, 'Paytm', 'UPI', NULL, NULL, FALSE),

-- User 4
(4, 'Visa', 'Debit Card', '1234', '2024-11-30', TRUE),

-- User 5
(5, 'Mastercard', 'Credit Card', '5678', '2025-09-30', TRUE),
(5, 'NetBanking', 'NetBanking', NULL, NULL, FALSE),

-- User 6
(6, 'Visa', 'Credit Card', '9012', '2025-07-31', TRUE),

-- User 7
(7, 'RuPay', 'Credit Card', '3456', '2025-01-31', TRUE),

-- User 8
(8, 'Mastercard', 'Debit Card', '6789', '2024-10-31', TRUE),
(8, 'PhonePe', 'UPI', NULL, NULL, FALSE),

-- User 9
(9, 'Visa', 'Debit Card', '0123', '2025-04-30', TRUE),

-- User 10
(10, 'RuPay', 'Debit Card', '4567', '2025-08-31', TRUE),

-- User 11
(11, 'American Express', 'Credit Card', '8901', '2025-12-31', TRUE),
(11, 'Google Pay', 'UPI', NULL, NULL, FALSE),

-- User 12
(12, 'Visa', 'Debit Card', '2345', '2024-09-30', TRUE),

-- User 13
(13, 'Mastercard', 'Credit Card', '6789', '2025-06-30', TRUE),

-- User 14
(14, 'RuPay', 'Debit Card', '0123', '2025-03-31', TRUE),

-- User 15
(15, 'Visa', 'Credit Card', '3456', '2025-11-30', TRUE),

-- User 16
(16, 'Mastercard', 'Debit Card', '7890', '2024-07-31', TRUE),

-- User 17
(17, 'American Express', 'Credit Card', '1234', '2025-10-31', TRUE),
(17, 'Paytm', 'UPI', NULL, NULL, FALSE),

-- User 18
(18, 'Visa', 'Debit Card', '5678', '2025-05-31', TRUE),

-- User 19
(19, 'Mastercard', 'Credit Card', '9012', '2025-08-31', TRUE),

-- User 20
(20, 'RuPay', 'Debit Card', '2345', '2024-12-31', TRUE);

-- Insert sample transactions (related to orders)
INSERT INTO transactions (wallet_id, order_id, transaction_id, amount, type, status, payment_method_id, description, metadata) VALUES
-- Successful transactions for delivered orders
(1, 1, 'TXN001', 1200.00, 'Debit', 'Completed', 1, 'Payment for Order FWD-1001', '{"gateway": "Visa", "auth_code": "123456"}'),
(2, 2, 'TXN002', 850.00, 'Debit', 'Completed', 4, 'Payment for Order FWD-1002', '{"gateway": "RuPay", "auth_code": "234567"}'),
(3, 3, 'TXN003', 2100.00, 'Debit', 'Completed', 6, 'Payment for Order FWD-1003', '{"gateway": "Amex", "auth_code": "345678"}'),
(4, 4, 'TXN004', 450.00, 'Debit', 'Completed', 9, 'Payment for Order FWD-1004', '{"gateway": "Visa", "auth_code": "456789"}'),
(5, 5, 'TXN005', 3200.00, 'Debit', 'Completed', 11, 'Payment for Order FWD-1005', '{"gateway": "Mastercard", "auth_code": "567890"}'),
(6, 6, 'TXN006', 1500.00, 'Debit', 'Completed', 13, 'Payment for Order FWD-1006', '{"gateway": "Visa", "auth_code": "678901"}'),
(7, 7, 'TXN007', 900.00, 'Debit', 'Completed', 16, 'Payment for Order FWD-1007', '{"gateway": "RuPay", "auth_code": "789012"}'),
(8, 8, 'TXN008', 2500.00, 'Debit', 'Completed', 17, 'Payment for Order FWD-1008', '{"gateway": "Mastercard", "auth_code": "890123"}'),
(9, 9, 'TXN009', 600.00, 'Debit', 'Completed', 19, 'Payment for Order FWD-1009', '{"gateway": "Visa", "auth_code": "901234"}'),
(10, 10, 'TXN010', 1100.00, 'Debit', 'Completed', 21, 'Payment for Order FWD-1010', '{"gateway": "RuPay", "auth_code": "012345"}'),

-- More transactions
(11, 11, 'TXN011', 3400.00, 'Debit', 'Completed', 22, 'Payment for Order FWD-1011', '{"gateway": "Amex", "auth_code": "123456"}'),
(12, 12, 'TXN012', 550.00, 'Debit', 'Completed', 24, 'Payment for Order FWD-1012', '{"gateway": "Visa", "auth_code": "234567"}'),
(13, 13, 'TXN013', 1800.00, 'Debit', 'Completed', 26, 'Payment for Order FWD-1013', '{"gateway": "Mastercard", "auth_code": "345678"}'),
(14, 14, 'TXN014', 950.00, 'Debit', 'Completed', 28, 'Payment for Order FWD-1014', '{"gateway": "RuPay", "auth_code": "456789"}'),
(15, 15, 'TXN015', 2200.00, 'Debit', 'Completed', 30, 'Payment for Order FWD-1015', '{"gateway": "Visa", "auth_code": "567890"}'),

-- Refund transactions for RTO orders
(13, NULL, 'TXN016', 1800.00, 'Refund', 'Completed', 26, 'Refund for Order FWD-1013 - RTO', '{"reason": "RTO", "original_txn": "TXN013"}'),
(14, NULL, 'TXN017', 950.00, 'Refund', 'Completed', 28, 'Refund for Order FWD-1014 - RTO', '{"reason": "RTO", "original_txn": "TXN014"}'),
(15, NULL, 'TXN018', 2200.00, 'Refund', 'Completed', 30, 'Refund for Order FWD-1015 - RTO', '{"reason": "RTO", "original_txn": "TXN015"}'),
(16, NULL, 'TXN019', 300.00, 'Refund', 'Completed', 32, 'Refund for Order FWD-1016 - RTO', '{"reason": "RTO", "original_txn": "TXN016"}'),
(17, NULL, 'TXN020', 4100.00, 'Refund', 'Completed', 34, 'Refund for Order FWD-1017 - RTO', '{"reason": "RTO", "original_txn": "TXN017"}'),

-- Exchange transactions
(18, 18, 'TXN021', 1250.00, 'Debit', 'Completed', 36, 'Payment for Exchange Order EXC-201', '{"gateway": "Visa", "auth_code": "678901"}'),
(19, 19, 'TXN022', 2700.00, 'Debit', 'Completed', 38, 'Payment for Exchange Order EXC-202', '{"gateway": "Mastercard", "auth_code": "789012"}'),
(20, 20, 'TXN023', 890.00, 'Debit', 'Completed', 40, 'Payment for Exchange Order EXC-203', '{"gateway": "RuPay", "auth_code": "890123"}'),

-- Cashback and bonus transactions
(1, NULL, 'TXN024', 100.00, 'Credit', 'Completed', NULL, 'Welcome bonus for new wallet', '{"bonus_type": "welcome", "campaign": "new_user"}'),
(3, NULL, 'TXN025', 200.00, 'Credit', 'Completed', NULL, 'Cashback on premium membership', '{"bonus_type": "cashback", "percentage": "5%"}'),
(5, NULL, 'TXN026', 150.00, 'Credit', 'Completed', NULL, 'Referral bonus', '{"bonus_type": "referral", "referred_user": "user_25"}'),
(8, NULL, 'TXN027', 300.00, 'Credit', 'Completed', NULL, 'Loyalty points redemption', '{"bonus_type": "loyalty", "points_redeemed": 3000}'),

-- Failed transaction example
(2, NULL, 'TXN028', 500.00, 'Debit', 'Failed', 4, 'Failed transaction - insufficient funds', '{"error_code": "INSUFFICIENT_FUNDS", "gateway": "RuPay"}');

-- =====================================================
-- Create views for easy querying
-- =====================================================

-- View for wallet summary with user information
CREATE VIEW wallet_summary AS
SELECT 
    w.id as wallet_id,
    w.user_id,
    w.balance,
    w.currency,
    w.wallet_type,
    w.is_active,
    w.created_at,
    COUNT(pm.id) as payment_methods_count,
    COUNT(CASE WHEN pm.is_default = TRUE THEN 1 END) as default_payment_methods
FROM wallets w
LEFT JOIN payment_methods pm ON w.id = pm.wallet_id AND pm.is_active = TRUE
GROUP BY w.id, w.user_id, w.balance, w.currency, w.wallet_type, w.is_active, w.created_at;

-- View for transaction summary
CREATE VIEW transaction_summary AS
SELECT 
    t.id as transaction_id,
    t.transaction_id,
    t.amount,
    t.type,
    t.status,
    t.description,
    t.created_at,
    w.user_id,
    w.currency,
    pm.provider as payment_provider,
    pm.method_type as payment_method_type
FROM transactions t
JOIN wallets w ON t.wallet_id = w.id
LEFT JOIN payment_methods pm ON t.payment_method_id = pm.id;

-- View for user transaction history
CREATE VIEW user_transaction_history AS
SELECT 
    w.user_id,
    COUNT(t.id) as total_transactions,
    COUNT(CASE WHEN t.type = 'Debit' THEN 1 END) as debit_transactions,
    COUNT(CASE WHEN t.type = 'Credit' THEN 1 END) as credit_transactions,
    COUNT(CASE WHEN t.type = 'Refund' THEN 1 END) as refund_transactions,
    SUM(CASE WHEN t.type = 'Debit' THEN t.amount ELSE 0 END) as total_debits,
    SUM(CASE WHEN t.type = 'Credit' THEN t.amount ELSE 0 END) as total_credits,
    SUM(CASE WHEN t.type = 'Refund' THEN t.amount ELSE 0 END) as total_refunds,
    MAX(t.created_at) as last_transaction_date
FROM wallets w
LEFT JOIN transactions t ON w.id = t.wallet_id AND t.status = 'Completed'
GROUP BY w.user_id;

-- View for payment method usage
CREATE VIEW payment_method_usage AS
SELECT 
    pm.id as payment_method_id,
    pm.provider,
    pm.method_type,
    pm.is_default,
    COUNT(t.id) as usage_count,
    COALESCE(SUM(t.amount), 0) as total_amount_processed,
    MAX(t.created_at) as last_used_date
FROM payment_methods pm
LEFT JOIN transactions t ON pm.id = t.payment_method_id AND t.status = 'Completed'
GROUP BY pm.id, pm.provider, pm.method_type, pm.is_default;

-- =====================================================
-- Display summary
-- =====================================================
SELECT 'PayGuard Database Setup Complete!' as status;
SELECT COUNT(*) as total_wallets FROM wallets;
SELECT COUNT(*) as total_payment_methods FROM payment_methods;
SELECT COUNT(*) as total_transactions FROM transactions;
SELECT SUM(balance) as total_wallet_balance FROM wallets;
SELECT AVG(balance) as avg_wallet_balance FROM wallets;