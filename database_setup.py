import sqlite3
from datetime import datetime

DATABASE_NAME = 'tracking.db'

def setup_database():
    """Sets up the SQLite database and creates the necessary tables."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # 1. Create the packages table (UPDATED SCHEMA)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS packages (
                tracking_id TEXT PRIMARY KEY,
                recipient TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                
                -- NEW COLUMNS FOR PARCEL DETAILS
                weight REAL,
                dimensions TEXT,
                shipment_type TEXT
            )
        """)
        print("Table 'packages' created successfully.")

        # 2. Create the history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                location TEXT NOT NULL,
                status_update TEXT NOT NULL,
                FOREIGN KEY (tracking_id) REFERENCES packages (tracking_id)
            )
        """)
        print("Table 'history' created successfully.")

        # 3. Insert a sample package for testing (UPDATED with new columns)
        sample_id = 'MVX-DEMO2025'
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        cursor.execute("SELECT tracking_id FROM packages WHERE tracking_id = ?", (sample_id,))
        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO packages 
                (tracking_id, recipient, status, created_at, weight, dimensions, shipment_type) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sample_id, 'Movexa Demo Customer', 'Delivered', created_at, 5.0, '20cm x 20cm x 10cm', 'Small Parcel'))
            print(f"Sample package {sample_id} added for testing.")

            # Insert sample history
            cursor.execute("""
                INSERT INTO history (tracking_id, timestamp, location, status_update) 
                VALUES (?, ?, ?, ?)
            """, (sample_id, created_at, 'Lagos, NG', 'Shipment Created'))
            cursor.execute("""
                INSERT INTO history (tracking_id, timestamp, location, status_update) 
                VALUES (?, ?, ?, ?)
            """, (sample_id, created_at, 'New York, USA', 'Shipment in Transit'))
            cursor.execute("""
                INSERT INTO history (tracking_id, timestamp, location, status_update) 
                VALUES (?, ?, ?, ?)
            """, (sample_id, created_at, 'Port Harcourt, NG', 'Delivered'))
            print("Sample history added.")
        
        conn.commit()
        conn.close()
        print("Database setup complete.")

    except sqlite3.Error as e:
        print(f"An error occurred during database setup: {e}")

if __name__ == '__main__':
    import os
    if os.path.exists(DATABASE_NAME):
        choice = input(f"Warning: {DATABASE_NAME} already exists. Do you want to delete and recreate the database? (y/n): ")
        if choice.lower() == 'y':
            os.remove(DATABASE_NAME)
            print(f"{DATABASE_NAME} deleted.")
            setup_database()
        else:
            print("Database setup skipped.")
    else:
        setup_database()