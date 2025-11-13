import os
import uuid
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from flask_cors import CORS
from datetime import datetime
from functools import wraps

# --- RENDER/POSTGRESQL SPECIFIC IMPORTS ---
# Note: psycopg2 is the PostgreSQL driver required for Render
try:
    import psycopg2
    # Determine the database connection string from environment variables (used by Render)
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/movexadb")
    USE_POSTGRES = True
except ImportError:
    # Fallback to SQLite for local development testing if psycopg2 is not installed
    import sqlite3
    DATABASE_FILE = 'tracking.db'
    USE_POSTGRES = False
# --- END RENDER/POSTGRESQL SPECIFIC IMPORTS ---
app = Flask(__name__)
CORS(app) 
# --- START OF CODE TO ADD ---
# This code is clean and should resolve all known AssertionErrors and SyntaxErrors.

@app.route('/')
def index():
    # Renders the styled homepage file
    return render_template('index.html')

@app.route('/track', methods=['POST'])
def track_shipment():
    # This route handles the submission of the tracking ID from the homepage form.
    from flask import request # Ensures 'request' is accessible if not imported globally
    
    # 1. Get the tracking ID from the submitted form data
    tracking_id = request.form.get('tracking_id')

    # 2. *** YOUR DATABASE/TRACKING CODE GOES HERE ***
    # For now, it returns dummy data to ensure the page loads:
    
    # 3. Render the results page (Tracking Dashboard)
    return render_template('results.html', tracking_id=tracking_id, status="In Transit", location="New York, USA")

@app.route('/ship-now')
def ship_now():
    return render_template('ship_now.html')

@app.route('/get-quote')
def get_quote():
    return render_template('quote.html')

@app.route('/business')
def business_page():
    return render_template('business.html')

@app.route('/contact')
def contact_page():
    return render_template('contact.html')

@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/client-portal')
def client_portal_page():
    return render_template('client_portal.html')

# --- SECURITY CONFIGURATION (Basic Authentication) ---
# NOTE: Render will use environment variables for security. 
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'movexa_admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'calaman081') 

def check_auth(username, password):
    """This function is called to check if a username / password combination is valid."""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    """Sends a 401 response that enables basic auth."""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Admin Login"'}
    )

def requires_auth(f):
    """Decorator to protect routes with basic HTTP authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated
# --- END SECURITY CONFIGURATION ---


# --- DATABASE CONNECTION HANDLERS ---

def get_db_connection():
    """Establishes a connection based on the runtime environment (PostgreSQL for Render, SQLite for local)."""
    if USE_POSTGRES:
        # Use psycopg2 for PostgreSQL
        conn = psycopg2.connect(DATABASE_URL)
    else:
        # Use sqlite3 for local development
        conn = sqlite3.connect(DATABASE_FILE)
    
    # Set row factory for dictionary-like access
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        conn.row_factory = None # psycopg2.extras.RealDictCursor handles this
    else:
        conn.row_factory = sqlite3.Row
    
    return conn

def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """Generic function to handle database operations for both DB types."""
    conn = None
    result = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if params is None:
            params = []
            
        # SQLite uses '?' placeholders, PostgreSQL uses '%s'
        if not USE_POSTGRES:
             # SQLite: ensure placeholders are compatible
             query = query.replace('%s', '?') 

        cursor.execute(query, params)
        
        if commit:
            conn.commit()
        
        if fetch_one:
            result = cursor.fetchone()
            if not USE_POSTGRES and result: result = dict(result) # Convert SQLite row object
        elif fetch_all:
            result = cursor.fetchall()
            if not USE_POSTGRES and result: result = [dict(row) for row in result] # Convert SQLite row objects

    except Exception as e:
        print(f"Database Query Error: {e}")
        if conn and not commit:
             conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()
    return result

# --- DATABASE CRUD LOGIC (Now using the execute_query helper) ---

def db_get_package_details(tracking_id):
    """Fetches package details (including new parcel data) by tracking ID."""
    query = "SELECT tracking_id, recipient, status, created_at, weight, dimensions, shipment_type FROM packages WHERE tracking_id = %s"
    package = execute_query(query, (tracking_id,), fetch_one=True)
    
    if package:
        return package
    else:
        # Placeholder for Not Found status
        return {'tracking_id': tracking_id, 'status': 'Not Found', 'recipient': 'N/A', 'created_at': 'N/A', 
                'weight': None, 'dimensions': None, 'shipment_type': None}

def db_get_tracking_history(tracking_id):
    """Fetches all history updates for a tracking ID."""
    query = "SELECT timestamp, location, status_update FROM history WHERE tracking_id = %s ORDER BY timestamp DESC"
    return execute_query(query, (tracking_id,), fetch_all=True)

def db_add_new_package(tracking_id, recipient, status, created_at, weight, dimensions, shipment_type):
    """Inserts a new package with all parcel details."""
    query_package = """
        INSERT INTO packages 
        (tracking_id, recipient, status, created_at, weight, dimensions, shipment_type) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    params_package = (tracking_id, recipient, status, created_at, weight, dimensions, shipment_type)
    execute_query(query_package, params_package, commit=True)
    
    query_history = "INSERT INTO history (tracking_id, timestamp, location, status_update) VALUES (%s, %s, %s, %s)"
    params_history = (tracking_id, created_at, 'Shipment created online', status)
    execute_query(query_history, params_history, commit=True)
    

def db_update_package_status(tracking_id, status, location, timestamp):
    """Updates package status and adds a new history entry."""
    
    query_update = "UPDATE packages SET status = %s WHERE tracking_id = %s"
    execute_query(query_update, (status, tracking_id), commit=True)
    
    query_history = "INSERT INTO history (tracking_id, timestamp, location, status_update) VALUES (%s, %s, %s, %s)"
    execute_query(query_history, (tracking_id, timestamp, location, status), commit=True)


# --- UTILITY ---
def generate_tracking_id():
    """Generates a unique MOVEXA tracking ID."""
    unique_part = uuid.uuid4().hex[:8].upper()
    return f"MVX-{unique_part}"


# --- Shipping Quote Calculation Logic (API) ---

# (Quote logic remains the same, using simple Python math)

def calculate_quote(origin, destination, weight):
    if weight is None or weight <= 0:
        raise ValueError("Weight must be a valid number greater than zero.")

    base_fee = 20.00
    cost_per_kg = 5.00
    
    origin_zone = origin.split(',')[-1].strip().lower()
    dest_zone = destination.split(',')[-1].strip().lower()
    
    is_international = origin_zone != dest_zone
    shipping_cost = base_fee + (weight * cost_per_kg)
    
    if is_international:
        shipping_cost *= 1.5
        currency = "USD"
    else:
        currency = "USD"
        
    return round(shipping_cost, 2), currency


@app.route('/api/quote', methods=['POST'])
def api_quote():
    data = request.json
    origin = data.get('origin')
    destination = data.get('destination')
    
    try:
        weight = float(data.get('weight', 0))
        quote, currency = calculate_quote(origin, destination, weight)
        return jsonify({'success': True, 'quote': quote, 'currency': currency})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Quote calculation error: {e}")
        return jsonify({'success': False, 'error': 'Server processing error.'}), 500


# --- MOVEXA Customer-Facing Routes (No Auth Required) ---


@app.route('/results/<tracking_id>')
def results(tracking_id):
    package = db_get_package_details(tracking_id)
    history = db_get_tracking_history(tracking_id)
    
    # Sorting logic for history
    if history:
        try:
            history.sort(key=lambda x: datetime.strptime(x['timestamp'].split('.')[0], '%Y-%m-%d %H:%M:%S'), reverse=True)
        except ValueError:
            history.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('results.html', package=package, history=history)

@app.route('/quote')
def quote_page():
    return render_template('quote.html')

@app.route('/ship_now')
def ship_now_page():
    return render_template('ship_now.html')


# --- MOVEXA Admin Routes (AUTH REQUIRED) ---

@app.route('/admin')
@requires_auth 
def admin_home():
    return render_template('admin_home.html')

@app.route('/admin/new', methods=['GET', 'POST'])
@requires_auth 
def admin_new():
    if request.method == 'POST':
        tracking_id = request.form['tracking_id'].upper()
        recipient = request.form['recipient']
        
        weight = request.form.get('weight')
        dimensions = request.form.get('dimensions')
        shipment_type = request.form.get('shipment_type')
        
        try:
            weight = float(weight) if weight else None
        except ValueError:
            weight = None
            
        status = 'Shipment Created'
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        try:
            db_add_new_package(tracking_id, recipient, status, created_at, weight, dimensions, shipment_type)
            return redirect(url_for('admin_update_status', tracking_id=tracking_id))
        except Exception as e:
            # Handle integrity error (duplicate ID) or connection errors
            error_message = f"Error creating package: {e}"
            placeholder_id = 'MVX-' + datetime.now().strftime('%Y%m%d%H%M%S')[-8:]
            return render_template('admin_new.html', error=error_message, placeholder_id=placeholder_id)
    
    placeholder_id = 'MVX-' + datetime.now().strftime('%Y%m%d%H%M%S')[-8:]
    
    return render_template('admin_new.html', placeholder_id=placeholder_id)

@app.route('/admin/update/<tracking_id>', methods=['GET', 'POST'])
@requires_auth 
def admin_update_status(tracking_id):
    package = db_get_package_details(tracking_id)
    
    if package['status'] == 'Not Found':
        return render_template('admin_update_status.html', error=f"Package ID {tracking_id} not found."), 404
        
    if request.method == 'POST':
        new_status = request.form['status']
        location = request.form['location']
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        db_update_package_status(tracking_id, new_status, location, timestamp)
        return redirect(url_for('results', tracking_id=tracking_id))
        
    return render_template('admin_update_status.html', package=package)

if __name__ == '__main__':
    # Local development run configuration
    app.run(debug=True, host='0.0.0.0', port=5000)