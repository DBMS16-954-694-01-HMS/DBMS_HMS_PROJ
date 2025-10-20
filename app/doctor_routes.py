from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/logs')
def view_logs():
    with sqlite3.connect('hospital_management.db') as conn:
        logs = conn.execute("SELECT * FROM treatments").fetchall()
    return render_template('doctor_logs.html', logs=logs)

@doctor_bp.route('/add_treatment', methods=['POST'])
def add_treatment():
    pid = request.form['patient_id']
    did = request.form['doctor_id']
    details = request.form['details']
    with sqlite3.connect('hospital_management.db') as conn:
        conn.execute("INSERT INTO treatments (patient_id, doctor_id, description) VALUES (?, ?, ?)", (pid, did, details))
    return redirect(url_for('doctor.view_logs'))
