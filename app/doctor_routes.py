from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3

doctor_bp = Blueprint('doctor', __name__)

DATABASE = 'hospital_management.db'

def get_conn():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@doctor_bp.route('/logs')
def view_logs():
    conn = get_conn()
    # include patient name for better display
    logs = conn.execute('''
        SELECT t.*, p.first_name || ' ' || p.last_name AS patient_name
        FROM treatments t
        LEFT JOIN patients p ON p.id = t.patient_id
        ORDER BY t.id DESC
    ''').fetchall()
    conn.close()
    return render_template('doctor_logs.html', logs=logs)


@doctor_bp.route('/add_treatment', methods=['GET', 'POST'])
def add_treatment():
    conn = get_conn()
    if request.method == 'POST':
        pid = request.form['patient_id']
        # prefer using logged-in doctor id
        if 'doctor_id' in request.form and request.form['doctor_id']:
            did = request.form['doctor_id']
        else:
            did = None
        # if doctor is logged in via session, use that id
        from flask import session
        if session.get('doctor_logged_in') and session.get('doctor_id'):
            did = session.get('doctor_id')

        details = request.form['details']
        conn.execute("INSERT INTO treatments (patient_id, doctor_id, description) VALUES (?, ?, ?)", (pid, did, details))
        conn.commit()
        conn.close()
        return redirect(url_for('doctor.view_logs'))

    # GET: render simple form with patients and doctors
    patients = conn.execute('SELECT id, first_name, last_name FROM patients').fetchall()
    doctors = conn.execute('SELECT doctor_id, f_name, l_name FROM doctors').fetchall()
    conn.close()
    return render_template('add_treatment.html', patients=patients, doctors=doctors)


@doctor_bp.route('/login', methods=['GET', 'POST'])
def login():
    from flask import session, flash
    conn = get_conn()
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        # username is f_name + l_name (no space)
        # try to find matching doctor
        row = conn.execute("SELECT * FROM doctors WHERE (f_name || l_name) = ? AND password = ?", (username, password)).fetchone()
        if row:
            session['doctor_logged_in'] = True
            session['doctor_id'] = row['doctor_id']
            session['doctor_name'] = f"{row['f_name']} {row['l_name']}"
            conn.close()
            return redirect(url_for('doctor.view_logs'))
        else:
            flash('Invalid doctor credentials')
    conn.close()
    return render_template('doctor_login.html')


@doctor_bp.route('/logout')
def logout():
    from flask import session
    session.pop('doctor_logged_in', None)
    session.pop('doctor_id', None)
    session.pop('doctor_name', None)
    return redirect(url_for('doctor.login'))



@doctor_bp.route('/treatment/edit/<int:tid>', methods=['GET', 'POST'])
def edit_treatment(tid):
    from flask import session, flash
    conn = get_conn()
    treatment = conn.execute('SELECT t.*, p.first_name || " " || p.last_name AS patient_name FROM treatments t LEFT JOIN patients p ON p.id = t.patient_id WHERE t.id = ?', (tid,)).fetchone()
    if not treatment:
        conn.close()
        flash('Treatment not found')
        return redirect(url_for('doctor.view_logs'))

    # Only the assigned doctor (or if not logged in, prevent edit)
    if not session.get('doctor_logged_in') or session.get('doctor_id') != treatment['doctor_id']:
        conn.close()
        flash('Not authorized to edit this treatment')
        return redirect(url_for('doctor.view_logs'))

    if request.method == 'POST':
        desc = request.form.get('description')
        conn.execute('UPDATE treatments SET description = ? WHERE id = ?', (desc, tid))
        conn.commit()
        conn.close()
        flash('Treatment updated')
        return redirect(url_for('doctor.view_logs'))

    conn.close()
    return render_template('edit_treatment.html', treatment=treatment)


@doctor_bp.route('/doctors')
def list_doctors():
    conn = get_conn()
    doctors = conn.execute('SELECT * FROM doctors ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('doctors.html', doctors=doctors)


@doctor_bp.route('/profile/<int:did>')
def doctor_profile(did):
    conn = get_conn()
    doc = conn.execute('SELECT * FROM doctors WHERE doctor_id = ?', (did,)).fetchone()
    treatments = conn.execute('SELECT * FROM treatments WHERE doctor_id = ? ORDER BY start_date DESC', (did,)).fetchall()
    conn.close()
    return render_template('doctor_profile.html', doctor=doc, treatments=treatments)


@doctor_bp.route('/patients')
def my_patients():
    # show patients assigned to logged-in doctor
    from flask import session, redirect, flash
    if not session.get('doctor_logged_in'):
        flash('Please login as doctor')
        return redirect(url_for('doctor.login'))
    did = session.get('doctor_id')
    conn = get_conn()
    patients = conn.execute('SELECT id, first_name, last_name, phone FROM patients WHERE doctor = ?', (did,)).fetchall()
    conn.close()
    return render_template('doctor_patients.html', patients=patients)


@doctor_bp.route('/patient/<int:pid>', methods=['GET', 'POST'])
def view_patient(pid):
    # doctor can add symptoms (as treatment), prescribe (prescription + items)
    from flask import session, flash
    if not session.get('doctor_logged_in'):
        flash('Please login as doctor')
        return redirect(url_for('doctor.login'))
    did = session.get('doctor_id')
    conn = get_conn()
    patient = conn.execute('SELECT * FROM patients WHERE id = ?', (pid,)).fetchone()
    if not patient:
        conn.close()
        flash('Patient not found')
        return redirect(url_for('doctor.my_patients'))

    # handle POST actions: add_symptom, add_prescription
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_symptom':
            desc = request.form.get('description')
            conn.execute('INSERT INTO treatments (patient_id, doctor_id, description, start_date) VALUES (?, ?, ?, datetime("now"))', (pid, did, desc))
            conn.commit()
            flash('Symptom / treatment note added')
        elif action == 'prescribe':
            med_name = request.form.get('medication_name')
            dosage = request.form.get('dosage')
            qty = int(request.form.get('quantity') or 1)
            unit_price = float(request.form.get('unit_price') or 0)
            # ensure medication exists (simple upsert)
            m = conn.execute('SELECT id FROM medications WHERE name = ?', (med_name,)).fetchone()
            if not m:
                cur = conn.execute('INSERT INTO medications (name, description, price) VALUES (?, ?, ?)', (med_name, '', unit_price))
                medication_id = cur.lastrowid
            else:
                medication_id = m['id']

            # create prescription
            cur = conn.execute('INSERT INTO prescriptions (patient_id, doctor_id, notes) VALUES (?, ?, ?)', (pid, did, request.form.get('notes') or ''))
            presc_id = cur.lastrowid
            # add item
            conn.execute('INSERT INTO prescription_items (prescription_id, medication_id, dosage, quantity, unit_price) VALUES (?, ?, ?, ?, ?)', (presc_id, medication_id, dosage, qty, unit_price))
            conn.commit()
            flash('Prescription created')

    treatments = conn.execute('SELECT * FROM treatments WHERE patient_id = ? ORDER BY start_date DESC', (pid,)).fetchall()
    prescriptions = conn.execute('SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY created_at DESC', (pid,)).fetchall()
    conn.close()
    return render_template('doctor_patient.html', patient=patient, treatments=treatments, prescriptions=prescriptions)
