from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import bcrypt
import jwt
import datetime
import os
import re
import pytz
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

CAT = pytz.timezone('Africa/Gaborone')

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

SECRET_KEY = os.environ.get("JWT_SECRET_KEY")  # used to sign JWTs
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set. Copy .env.example to .env and fill it in.")

ISSUER = os.environ.get("JWT_ISSUER", "flask-auth")

@app.template_filter('timestamp')
def timestamp_filter(value):
    CAT = pytz.timezone('Africa/Gaborone')
    utc_time = datetime.datetime.utcfromtimestamp(value)
    cat_time = pytz.utc.localize(utc_time).astimezone(CAT)
    return cat_time.strftime('%b %d, %Y, %I:%M:%S %p') + ' CAT'

# Input Sanitization
def sanitize_input(value):
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if len(value) > 50:
        return None
    if re.search(r"[<>\"'%;()&+]", value):
        return None
    return value

def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*]", password):
        return False, "Password must contain at least one special character (!@#$%^&*)"
    return True, "Password is strong"

# Database setup 
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    ''')
    conn.commit()
    conn.close()

# Routes 
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = sanitize_input(request.form.get('first_name'))
        last_name = sanitize_input(request.form.get('last_name'))
        username = sanitize_input(request.form.get('username'))
        password = request.form.get('password')
        role = request.form.get('role')

        # Check for invalid inputs
        if not all([first_name, last_name, username, password, role]):
            return render_template('register.html', error="Invalid input detected. Please avoid special characters")

        # Validate role
        if role not in ['staff', 'manager']:
            return render_template('register.html', error="Invalid role selected")

        # Validate password strength
        is_valid, message = validate_password(password)
        if not is_valid:
            return render_template('register.html', error=message)

        # Hash and salt password
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute('INSERT INTO users (first_name, last_name, username, password, role) VALUES (?, ?, ?, ?, ?)',
                      (first_name, last_name, username, hashed, role))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Username already exists")

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username'))
        password = request.form.get('password')

        # Check for invalid inputs
        if not username or not password:
            return render_template('login.html', error="Invalid input detected. Please avoid special characters")

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[4]):
            token = jwt.encode({
                'username': user[3],
                'first_name': user[1],
                'last_name': user[2],
                'role': user[5],
                'iss': ISSUER,
                'iat': datetime.datetime.now(CAT),
                'exp': datetime.datetime.now(CAT) + datetime.timedelta(hours=1)
            }, SECRET_KEY, algorithm='HS256')

            session['token'] = token
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    token = session.get('token')
    if not token:
        return redirect(url_for('login'))

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=['HS256'],
                             options={"verify_exp": True})
        return render_template('dashboard.html', token=token, decoded=decoded)
    except jwt.ExpiredSignatureError:
        return render_template('dashboard.html', error="Token has expired")
    except jwt.InvalidTokenError:
        return render_template('dashboard.html', error="Invalid token")

@app.route('/validate', methods=['GET', 'POST'])
def validate():
    result = None
    if request.method == 'POST':
        token = request.form.get('token', '').strip()

        if not token:
            return render_template('validate.html', error="Please enter a token")

        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=['HS256'],
                                 options={"verify_exp": True})
            result = {
                'status': 'valid',
                'username': decoded.get('username'),
                'first_name': decoded.get('first_name'),
                'last_name': decoded.get('last_name'),
                'role': decoded.get('role'),
                'issuer': decoded.get('iss'),
                'issued_at': pytz.utc.localize(datetime.datetime.utcfromtimestamp(decoded.get('iat'))).astimezone(CAT).strftime('%b %d, %Y, %I:%M:%S %p') + ' CAT',
                'expires_at': pytz.utc.localize(datetime.datetime.utcfromtimestamp(decoded.get('exp'))).astimezone(CAT).strftime('%b %d, %Y, %I:%M:%S %p') + ' CAT'
            }
        except jwt.ExpiredSignatureError:
            result = {
                'status': 'expired',
                'message': 'This token has expired and is no longer valid'
            }
        except jwt.InvalidSignatureError:
            result = {
                'status': 'invalid',
                'message': 'This token has been tampered with and is not trustworthy'
            }
        except jwt.DecodeError:
            result = {
                'status': 'invalid',
                'message': 'This is not a valid token format'
            }
        except Exception:
            result = {
                'status': 'invalid',
                'message': 'Token could not be validated'
            }

    return render_template('validate.html', result=result)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
