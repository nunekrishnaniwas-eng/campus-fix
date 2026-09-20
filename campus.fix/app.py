from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
import os
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "smart_university_super_secret_key_2026"

# ==========================================
# EMAIL CONFIGURATION (Real OTP Delivery)
# ==========================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "nunekrishnaniwas@gmail.com"
SENDER_PASSWORD = "zjzg aqhk nuzp prwr"

OTP_STORE = {}

ADMIN_EMAIL = "admin@smartuniv.edu"
ADMIN_PASSWORD = "Admin@123"
ADMIN_ENROLLMENT = "ADMIN001"

def send_otp_email(receiver_email, otp_code):
    try:
        msg = MIMEText(f"Hello,\n\nYour Smart University verification OTP is: {otp_code}\nThis code is required to complete your student registration.\n\nSmart University Maintenance Portal")
        msg['Subject'] = "Smart University Student Registration OTP"
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[CONSOLE OTP FALLBACK for {receiver_email}]: {otp_code}")
        return False

def init_db():
    os.makedirs("data", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    os.makedirs("static/charts", exist_ok=True)
    conn = sqlite3.connect("data/campus.db")
    cursor = conn.cursor()
    
    # Complaints Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id TEXT UNIQUE,
            enrollment_no TEXT,
            student_name TEXT,
            department TEXT,
            building TEXT,
            room_no TEXT,
            category TEXT,
            problem TEXT,
            priority TEXT,
            status TEXT,
            date TEXT,
            admin_remarks TEXT DEFAULT 'Pending verification by administration'
        )
    ''')

    # Users Table (Students & Admins)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_no TEXT UNIQUE,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')

    # Upsert Administrator Credentials
    cursor.execute("SELECT id FROM users WHERE email=? OR enrollment_no=?", (ADMIN_EMAIL, ADMIN_ENROLLMENT))
    admin_row = cursor.fetchone()
    if admin_row:
        cursor.execute('''
            UPDATE users 
            SET name='University Admin', email=?, password=?, role='admin'
            WHERE id=?
        ''', (ADMIN_EMAIL, ADMIN_PASSWORD, admin_row[0]))
    else:
        cursor.execute('''
            INSERT INTO users (enrollment_no, name, email, password, role)
            VALUES (?, 'University Admin', ?, ?, 'admin')
        ''', (ADMIN_ENROLLMENT, ADMIN_EMAIL, ADMIN_PASSWORD))

    conn.commit()
    conn.close()

def generate_reports_charts():
    conn = sqlite3.connect("data/campus.db")
    df = pd.read_sql_query("SELECT * FROM complaints", conn)
    conn.close()

    os.makedirs("static/charts", exist_ok=True)
    plt.style.use('dark_background')

    if df.empty:
        for filename in ['status_distribution.png', 'complaints_building.png', 'complaints_month.png']:
            fig, ax = plt.subplots(figsize=(5.5, 4), facecolor='#0B0C10')
            ax.set_facecolor('#0B0C10')
            ax.text(0.5, 0.5, 'No Data Available Yet', horizontalalignment='center', verticalalignment='center', color='#C5C6C7')
            ax.axis('off')
            plt.savefig(f'static/charts/{filename}', bbox_inches='tight', facecolor='#0B0C10')
            plt.close()
        return

    # Chart 1: Status Distribution
    status_counts = df['status'].value_counts()
    fig, ax = plt.subplots(figsize=(5.5, 5.5), facecolor='#1F2833')
    ax.set_facecolor('#1F2833')
    palette = {'Pending': '#fb923c', 'In Progress': '#45A29E', 'Resolved': '#66FCF1'}
    colors = [palette.get(s, '#C5C6C7') for s in status_counts.index]
    ax.pie(status_counts, labels=status_counts.index, autopct='%1.0f%%', startangle=140, colors=colors,
           textprops={'color': '#C5C6C7', 'fontsize': 11, 'weight': 'bold'},
           wedgeprops={'edgecolor': '#1F2833', 'linewidth': 3})
    plt.title('STATUS DISTRIBUTION', color='#66FCF1', fontsize=12, pad=15, weight='bold')
    plt.savefig('static/charts/status_distribution.png', bbox_inches='tight', facecolor='#1F2833')
    plt.close()

    # Chart 2: Complaints by Building
    bldg_counts = df['building'].value_counts()
    fig, ax = plt.subplots(figsize=(6, 4.2), facecolor='#1F2833')
    ax.set_facecolor('#1F2833')
    bar_width = 0.3 if len(bldg_counts) == 1 else 0.45
    bldg_counts.plot(kind='bar', color='#45A29E', ax=ax, width=bar_width, edgecolor='none')
    ax.set_title('COMPLAINTS BY BUILDING', color='#66FCF1', fontsize=11, weight='bold', pad=12)
    ax.tick_params(colors='#C5C6C7', labelsize=10)
    plt.xticks(rotation=0, ha='center')
    ax.set_xlabel('')
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.grid(axis='y', color='#45A29E', linestyle='--', alpha=0.2)
    for spine in ax.spines.values():
        spine.set_color('#45A29E')
        spine.set_alpha(0.3)
    plt.savefig('static/charts/complaints_building.png', bbox_inches='tight', facecolor='#1F2833')
    plt.close()

    # Chart 3: Complaints Reported per Month
    df['month'] = df['date'].apply(lambda x: str(x)[:7] if pd.notnull(x) else datetime.today().strftime('%Y-%m'))
    month_counts = df['month'].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(6, 4.2), facecolor='#1F2833')
    ax.set_facecolor('#1F2833')
    ax.plot(month_counts.index, month_counts.values, color='#66FCF1', marker='o', linewidth=2.5, markersize=7)
    ax.fill_between(month_counts.index, month_counts.values, color='#66FCF1', alpha=0.15)
    ax.set_title('COMPLAINTS REPORTED PER MONTH', color='#66FCF1', fontsize=11, weight='bold', pad=12)
    ax.tick_params(colors='#C5C6C7', labelsize=10)
    plt.xticks(rotation=0, ha='center')
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.grid(color='#45A29E', linestyle='--', alpha=0.2)
    for spine in ax.spines.values():
        spine.set_color('#45A29E')
        spine.set_alpha(0.3)
    plt.savefig('static/charts/complaints_month.png', bbox_inches='tight', facecolor='#1F2833')
    plt.close()

# ----------------- ROUTES ----------------- #

@app.route('/')
def dashboard():
    return render_template('index.html', active_tab='hero')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        enrollment = request.form.get('enrollment_no', '').strip().upper()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        conn = sqlite3.connect("data/campus.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE enrollment_no=? OR email=?", (enrollment, email))
        existing = cursor.fetchone()
        conn.close()

        if existing:
            flash("Enrollment number or email is already registered. Please log in.", "danger")
            return redirect(url_for('signup'))

        otp = str(random.randint(100000, 999999))
        OTP_STORE[email] = {
            'otp': otp,
            'data': {
                'enrollment_no': enrollment,
                'name': name,
                'email': email,
                'password': password,
                'role': 'student'
            }
        }
        send_otp_email(email, otp)
        flash("Verification OTP has been sent to your email address!", "info")
        return redirect(url_for('verify_otp', email=email))

    return render_template('index.html', active_tab='signup')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.args.get('email', '')
    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        record = OTP_STORE.get(email)

        if record and record['otp'] == entered_otp:
            user_data = record['data']
            conn = sqlite3.connect("data/campus.db")
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (enrollment_no, name, email, password, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_data['enrollment_no'], user_data['name'], user_data['email'], user_data['password'], user_data['role']))
            conn.commit()
            conn.close()
            OTP_STORE.pop(email, None)
            flash("Signup successful! You can now log in.", "success")
            return redirect(url_for('login'))
        else:
            flash("Invalid OTP code. Please enter the correct 6-digit code.", "danger")

    return render_template('index.html', active_tab='verify_otp', email=email)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password')

        conn = sqlite3.connect("data/campus.db")
        cursor = conn.cursor()
        cursor.execute("SELECT enrollment_no, name, email, role FROM users WHERE (email=? OR enrollment_no=?) AND password=?", (identifier, identifier, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = {
                'enrollment_no': user[0],
                'name': user[1],
                'email': user[2],
                'role': user[3]
            }
            flash(f"Welcome, {user[1]}!", "success")
            if user[3] == 'admin':
                return redirect(url_for('admin_verify'))
            return redirect(url_for('my_complaints'))
        else:
            flash("Invalid credentials. Please verify your details.", "danger")

    return render_template('index.html', active_tab='login')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' not in session:
        flash("Please log in to submit a complaint.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('student_name')
        dept = request.form.get('department')
        building = request.form.get('building')
        room = request.form.get('room_no')
        category = request.form.get('category')
        priority = request.form.get('priority')
        problem = request.form.get('problem')
        enrollment_no = session['user']['enrollment_no']

        conn = sqlite3.connect("data/campus.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM complaints")
        count = cursor.fetchone()[0]
        complaint_id = f"CMP{str(count + 1).zfill(3)}"
        date_str = datetime.today().strftime('%Y-%m-%d')

        cursor.execute('''
            INSERT INTO complaints (complaint_id, enrollment_no, student_name, department, building, room_no, category, problem, priority, status, date, admin_remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, 'Pending admin verification')
        ''', (complaint_id, enrollment_no, name, dept, building, room, category, problem, priority, date_str))
        conn.commit()
        conn.close()
        flash(f"Complaint registered successfully! Ticket ID: {complaint_id}", "success")
        return redirect(url_for('my_complaints'))

    return render_template('index.html', active_tab='register')

# NEW: Student My Complaints Status Route
@app.route('/my-complaints')
def my_complaints():
    if 'user' not in session:
        flash("Please log in to check your complaints status.", "danger")
        return redirect(url_for('login'))

    enrollment_no = session['user']['enrollment_no']
    conn = sqlite3.connect("data/campus.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT complaint_id, student_name, building, room_no, category, status, date, enrollment_no, admin_remarks, problem 
        FROM complaints 
        WHERE enrollment_no = ?
        ORDER BY id DESC
    ''', (enrollment_no,))
    user_tickets = cursor.fetchall()
    conn.close()

    return render_template('index.html', active_tab='my_complaints', user_tickets=user_tickets)

# Admin All Tickets Route (Strictly Protected)
@app.route('/tickets')
def tickets():
    if 'user' not in session or session['user'].get('role') != 'admin':
        flash("Access Denied: Only College Admin can view all campus tickets.", "danger")
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    conn = sqlite3.connect("data/campus.db")
    cursor = conn.cursor()
    if search:
        cursor.execute('''
            SELECT complaint_id, student_name, building, room_no, category, status, date, enrollment_no, admin_remarks 
            FROM complaints 
            WHERE student_name LIKE ? OR complaint_id LIKE ? OR enrollment_no LIKE ?
            ORDER BY id DESC
        ''', (f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        cursor.execute('''
            SELECT complaint_id, student_name, building, room_no, category, status, date, enrollment_no, admin_remarks 
            FROM complaints 
            ORDER BY id DESC
        ''')
    all_tickets = cursor.fetchall()
    conn.close()
    return render_template('index.html', active_tab='tickets', all_tickets=all_tickets, search=search)

@app.route('/admin/verify', methods=['GET', 'POST'])
def admin_verify():
    if 'user' not in session or session['user'].get('role') != 'admin':
        flash("Admin credentials required to view this panel.", "danger")
        return redirect(url_for('login'))

    conn = sqlite3.connect("data/campus.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        c_id = request.form.get('complaint_id')
        new_status = request.form.get('status')
        admin_note = request.form.get('admin_remarks')
        cursor.execute("UPDATE complaints SET status = ?, admin_remarks = ? WHERE complaint_id = ?", (new_status, admin_note, c_id))
        conn.commit()
        flash(f"Ticket {c_id} updated to '{new_status}'.", "success")

    filter_status = request.args.get('filter_status', 'All')
    if filter_status and filter_status != 'All':
        cursor.execute("SELECT complaint_id, enrollment_no, student_name, department, building, room_no, category, problem, priority, status, date, admin_remarks FROM complaints WHERE status=? ORDER BY id DESC", (filter_status,))
    else:
        cursor.execute("SELECT complaint_id, enrollment_no, student_name, department, building, room_no, category, problem, priority, status, date, admin_remarks FROM complaints ORDER BY id DESC")
    complaints_list = cursor.fetchall()
    conn.close()
    return render_template('index.html', active_tab='admin_verify', complaints_list=complaints_list, filter_status=filter_status)

@app.route('/reports')
def reports():
    if 'user' not in session or session['user'].get('role') != 'admin':
        flash("Access Denied: Only administrators can view university analytics and reports.", "danger")
        return redirect(url_for('login'))

    conn = sqlite3.connect("data/campus.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'")
    in_progress = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'")
    resolved = cursor.fetchone()[0]

    df = pd.read_sql_query("SELECT * FROM complaints", conn)
    top_cat = df['category'].mode()[0] if not df.empty and not df['category'].empty else 'N/A'
    top_bldg = df['building'].mode()[0] if not df.empty and not df['building'].empty else 'N/A'
    
    cat_counts = df['category'].value_counts().to_dict() if not df.empty else {}
    max_cat_count = max(cat_counts.values()) if cat_counts else 1
    
    all_categories = ["Electrical", "Furniture", "Plumbing", "IT", "Internet", "Cleaning", "AC/Cooling", "Other"]
    cat_percentages = {cat: int((cat_counts.get(cat, 0) / max_cat_count) * 100) for cat in all_categories}

    conn.close()
    generate_reports_charts()

    return render_template('index.html', active_tab='reports', total=total, pending=pending, in_progress=in_progress, resolved=resolved, top_cat=top_cat, top_bldg=top_bldg, cat_percentages=cat_percentages)

@app.route('/export')
def export_csv():
    if 'user' not in session or session['user'].get('role') != 'admin':
        flash("Admin credentials required to export reports.", "danger")
        return redirect(url_for('login'))
        
    conn = sqlite3.connect("data/campus.db")
    df = pd.read_sql_query("SELECT * FROM complaints", conn)
    conn.close()
    filepath = "reports/complaints_report.csv"
    df.to_csv(filepath, index=False)
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)