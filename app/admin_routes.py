from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3

admin_bp = Blueprint('admin', __name__)

DATABASE = "hospital_management.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --------------------------
# Admin Login / Logout
# --------------------------
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Simple hardcoded admin login (you can connect to staff table if you want)
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@admin_bp.route('/logout')
def logout():
    session.pop('admin', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('admin.login'))  # <- added blueprint prefix


# --------------------------
# Admin Dashboard
# --------------------------
@admin_bp.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin.login'))  # <- added blueprint prefix

    conn = get_db_connection()
    stats = {
        'patients': conn.execute('SELECT COUNT(*) FROM patients').fetchone()[0],
        'doctors': conn.execute("SELECT COUNT(*) FROM staff WHERE role='doctor'").fetchone()[0],
        'rooms': conn.execute('SELECT COUNT(*) FROM rooms').fetchone()[0],
        'bills': conn.execute('SELECT COUNT(*) FROM bills').fetchone()[0],
    }
    conn.close()
    return render_template('dashboard.html', stats=stats)  # <- corrected template name


# --------------------------
# Patients Management
# --------------------------
@admin_bp.route('/patients')
def patients():
    if 'admin' not in session:
        return redirect(url_for('admin.login'))  # <- added blueprint prefix
    conn = get_db_connection()
    patients = conn.execute('SELECT * FROM patients').fetchall()
    conn.close()
    return render_template('patient_book.html', patients=patients)


@admin_bp.route('/patients/add', methods=['GET', 'POST'])
def add_patient():
    if 'admin' not in session:
        return redirect(url_for('admin.login'))  # <- added blueprint prefix
    if request.method == 'POST':
        first = request.form['first_name']
        last = request.form['last_name']
        phone = request.form['phone']
        address = request.form['address']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO patients (first_name, last_name, phone, address) VALUES (?, ?, ?, ?)',
            (first, last, phone, address)
        )
        conn.commit()
        conn.close()
        flash('Patient added successfully!', 'success')
        return redirect(url_for('admin.patients'))  # <- added blueprint prefix

    return render_template('add_patients.html')


@admin_bp.route('/patients/delete/<int:pid>')
def delete_patient(pid):
    if 'admin' not in session:
        return redirect(url_for('admin.login'))  # <- added blueprint prefix
    conn = get_db_connection()
    conn.execute('DELETE FROM patients WHERE id = ?', (pid,))
    conn.commit()
    conn.close()
    flash('Patient deleted successfully!', 'info')
    return redirect(url_for('admin.patients'))  # <- added blueprint prefix


# --------------------------
# View Bills
# --------------------------
@admin_bp.route('/bills')
def bills():
    if 'admin' not in session:
        return redirect(url_for('admin.login'))  # <- added blueprint prefix
    conn = get_db_connection()
    bills = conn.execute('''
        SELECT b.id, p.first_name || " " || p.last_name AS patient_name,
               b.total_amount, b.paid, b.created_at
        FROM bills b
        JOIN patients p ON p.id = b.patient_id
        ORDER BY b.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('bills.html', bills=bills)


# --------------------------
# Doctors Management (Admin)
# --------------------------
@admin_bp.route('/doctors')
def doctors():
    if 'admin' not in session:
        return redirect(url_for('admin.login'))
    conn = get_db_connection()
    doctors = conn.execute("SELECT * FROM staff WHERE role='doctor'").fetchall()
    conn.close()
    return render_template('doctors.html', doctors=doctors)


@admin_bp.route('/doctors/add', methods=['GET', 'POST'])
def add_doctor():
    if 'admin' not in session:
        return redirect(url_for('admin.login'))
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        specialization = request.form['specialization']
        phone = request.form['phone']

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO staff (first_name, last_name, specialization, phone, role) VALUES (?, ?, ?, ?, 'doctor')",
            (first_name, last_name, specialization, phone)
        )
        conn.commit()
        conn.close()
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('admin.doctors'))
    
    return render_template('add_doctor.html')


@admin_bp.route('/doctors/delete/<int:did>')
def delete_doctor(did):
    if 'admin' not in session:
        return redirect(url_for('admin.login'))
    conn = get_db_connection()
    conn.execute("DELETE FROM staff WHERE id = ? AND role='doctor'", (did,))
    conn.commit()
    conn.close()
    flash('Doctor deleted successfully!', 'info')
    return redirect(url_for('admin.doctors'))

# --------------------------
# Update Patient Logs
# --------------------------
@admin_bp.route('/patients/update/<int:pid>', methods=['GET', 'POST'])
def update_patient(pid):
    if 'admin' not in session:
        return redirect(url_for('admin.login'))

    conn = get_db_connection()
    patient = conn.execute('SELECT * FROM patients WHERE id = ?', (pid,)).fetchone()

    if request.method == 'POST':
        first = request.form['first_name']
        last = request.form['last_name']
        phone = request.form['phone']
        address = request.form['address']
        logs = request.form['logs']  # new field for patient logs

        conn.execute(
            'UPDATE patients SET first_name=?, last_name=?, phone=?, address=?, logs=? WHERE id=?',
            (first, last, phone, address, logs, pid)
        )
        conn.commit()
        conn.close()
        flash('Patient updated successfully!', 'success')
        return redirect(url_for('admin.patients'))

    conn.close()
    return render_template('update_patient.html', patient=patient)
