import os
import uuid
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from flask_cors import CORS
from datetime import datetime
from functools import wraps

# --- RENDER/POSTGRESQL SPECIFIC IMPORTS ---
try:
    import psycopg2
    import psycopg2.extras
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/movexadb")
    USE_POSTGRES = True
except ImportError:
    import sqlite3
    DATABASE_FILE = 'tracking.db'
    USE_POSTGRES = False
# --- END RENDER/POSTGRESQL SPECIFIC IMPORTS ---

app = Flask(__name__)
CORS(app) 

# --- SECURITY CONFIGURATION (Basic Authentication) ---
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
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """Generic function to handle database operations for both DB types."""
    conn = None
    result = None
    try:
        conn = get_db_connection()
        
        # Determine cursor type and query placeholders
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
             # SQLite uses '?' placeholders
             query = query.replace('%s', '?') 
             cursor = conn.cursor()

        if params is None:
            params = []
            
        cursor.execute(query, params)
        
        if commit:
            conn.commit()
        
        if fetch_one:
            result = cursor.fetchone()
            if not USE_POSTGRES and result: result = dict(result)
        elif fetch_all:
            result = cursor.fetchall()
            if not USE_POSTGRES and result: result = [dict(row) for row in result]

    except Exception as e:
        print(f"Database Query Error: {e}")
        if conn and not commit:
             conn.rollback()
        # In a real app, you might want to log this and raise a user-friendly error
        # For deployment debugging, re-raise the exception:
        raise e
    finally:
        if conn:
            conn.close()
    return result

# --- DATABASE CRUD LOGIC (Placeholder implementation) ---

# NOTE: The actual database logic functions (db_get_package_details, db_add_new_package, etc.) 
# require a connected database and are omitted here for brevity and focus on syntax/routing,
# but they exist in the full working application and rely on execute_query.

def db_get_package_details(tracking_id):
    # This is a placeholder for the full logic
    return {'tracking_id': tracking_id, 'status': 'Debug Mode - Ready', 'recipient': 'N/A', 'created_at': 'N/A', 
            'weight': None, 'dimensions': None, 'shipment_type': None}

def db_get_tracking_history(tracking_id):
    # Placeholder
    return [{'timestamp': '2025-11-13 10:00:00.0', 'location': 'Placeholder City', 'status_update': 'Created'}]

# --- UTILITY ---
def generate_tracking_id():
    unique_part = uuid.uuid4().hex[:8].upper()
    return f"MVX-{unique_part}"


# --- Shipping Quote Calculation Logic (API) ---

def calculate_quote(origin, destination, weight):
    # ... (Quote calculation logic) ...
    if weight is None or weight <= 0:
        raise ValueError("Weight must be a valid number greater than zero.")
    base_fee = 20.00
    cost_per_kg = 5.00
    shipping_cost = base_fee + (weight * cost_per_kg)
    return round(shipping_cost, 2), "USD"


@app.route('/api/quote', methods=['POST'])
def api_quote():
    # ... (API logic) ...
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
        # app.logger.error(f"Quote calculation error: {e}")
        return jsonify({'success': False, 'error': 'Server processing error.'}), 500


# --- MOVEXA Customer-Facing Routes (No Auth Required) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/track', methods=['POST'])
def track_shipment():
    # 1. Get the tracking ID from the submitted form data
    tracking_id = request.form.get('tracking_id')
    # 2. For now, return dummy data to ensure the page loads:
    
    # NOTE: Calling the results route directly with the ID is cleaner
    return redirect(url_for('results', tracking_id=tracking_id))


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

@app.route('/get-quote')
def get_quote():
    # NOTE: Function name is 'get_quote' to match HTML links
    return render_template('quote.html')

@app.route('/ship-now')
def ship_now():
    return render_template('ship_now.html')

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
def client_portal():
    # NOTE: Function name is 'client_portal' to match simplified HTML links
    return render_template('client_portal.html')


# --- MOVEXA Admin Routes (AUTH REQUIRED) ---

@app.route('/admin')
@requires_auth 
def admin_home():
    return render_template('admin_home.html')

# (Admin routes remain the same structure)

if __name__ == '__main__':
    # Local development run configuration
    app.run(debug=True, host='0.0.0.0', port=5000)