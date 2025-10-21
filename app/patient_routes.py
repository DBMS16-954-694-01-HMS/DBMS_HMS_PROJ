from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3

patient_bp = Blueprint('patient', __name__)

@patient_bp.route('/book')
def book_appointment():
    if request.method == 'POST':
        pid = request.form['patient_id']
        did = request.form['doctor_id']
        date = request.form['date']
        with sqlite3.connect('hospital_management.db') as conn:
            conn.execute("INSERT INTO appointment (patient_id, doctor_id, appointment_datetime) VALUES (?, ?, ?)", (pid, did, date))
        return redirect(url_for('patient.view_appointments'))
    # GET: provide list of doctors and patients for booking
    with sqlite3.connect('hospital_management.db') as conn:
        conn.row_factory = sqlite3.Row
        patients = conn.execute('SELECT id, first_name, last_name FROM patients').fetchall()
        doctors = conn.execute('SELECT doctor_id, f_name, l_name FROM doctors').fetchall()
    return render_template('patient_book.html', patients=patients, doctors=doctors)


@patient_bp.route('/appointments')
def view_appointments():
    with sqlite3.connect('hospital_management.db') as conn:
        rows = conn.execute("SELECT * FROM appointment").fetchall()
    return render_template('patient_appointments.html', rows=rows)
