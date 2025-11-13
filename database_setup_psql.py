import psycopg2
import psycopg2.extras
import os
from datetime import datetime

# Render sets this environment variable automatically
DATABASE_URL = os.environ.get("DATABASE_URL")

# --- DATABASE SETUP ---

def setup_database_psql():
    """Initializes the PostgreSQL database and creates the necessary tables."""
    conn = None
    if not DATABASE_URL:
        print("CRITICAL: DATABASE_URL not set. Skipping PostgreSQL setup.")
        return

    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # SQL to create the packages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS packages (
                tracking_id VARCHAR(255) PRIMARY KEY,
                recipient VARCHAR(255) NOT NULL,
                status VARCHAR(255) NOT NULL,
                created_at VARCHAR(255) NOT NULL,
                
                weight REAL,
                dimensions VARCHAR(255),
                shipment_type VARCHAR(255),
                location VARCHAR(255)
            );
        """)

        # SQL to create the history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id SERIAL PRIMARY KEY,
                tracking_id VARCHAR(255) NOT NULL,
                timestamp VARCHAR(255) NOT NULL,
                location VARCHAR(255) NOT NULL,
                status_update VARCHAR(255) NOT NULL,
                FOREIGN KEY (tracking_id) REFERENCES packages (tracking_id)
            );
        """)
        
        # Insert Sample Data for Live Environment
        sample_id = 'MVX-DEMOLIVE'
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        cursor.execute("SELECT tracking_id FROM packages WHERE tracking_id = %s", (sample_id,))
        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO packages 
                (tracking_id, recipient, status, created_at, weight, dimensions, shipment_type, location) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (sample_id, 'Render Test Customer', 'Shipment Created', created_at, 1.2, '10cm x 10cm x 10cm', 'Document', 'Live Render Hub'))
            
            cursor.execute("""
                INSERT INTO history (tracking_id, timestamp, location, status_update) 
                VALUES (%s, %s, %s, %s)
            """, (sample_id, created_at, 'Live Render Hub', 'Shipment Created'))
            print(f"Sample package {sample_id} added.")

        conn.commit()
        cursor.close()
        conn.close()
        print("PostgreSQL Database schema initialized successfully.")

    except Exception as e:
        print(f"PostgreSQL Setup Error: {e}")
        raise e