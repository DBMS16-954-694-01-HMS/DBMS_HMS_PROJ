from flask import Flask
from admin_routes import admin_bp
from patient_routes import patient_bp
from doctor_routes import doctor_bp

# also import the modules so we can print which DB they point to on startup
import admin_routes as admin_mod
import patient_routes as patient_mod
import doctor_routes as doctor_mod
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(patient_bp, url_prefix='/patient')
app.register_blueprint(doctor_bp, url_prefix='/doctor')


@app.route('/')
def index():
    # default landing: redirect to admin login
    from flask import redirect, url_for
    return redirect(url_for('admin.login'))

def _log_db_paths():
    try:
        print('--- HMS DB paths ---')
        print(' admin DB:', os.path.abspath(admin_mod.DATABASE))
        print(' patient DB:', os.path.abspath(patient_mod.DATABASE))
        print(' doctor DB:', os.path.abspath(doctor_mod.DATABASE))
        print('--------------------')
    except Exception as e:
        print('Could not resolve DB paths:', e)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    _log_db_paths()
    app.run(debug=True, port=port)

