-- =====================================================
-- CareDesk Database Setup
-- =====================================================
-- This script creates tables for the CareDesk module

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS caredesk;
USE caredesk;

-- Drop existing tables if they exist (for clean import)
DROP TABLE IF EXISTS satisfaction_surveys;
DROP TABLE IF EXISTS ticket_messages;
DROP TABLE IF EXISTS tickets;

-- Create tickets table
CREATE TABLE tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,                    -- reference to shopcore.User.id
    reference_id VARCHAR(50) NOT NULL,        -- OrderID or TransactionID
    issue_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'Open',
    priority VARCHAR(20) DEFAULT 'Medium',
    assigned_agent_id INT NULL,
    resolution_details TEXT NULL,
    resolved_at TIMESTAMP NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_reference_id (reference_id),
    INDEX idx_status (status),
    INDEX idx_issue_type (issue_type),
    INDEX idx_created_at (created_at)
);

-- Create ticket messages table
CREATE TABLE ticket_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,                   -- reference to Ticket.id
    sender VARCHAR(10) NOT NULL,              -- User / Agent
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_internal BOOLEAN DEFAULT FALSE,           -- Internal notes vs customer messages
    attachment_url VARCHAR(255) NULL,
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_sender (sender)
);

-- Create satisfaction surveys table
CREATE TABLE satisfaction_surveys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,                   -- reference to Ticket.id
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comments TEXT,
    survey_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_by_agent_id INT NULL,
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_rating (rating),
    INDEX idx_survey_date (survey_date)
);

-- =====================================================
-- Insert sample data
-- =====================================================

-- Insert sample tickets (related to shipment issues)
INSERT INTO tickets (user_id, reference_id, issue_type, status, priority, assigned_agent_id, resolution_details, resolved_at) VALUES
-- Delivered orders with minor issues
(1, 'FWD-1001', 'Delivery Delay', 'Resolved', 'Low', 1, 'Customer contacted and package was located. Delivered successfully.', '2023-10-06 10:30:00'),
(2, 'FWD-1002', 'Product Query', 'Resolved', 'Low', 2, 'Provided detailed product information and usage instructions.', '2023-10-07 14:20:00'),
(3, 'FWD-1003', 'Billing Issue', 'Resolved', 'Medium', 1, 'Billing discrepancy corrected and refund processed.', '2023-10-08 11:45:00'),

-- RTO related tickets
(13, 'FWD-1013', 'Return Request', 'In Progress', 'High', 3, 'Customer refused delivery. Return process initiated.', NULL),
(14, 'FWD-1014', 'Address Correction', 'In Progress', 'High', 2, 'Address incomplete. Awaiting customer confirmation.', NULL),
(15, 'FWD-1015', 'Return Request', 'In Progress', 'High', 1, 'Customer unavailable during delivery. Return scheduled.', NULL),
(16, 'FWD-1016', 'Damaged Product', 'In Progress', 'High', 3, 'Product damaged in transit. Return and replacement initiated.', NULL),
(17, 'FWD-1017', 'Payment Issue', 'In Progress', 'High', 2, 'COD amount mismatch. Investigation in progress.', NULL),

-- Exchange related tickets
(18, 'FWD-1018', 'Exchange Request', 'Resolved', 'Medium', 1, 'Size exchange processed. New item dispatched.', '2023-10-13 16:00:00'),
(19, 'FWD-1019', 'Exchange Request', 'In Progress', 'Medium', 2, 'Color exchange requested. Processing new order.', NULL),
(20, 'FWD-1020', 'Defective Product', 'Resolved', 'High', 3, 'Defective item replaced. New product delivered.', '2023-10-16 09:30:00'),

-- General support tickets
(5, 'FWD-1005', 'Order Status', 'Resolved', 'Low', 1, 'Provided real-time tracking information.', '2023-10-04 13:15:00'),
(8, 'FWD-1008', 'Product Information', 'Resolved', 'Low', 2, 'Shared detailed product specifications and warranty info.', '2023-10-05 15:30:00'),
(10, 'FWD-1010', 'Delivery Instructions', 'Resolved', 'Medium', 1, 'Updated delivery instructions in system.', '2023-10-06 12:45:00');

-- Insert sample ticket messages
INSERT INTO ticket_messages (ticket_id, sender, content, timestamp, is_internal) VALUES
-- Ticket 1 - Delivery Delay
(1, 'User', 'My order FWD-1001 was supposed to be delivered yesterday but I haven''t received it yet.', '2023-10-05 09:00:00', FALSE),
(1, 'Agent', 'I apologize for the delay. Let me check the tracking information for you.', '2023-10-05 09:15:00', FALSE),
(1, 'Agent', 'I can see your package is out for delivery today. You should receive it by 6 PM.', '2023-10-05 09:30:00', FALSE),
(1, 'User', 'Thank you for the update. I''ll wait for the delivery.', '2023-10-05 09:45:00', FALSE),
(1, 'Agent', 'Package delivered successfully. Ticket marked as resolved.', '2023-10-06 10:30:00', FALSE),

-- Ticket 13 - Return Request
(13, 'User', 'I want to return order FWD-1013. I refused the delivery as the product was not what I ordered.', '2023-10-08 11:00:00', FALSE),
(13, 'Agent', 'I understand your concern. Let me help you with the return process.', '2023-10-08 11:15:00', FALSE),
(13, 'Agent', 'Return request initiated. You will receive refund instructions via email.', '2023-10-08 11:30:00', FALSE),
(13, 'User', 'When can I expect the refund to be processed?', '2023-10-09 10:00:00', FALSE),
(13, 'Agent', 'Refund will be processed within 5-7 business days after we receive the returned item.', '2023-10-09 10:15:00', FALSE),

-- Ticket 18 - Exchange Request
(18, 'User', 'I received order FWD-1018 but the size is wrong. I need size L instead of M.', '2023-10-11 14:00:00', FALSE),
(18, 'Agent', 'I apologize for the size error. I can help you with an exchange.', '2023-10-11 14:15:00', FALSE),
(18, 'Agent', 'Exchange request processed. Size L will be dispatched within 24 hours.', '2023-10-11 14:30:00', FALSE),
(18, 'User', 'Thank you! Do I need to return the wrong size?', '2023-10-11 14:45:00', FALSE),
(18, 'Agent', 'Yes, a reverse pickup has been scheduled for tomorrow.', '2023-10-11 15:00:00', FALSE),
(18, 'Agent', 'New item dispatched. Tracking number for exchange: EXC-201', '2023-10-12 16:00:00', FALSE);

-- Insert sample satisfaction surveys
INSERT INTO satisfaction_surveys (ticket_id, rating, comments, survey_date, resolved_by_agent_id) VALUES
(1, 5, 'Quick response and effective resolution. Very satisfied with the service!', '2023-10-07 09:00:00', 1),
(2, 4, 'Good service but took a bit longer than expected to get product details.', '2023-10-08 10:00:00', 2),
(3, 5, 'Billing issue was resolved quickly and professionally. Thank you!', '2023-10-09 11:00:00', 1),
(5, 4, 'Agent was helpful in providing tracking information.', '2023-10-05 14:00:00', 1),
(8, 5, 'Excellent product information provided. Very detailed and helpful.', '2023-10-06 15:00:00', 2),
(10, 3, 'Delivery instructions were updated but could have been faster.', '2023-10-07 16:00:00', 1),
(18, 5, 'Perfect exchange process! Agent was very helpful and professional.', '2023-10-14 09:00:00', 1),
(20, 4, 'Defective product was replaced quickly. Good service overall.', '2023-10-17 10:00:00', 3);

-- =====================================================
-- Create views for easy querying
-- =====================================================

-- View for ticket summary with user information
CREATE VIEW ticket_summary AS
SELECT 
    t.id as ticket_id,
    t.reference_id,
    t.issue_type,
    t.status,
    t.priority,
    t.created_at,
    t.resolved_at,
    CASE 
        WHEN t.resolved_at IS NOT NULL 
        THEN TIMESTAMPDIFF(HOUR, t.created_at, t.resolved_at)
        ELSE NULL
    END as resolution_hours,
    COUNT(tm.id) as message_count
FROM tickets t
LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
GROUP BY t.id, t.reference_id, t.issue_type, t.status, t.priority, t.created_at, t.resolved_at;

-- View for agent performance
CREATE VIEW agent_performance AS
SELECT 
    assigned_agent_id as agent_id,
    COUNT(*) as total_tickets,
    COUNT(CASE WHEN status = 'Resolved' THEN 1 END) as resolved_tickets,
    AVG(CASE WHEN resolved_at IS NOT NULL 
        THEN TIMESTAMPDIFF(HOUR, created_at, resolved_at) 
        END) as avg_resolution_time,
    COUNT(CASE WHEN priority = 'High' THEN 1 END) as high_priority_tickets
FROM tickets
WHERE assigned_agent_id IS NOT NULL
GROUP BY assigned_agent_id;

-- View for customer satisfaction metrics
CREATE VIEW satisfaction_metrics AS
SELECT 
    AVG(rating) as avg_rating,
    COUNT(*) as total_surveys,
    COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_ratings,
    COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_ratings,
    ROUND(COUNT(CASE WHEN rating >= 4 THEN 1 END) * 100.0 / COUNT(*), 2) as satisfaction_rate
FROM satisfaction_surveys;

-- View for issue type analysis
CREATE VIEW issue_type_analysis AS
SELECT 
    issue_type,
    COUNT(*) as total_tickets,
    COUNT(CASE WHEN status = 'Resolved' THEN 1 END) as resolved_tickets,
    AVG(CASE WHEN resolved_at IS NOT NULL 
        THEN TIMESTAMPDIFF(HOUR, created_at, resolved_at) 
        END) as avg_resolution_time
FROM tickets
GROUP BY issue_type
ORDER BY total_tickets DESC;

-- =====================================================
-- Display summary
-- =====================================================
SELECT 'CareDesk Database Setup Complete!' as status;
SELECT COUNT(*) as total_tickets FROM tickets;
SELECT COUNT(*) as total_messages FROM ticket_messages;
SELECT COUNT(*) as total_surveys FROM satisfaction_surveys;
SELECT AVG(rating) as avg_satisfaction_rating FROM satisfaction_surveys;