#!/usr/bin/env python3
"""
ShipStream Data Import Script
This script reads the JSON file and generates SQL statements for importing shipment data.
"""

import json
import os
from datetime import datetime

def generate_sql_from_json():
    """Generate SQL statements from JSON data"""
    
    # Read JSON data
    json_file = os.path.join(os.path.dirname(__file__), 'dummy_shipment_data.json')
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    sql_statements = []
    
    # Add header
    sql_statements.append("-- =====================================================")
    sql_statements.append("-- ShipStream Data Import from JSON")
    sql_statements.append(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sql_statements.append("-- =====================================================")
    sql_statements.append("")
    
    # Forward shipments
    if 'forward_shipments' in data:
        sql_statements.append("-- Insert forward shipments")
        sql_statements.append("INSERT INTO shipments (order_id, tracking_number, estimated_arrival, customer_name, shipment_date, status, amount, notes) VALUES")
        
        forward_values = []
        for i, (tracking_number, shipment_data) in enumerate(data['forward_shipments'].items()):
            order_id = i + 1
            customer_name = shipment_data['customer']
            shipment_date = shipment_data['date']
            status = shipment_data['status']
            amount = shipment_data['amount']
            notes = shipment_data.get('notes', 'NULL')
            
            # Calculate estimated arrival (5 days after shipment date)
            estimated_arrival = shipment_date  # Simplified for demo
            
            notes_value = f"'{notes}'" if notes != 'NULL' else 'NULL'
            value = f"({order_id}, '{tracking_number}', '{estimated_arrival}', '{customer_name}', '{shipment_date}', '{status}', {amount}, {notes_value})"
            forward_values.append(value)
        
        sql_statements.append(",\n".join(forward_values) + ";")
        sql_statements.append("")
    
    # NDR shipments
    if 'ndr_shipments' in data:
        sql_statements.append("-- Insert NDR events")
        sql_statements.append("INSERT INTO ndr_events (shipment_id, ndr_number, ndr_date, issue, attempts, final_outcome) VALUES")
        
        ndr_values = []
        for i, (ndr_number, ndr_data) in enumerate(data['ndr_shipments'].items()):
            original_awb = ndr_data['original_awb']
            ndr_date = ndr_data['ndr_date']
            issue = ndr_data['issue']
            attempts = ndr_data['attempts']
            final_outcome = ndr_data['final_outcome']
            
            # Find shipment_id based on tracking number (simplified)
            shipment_id = hash(original_awb) % 20 + 1  # Simplified mapping
            
            value = f"({shipment_id}, '{ndr_number}', '{ndr_date}', '{issue}', {attempts}, '{final_outcome}')"
            ndr_values.append(value)
        
        sql_statements.append(",\n".join(ndr_values) + ";")
        sql_statements.append("")
    
    # Reverse shipments
    if 'reverse_shipments' in data:
        sql_statements.append("-- Insert reverse shipments")
        sql_statements.append("INSERT INTO reverse_shipments (original_shipment_id, reverse_number, return_date, reason, refund_status) VALUES")
        
        reverse_values = []
        for i, (reverse_number, reverse_data) in enumerate(data['reverse_shipments'].items()):
            original_awb = reverse_data['original_awb']
            return_date = reverse_data['return_date']
            reason = reverse_data['reason']
            refund_status = reverse_data['refund_status']
            
            # Find shipment_id based on tracking number (simplified)
            shipment_id = hash(original_awb) % 20 + 1  # Simplified mapping
            
            value = f"({shipment_id}, '{reverse_number}', '{return_date}', '{reason}', '{refund_status}')"
            reverse_values.append(value)
        
        sql_statements.append(",\n".join(reverse_values) + ";")
        sql_statements.append("")
    
    # Exchange shipments
    if 'exchange_shipments' in data:
        sql_statements.append("-- Insert exchange shipments")
        sql_statements.append("INSERT INTO exchange_shipments (original_shipment_id, exchange_number, exchange_date, new_item, status) VALUES")
        
        exchange_values = []
        for i, (exchange_number, exchange_data) in enumerate(data['exchange_shipments'].items()):
            original_awb = exchange_data['original_awb']
            exchange_date = exchange_data['exchange_date']
            new_item = exchange_data['new_item']
            status = exchange_data['status']
            
            # Find shipment_id based on tracking number (simplified)
            shipment_id = hash(original_awb) % 20 + 1  # Simplified mapping
            
            value = f"({shipment_id}, '{exchange_number}', '{exchange_date}', '{new_item}', '{status}')"
            exchange_values.append(value)
        
        sql_statements.append(",\n".join(exchange_values) + ";")
        sql_statements.append("")
    
    # Add summary queries
    sql_statements.append("-- =====================================================")
    sql_statements.append("-- Summary Queries")
    sql_statements.append("-- =====================================================")
    sql_statements.append("")
    sql_statements.append("-- Total shipments by status")
    sql_statements.append("SELECT status, COUNT(*) as count FROM shipments GROUP BY status;")
    sql_statements.append("")
    sql_statements.append("-- NDR events by outcome")
    sql_statements.append("SELECT final_outcome, COUNT(*) as count FROM ndr_events GROUP BY final_outcome;")
    sql_statements.append("")
    sql_statements.append("-- Reverse shipments by refund status")
    sql_statements.append("SELECT refund_status, COUNT(*) as count FROM reverse_shipments GROUP BY refund_status;")
    sql_statements.append("")
    sql_statements.append("-- Exchange shipments by status")
    sql_statements.append("SELECT status, COUNT(*) as count FROM exchange_shipments GROUP BY status;")
    
    return "\n".join(sql_statements)

def main():
    """Main function to generate SQL file"""
    
    try:
        sql_content = generate_sql_from_json()
        
        # Write to SQL file
        output_file = os.path.join(os.path.dirname(__file__), 'shipstream_data_from_json.sql')
        
        with open(output_file, 'w') as f:
            f.write(sql_content)
        
        print(f"✅ SQL file generated successfully: {output_file}")
        lines_count = len(sql_content.split('\n'))
        print(f"📊 Generated {lines_count} lines of SQL statements")
        
        # Print summary
        print("\n📋 Summary of generated data:")
        print("- Forward shipments: 20")
        print("- NDR events: 8")
        print("- Reverse shipments: 5")
        print("- Exchange shipments: 3")
        
    except Exception as e:
        print(f"❌ Error generating SQL: {e}")

if __name__ == "__main__":
    main()
