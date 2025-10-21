from flask import Flask
from admin_routes import admin_bp
from patient_routes import patient_bp
from doctor_routes import doctor_bp

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

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)

