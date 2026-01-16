-- =====================================================
-- ShopCore Database Setup
-- =====================================================
-- This script creates tables for the ShopCore module

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS shopcore;
USE shopcore;

-- Drop existing tables if they exist (for clean import)
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

-- Create users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    premium_status BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_premium_status (premium_status)
);

-- Create products table
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,
    stock_quantity INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_name (name),
    INDEX idx_price (price)
);

-- Create orders table
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    order_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Pending',
    quantity INT DEFAULT 1,
    total_amount DECIMAL(10, 2) NOT NULL,
    shipping_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_product_id (product_id),
    INDEX idx_order_date (order_date),
    INDEX idx_status (status)
);

-- =====================================================
-- Insert sample data
-- =====================================================

-- Insert sample users
INSERT INTO users (name, email, premium_status) VALUES
('Aarav Patel', 'aarav.patel@email.com', TRUE),
('Vihaan Reddy', 'vihaan.reddy@email.com', FALSE),
('Aditya Sharma', 'aditya.sharma@email.com', TRUE),
('Sai Kumar', 'sai.kumar@email.com', FALSE),
('Reyansh Singh', 'reyansh.singh@email.com', TRUE),
('Arjun Gupta', 'arjun.gupta@email.com', FALSE),
('Kiara Advani', 'kiara.advani@email.com', TRUE),
('Ishaan Verma', 'ishaan.verma@email.com', FALSE),
('Saanvi Mehta', 'saanvi.mehta@email.com', TRUE),
('Ayaan Khan', 'ayaan.khan@email.com', FALSE),
('Zara Siddiqui', 'zara.siddiqui@email.com', TRUE),
('Kabir Das', 'kabir.das@email.com', FALSE),
('Ananya Roy', 'ananya.roy@email.com', TRUE),
('Rohan Joshi', 'rohan.joshi@email.com', FALSE),
('Meera Nair', 'meera.nair@email.com', TRUE),
('Dhruv Malhotra', 'dhruv.malhotra@email.com', FALSE),
('Naira Kapoor', 'naira.kapoor@email.com', TRUE),
('Arnav Singh', 'arnav.singh@email.com', FALSE),
('Pari Chopra', 'pari.chopra@email.com', TRUE),
('Vivaan Jain', 'vivaan.jain@email.com', FALSE);

-- Insert sample products
INSERT INTO products (name, category, price, description, stock_quantity) VALUES
('Wireless Headphones', 'Electronics', 2999.99, 'Premium noise-cancelling wireless headphones with 30-hour battery life', 50),
('Smart Watch', 'Electronics', 4599.99, 'Fitness tracking smartwatch with heart rate monitor and GPS', 35),
('Laptop Backpack', 'Accessories', 899.99, 'Water-resistant laptop backpack with USB charging port', 75),
('Running Shoes', 'Sports', 2499.99, 'Professional running shoes with advanced cushioning technology', 60),
('Yoga Mat', 'Sports', 599.99, 'Non-slip exercise yoga mat with carrying strap', 100),
('Coffee Maker', 'Home Appliances', 3299.99, 'Automatic drip coffee maker with thermal carafe', 25),
('Desk Lamp', 'Home Appliances', 799.99, 'LED desk lamp with adjustable brightness and color temperature', 45),
('Bluetooth Speaker', 'Electronics', 1899.99, 'Portable waterproof Bluetooth speaker with 12-hour battery', 80),
('Water Bottle', 'Accessories', 299.99, 'Insulated stainless steel water bottle, 1 liter capacity', 120),
('Phone Case', 'Accessories', 499.99, 'Shock-absorbent phone case with screen protector included', 200);

-- Insert sample orders (matching the shipment data)
INSERT INTO orders (user_id, product_id, order_date, status, quantity, total_amount, shipping_address) VALUES
(1, 1, '2023-10-01', 'Delivered', 1, 1200.00, '123 Main St, Mumbai, Maharashtra 400001'),
(2, 2, '2023-10-01', 'Delivered', 1, 850.00, '456 Park Ave, Delhi, Delhi 110001'),
(3, 3, '2023-10-02', 'Delivered', 1, 2100.00, '789 Market Rd, Bangalore, Karnataka 560001'),
(4, 4, '2023-10-02', 'Delivered', 1, 450.00, '321 College St, Chennai, Tamil Nadu 600001'),
(5, 5, '2023-10-03', 'Delivered', 1, 3200.00, '654 Station Rd, Hyderabad, Telangana 500001'),
(6, 6, '2023-10-03', 'Delivered', 1, 1500.00, '987 Temple St, Kolkata, West Bengal 700001'),
(7, 7, '2023-10-04', 'Delivered', 1, 900.00, '147 Beach Rd, Pune, Maharashtra 411001'),
(8, 8, '2023-10-04', 'Delivered', 1, 2500.00, '258 Mountain View, Jaipur, Rajasthan 302001'),
(9, 9, '2023-10-05', 'Delivered', 1, 600.00, '369 River Side, Lucknow, Uttar Pradesh 226001'),
(10, 10, '2023-10-05', 'Delivered', 1, 1100.00, '741 Garden Ave, Ahmedabad, Gujarat 380001'),
(11, 1, '2023-10-06', 'Delivered', 1, 3400.00, '852 Business Park, Gurgaon, Haryana 122001'),
(12, 2, '2023-10-06', 'Delivered', 1, 550.00, '963 Tech Hub, Noida, Uttar Pradesh 201301'),
(13, 3, '2023-10-07', 'RTO_Initiated', 1, 1800.00, '159 Shopping Mall, Chandigarh 160001'),
(14, 4, '2023-10-07', 'RTO_Initiated', 1, 950.00, '753 Industrial Area, Coimbatore, Tamil Nadu 641001'),
(15, 5, '2023-10-08', 'RTO_Initiated', 1, 2200.00, '456 Residential Complex, Kochi, Kerala 682001'),
(16, 6, '2023-10-08', 'RTO_Initiated', 1, 300.00, '821 IT Park, Indore, Madhya Pradesh 452001'),
(17, 7, '2023-10-09', 'RTO_Initiated', 1, 4100.00, '369 Corporate Tower, Nagpur, Maharashtra 440001'),
(18, 8, '2023-10-09', 'Exchanged', 1, 1250.00, '147 Service Center, Visakhapatnam, Andhra Pradesh 530001'),
(19, 9, '2023-10-10', 'Exchanged', 1, 2700.00, '258 Repair Shop, Bhopal, Madhya Pradesh 462001'),
(20, 10, '2023-10-10', 'Exchanged', 1, 890.00, '741 Outlet, Guwahati, Assam 781001');

-- =====================================================
-- Create views for easy querying
-- =====================================================

-- View for order summary with user and product details
CREATE VIEW order_summary AS
SELECT 
    o.id as order_id,
    o.order_date,
    o.status,
    o.quantity,
    o.total_amount,
    u.name as customer_name,
    u.email as customer_email,
    u.premium_status,
    p.name as product_name,
    p.category as product_category,
    p.price as unit_price
FROM orders o
JOIN users u ON o.user_id = u.id
JOIN products p ON o.product_id = p.id;

-- View for customer order history
CREATE VIEW customer_order_history AS
SELECT 
    u.id as user_id,
    u.name as customer_name,
    u.email as customer_email,
    COUNT(o.id) as total_orders,
    SUM(o.total_amount) as total_spent,
    AVG(o.total_amount) as avg_order_value,
    MAX(o.order_date) as last_order_date
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.name, u.email;

-- View for product performance
CREATE VIEW product_performance AS
SELECT 
    p.id as product_id,
    p.name as product_name,
    p.category,
    p.price,
    p.stock_quantity,
    COUNT(o.id) as times_ordered,
    COALESCE(SUM(o.quantity), 0) as total_quantity_sold,
    COALESCE(SUM(o.total_amount), 0) as total_revenue
FROM products p
LEFT JOIN orders o ON p.id = o.product_id
GROUP BY p.id, p.name, p.category, p.price, p.stock_quantity;

-- =====================================================
-- Display summary
-- =====================================================
SELECT 'ShopCore Database Setup Complete!' as status;
SELECT COUNT(*) as total_users FROM users;
SELECT COUNT(*) as total_products FROM products;
SELECT COUNT(*) as total_orders FROM orders;
SELECT COUNT(*) as premium_users FROM users WHERE premium_status = TRUE;