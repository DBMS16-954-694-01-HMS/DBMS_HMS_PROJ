from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

patient_bp = Blueprint('patient', __name__)

# DB path relative to this module
DATABASE = os.path.join(os.path.dirname(__file__), 'hospital_management.db')

def get_db():
    # increase timeout and allow connections from different threads
    conn = sqlite3.connect(DATABASE, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA foreign_keys = ON;')
    except Exception:
        pass
    return conn


@patient_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Patient logs in using only their patient ID
    if request.method == 'POST':
        pid = request.form.get('patient_id')
        if not pid:
            flash('Please enter your patient ID', 'danger')
            return render_template('patient_login.html')

        conn = get_db()
        patient = conn.execute('SELECT id, first_name, last_name FROM patients WHERE id = ?', (pid,)).fetchone()
        conn.close()
        if patient:
            session['patient_id'] = patient['id']
            session['patient_name'] = f"{patient['first_name']} {patient['last_name']}"
            return redirect(url_for('patient.home'))
        else:
            flash('Patient ID not found', 'danger')

    return render_template('patient_login.html')


@patient_bp.route('/logout')
def logout():
    session.pop('patient_id', None)
    session.pop('patient_name', None)
    return redirect(url_for('patient.login'))


@patient_bp.route('/home')
def home():
    if 'patient_id' not in session:
        return redirect(url_for('patient.login'))
    return render_template('patient_home.html', name=session.get('patient_name'))


@patient_bp.route('/book', methods=['GET', 'POST'])
def book_appointment():
    if 'patient_id' not in session:
        return redirect(url_for('patient.login'))

    conn = get_db()
    if request.method == 'POST':
        # Patients should not select a doctor when booking; admin will assign later.
        doctor_id = None
        date = request.form.get('date')
        time = request.form.get('time')
        notes = request.form.get('reason') or request.form.get('notes')

        # combine date and time if provided
        appt_dt = date
        if time:
            appt_dt = f"{date} {time}"

        conn.execute('INSERT INTO appointments (patient_id, doctor_id, appointment_datetime, notes) VALUES (?, ?, ?, ?)', (session['patient_id'], doctor_id, appt_dt, notes))
        conn.commit()
        conn.close()
        flash('Appointment booked successfully and is pending admin approval', 'success')
        return redirect(url_for('patient.view_appointments'))

    # GET: show booking form (no doctor selection)
    conn.close()
    return render_template('patient_book.html')


@patient_bp.route('/appointments')
def view_appointments():
    if 'patient_id' not in session:
        return redirect(url_for('patient.login'))
    conn = get_db()
    rows = conn.execute('SELECT a.*, d.f_name || " " || d.l_name AS doctor_name FROM appointments a LEFT JOIN doctors d ON d.doctor_id = a.doctor_id WHERE a.patient_id = ? ORDER BY a.appointment_datetime DESC', (session['patient_id'],)).fetchall()
    conn.close()
    return render_template('patient_appointments.html', rows=rows)


@patient_bp.route('/appointments/cancel/<int:aid>', methods=['POST'])
def cancel_appointment(aid):
    if 'patient_id' not in session:
        return redirect(url_for('patient.login'))
    conn = get_db()
    appt = conn.execute('SELECT * FROM appointments WHERE id = ?', (aid,)).fetchone()
    if not appt:
        conn.close()
        flash('Appointment not found', 'danger')
        return redirect(url_for('patient.view_appointments'))

    # ensure the logged-in patient owns this appointment
    if appt['patient_id'] != session['patient_id']:
        conn.close()
        flash('Not authorized to cancel this appointment', 'danger')
        return redirect(url_for('patient.view_appointments'))

    conn.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (aid,))
    conn.commit()
    conn.close()
    flash('Appointment cancelled', 'success')
    return redirect(url_for('patient.view_appointments'))
