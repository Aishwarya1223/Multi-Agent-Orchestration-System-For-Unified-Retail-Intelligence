# OmniFlow Database Setup Guide

This directory contains all the necessary files to set up the complete OmniFlow database with dummy data for testing and development.

## 📁 Files Overview

### Core Database Files

### 1. `shopcore.sql`
**Purpose**: Core e-commerce functionality
- **Users**: Customer accounts with premium status
- **Products**: Product catalog with categories and pricing
- **Orders**: Customer orders with status tracking
- **Sample Data**: 20 users, 10 products, 20 orders
- **Views**: order_summary, customer_order_history, product_performance

### 2. `shipstream.sql`
**Purpose**: Shipment and logistics management
- **Warehouses**: Storage locations across India
- **Shipments**: Forward shipment tracking
- **Tracking Events**: Detailed shipment journey
- **NDR Events**: Non-delivery reports and resolutions
- **Reverse Shipments**: Return and refund processing
- **Exchange Shipments**: Product exchange management
- **Sample Data**: 10 warehouses, 20 shipments, 8 NDR events, 5 returns, 3 exchanges
- **Views**: shipment_summary, reverse_shipment_summary, exchange_shipment_summary, warehouse_performance, ndr_analytics

### 3. `caredesk.sql`
**Purpose**: Customer support and ticketing system
- **Tickets**: Customer support tickets
- **Ticket Messages**: Conversation history
- **Satisfaction Surveys**: Customer feedback collection
- **Sample Data**: 10 tickets, 15 messages, 8 surveys
- **Views**: ticket_summary, agent_performance, satisfaction_metrics, issue_type_analysis

### 4. `payguard.sql`
**Purpose**: Payment and wallet management
- **Wallets**: Customer digital wallets
- **Payment Methods**: Saved payment options
- **Transactions**: Payment history and processing
- **Sample Data**: 20 wallets, 25 payment methods, 28 transactions
- **Views**: wallet_summary, transaction_summary, user_transaction_history, payment_method_usage

### 5. `dummy_shipment_data.json`
**Purpose**: Raw shipment data in JSON format
- **Forward Shipments**: 20 records with delivery status
- **Reverse Shipments**: 5 return records
- **NDR Shipments**: 8 non-delivery events
- **Exchange Shipments**: 3 exchange records

### 6. `shipstream_data_import.sql`
**Purpose**: Complete ShipStream setup with enhanced schema
- Comprehensive table creation with proper relationships
- Full dummy data import
- Advanced views for analytics
- Performance indexes

### 7. `shipstream_data_from_json.sql`
**Purpose**: Generated SQL from JSON data
- 68 lines of SQL statements
- Alternative import method

### 8. `generate_shipment_sql.py`
**Purpose**: Python script to convert JSON to SQL
- Dynamic SQL generation
- Error handling and validation

### 9. `setup_database.bat`
**Purpose**: Windows batch script for easy setup
- Interactive menu system
- Automated database creation
- Error handling

## 🚀 Quick Setup

### Option 1: Complete Database Setup (Recommended)
```sql
-- Run each database script in order
SOURCE shopcore.sql;
SOURCE shipstream.sql;
SOURCE caredesk.sql;
SOURCE payguard.sql;
```

### Option 2: Use Batch Script (Windows)
```batch
setup_database.bat
```

### Option 3: Individual Module Setup

#### ShopCore (E-commerce)
```sql
SOURCE shopcore.sql;
```

#### ShipStream (Logistics)
```sql
SOURCE shipstream.sql;
```

#### CareDesk (Support)
```sql
SOURCE caredesk.sql;
```

#### PayGuard (Payments)
```sql
SOURCE payguard.sql;
```

## 📊 Database Schema Overview

### ShopCore Database
```
users (id, name, email, premium_status)
  ↓
orders (id, user_id, product_id, order_date, status, amount)
  ↓
products (id, name, category, price, stock_quantity)
```

### ShipStream Database
```
warehouses (id, location, manager_name)
  ↓
shipments (id, order_id, tracking_number, status)
  ↓
tracking_events (id, shipment_id, timestamp, status_update)
  ↓
ndr_events (id, shipment_id, issue, final_outcome)
  ↓
reverse_shipments (id, original_shipment_id, refund_status)
  ↓
exchange_shipments (id, original_shipment_id, new_item)
```

### CareDesk Database
```
tickets (id, user_id, reference_id, issue_type, status)
  ↓
ticket_messages (id, ticket_id, sender, content, timestamp)
  ↓
satisfaction_surveys (id, ticket_id, rating, comments)
```

### PayGuard Database
```
users (from shopcore)
  ↓
wallets (id, user_id, balance, currency)
  ↓
payment_methods (id, wallet_id, provider, method_type)
  ↓
transactions (id, wallet_id, order_id, amount, type, status)
```

## 📈 Data Summary

### ShopCore
- **20 Users** (10 premium, 10 standard)
- **10 Products** across Electronics, Sports, Accessories, Home Appliances
- **20 Orders** with various statuses (Delivered, RTO_Initiated, Exchanged)

### ShipStream
- **10 Warehouses** across major Indian cities
- **20 Forward Shipments** (12 Delivered, 5 RTO, 3 Exchanged)
- **8 NDR Events** (3 resolved as delivered, 5 resulted in RTO)
- **5 Reverse Shipments** (3 processed refunds, 2 pending)
- **3 Exchange Shipments** (1 dispatched, 1 in transit, 1 delivered)

### CareDesk
- **10 Support Tickets** with various issue types
- **15 Ticket Messages** showing customer-agent conversations
- **8 Satisfaction Surveys** with average rating of 4.25/5

### PayGuard
- **20 Wallets** with INR currency
- **25 Payment Methods** (Cards, UPI, NetBanking)
- **28 Transactions** (Debits, Credits, Refunds, Cashback)
- **Total Wallet Balance**: ₹2,66,500

## 🔍 Key Sample Queries

### Cross-Module Analytics
```sql
-- Customer 360° view
SELECT 
    u.name, u.email, u.premium_status,
    COUNT(o.id) as total_orders,
    SUM(o.total_amount) as total_spent,
    w.balance as wallet_balance,
    COUNT(t.id) as support_tickets,
    AVG(sv.rating) as avg_satisfaction
FROM shopcore.users u
LEFT JOIN shopcore.orders o ON u.id = o.user_id
LEFT JOIN payguard.wallets w ON u.id = w.user_id
LEFT JOIN caredesk.tickets t ON u.id = t.user_id
LEFT JOIN caredesk.satisfaction_surveys sv ON t.id = sv.ticket_id
GROUP BY u.id;
```

### Shipment Performance
```sql
-- Delivery success rate by warehouse
SELECT 
    w.location,
    COUNT(s.id) as total_shipments,
    COUNT(CASE WHEN s.status = 'Delivered' THEN 1 END) as delivered,
    ROUND(COUNT(CASE WHEN s.status = 'Delivered' THEN 1 END) * 100.0 / COUNT(s.id), 2) as success_rate
FROM shipstream.warehouses w
JOIN shipstream.tracking_events te ON w.id = te.warehouse_id
JOIN shipstream.shipments s ON te.shipment_id = s.id
GROUP BY w.location;
```

### Payment Analytics
```sql
-- Payment method preferences
SELECT 
    pm.provider,
    pm.method_type,
    COUNT(t.id) as usage_count,
    SUM(t.amount) as total_volume,
    AVG(t.amount) as avg_transaction
FROM payguard.payment_methods pm
JOIN payguard.transactions t ON pm.id = t.payment_method_id
WHERE t.status = 'Completed'
GROUP BY pm.provider, pm.method_type
ORDER BY usage_count DESC;
```

## 🔄 Data Relationships

### Foreign Key Relationships
- `shipstream.shipments.order_id` → `shopcore.orders.id`
- `caredesk.tickets.user_id` → `shopcore.users.id`
- `payguard.wallets.user_id` → `shopcore.users.id`
- `payguard.transactions.order_id` → `shopcore.orders.id`
- `shipstream.reverse_shipments.original_shipment_id` → `shipstream.shipments.id`

### Data Flow
1. **Customer** registers in `shopcore.users`
2. **Order** created in `shopcore.orders`
3. **Payment** processed via `payguard.transactions`
4. **Shipment** created in `shipstream.shipments`
5. **Support** ticket created in `caredesk.tickets` if needed
6. **Tracking** events logged in `shipstream.tracking_events`
7. **NDR** created if delivery fails
8. **Return/Exchange** processed if required

## 🛠️ Integration with Django

The database schemas align with Django models:

### Model Mappings:
- `shopcore.models.User` → `shopcore.users`
- `shopcore.models.Product` → `shopcore.products`
- `shopcore.models.Order` → `shopcore.orders`
- `shipstream.models.Warehouse` → `shipstream.warehouses`
- `shipstream.models.Shipment` → `shipstream.shipments`
- `shipstream.models.TrackingEvent` → `shipstream.tracking_events`
- `caredesk.models.Ticket` → `caredesk.tickets`
- `caredesk.models.TicketMessage` → `caredesk.ticket_messages`
- `caredesk.models.SatisfactionSurvey` → `caredesk.satisfaction_surveys`
- `payguard.models.Wallet` → `payguard.wallets`
- `payguard.models.PaymentMethod` → `payguard.payment_methods`
- `payguard.models.Transaction` → `payguard.transactions`

## 🔄 Data Updates

To update the data:
1. Modify `dummy_shipment_data.json` for shipment data
2. Modify individual SQL files for other modules
3. Run `python generate_shipment_sql.py` for shipment SQL
4. Execute the updated SQL scripts

## 📝 Notes

- All dates are in 2023 for consistency
- Customer names are Indian names for regional relevance
- Amounts are in INR (Indian Rupees)
- Tracking numbers follow patterns: FWD-XXXX, REV-XXXX, NDR-XXX, EXC-XXX
- The scripts include proper foreign key relationships and indexes for performance
- All databases are independent but interconnected through foreign keys

## 🐛 Troubleshooting

### Common Issues:
1. **Foreign Key Constraints**: Ensure tables are created in the correct order
2. **Cross-Database References**: Use fully qualified names (database.table)
3. **Date Format**: All dates should be in 'YYYY-MM-DD' format
4. **Character Encoding**: Use UTF-8 encoding for special characters

### Solutions:
- Use the complete setup scripts (handles dependencies)
- Check MySQL version compatibility (tested with MySQL 8.0+)
- Ensure proper permissions for CREATE/DROP operations
- Run databases in sequence: shopcore → shipstream → caredesk → payguard

## 📊 Expected Results

After complete setup, you'll have:
- **Fully integrated e-commerce platform**
- **Complete shipment tracking system**
- **Customer support infrastructure**
- **Payment processing system**
- **Realistic Indian market data**
- **Cross-module analytics capabilities**
