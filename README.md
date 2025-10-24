# DBMS_HMS_PROJ

This is a small Hospital Management System (HMS) demo built with Flask and SQLite.

Overview (pipeline)
- Admin logs in via `/admin/login`.
- Admin can add patients (`/admin/patients/add`) and add doctors (`/admin/doctors/add`). When adding a doctor the admin sets a password which the doctor will use to log in.
- Patients log in using their patient ID at `/patient/login` and can book appointments at `/patient/book` (patients do not select doctors when booking).
- Admin reviews booked appointments at `/admin/appointments`, assigns a doctor, and confirms the appointment. Once confirmed the assigned doctor will see the appointment in their `/doctor/appointments` view.

Quick start (development)
1. Create and activate a virtual environment (example uses the included `myenv`):

```powershell
# Activate (Windows PowerShell)
.\myenv\Scripts\Activate.ps1
```

2. Run the app:

```powershell
python .\app\app.py
```

3. Open the app in a browser:

- Admin login: `http://localhost:5000/admin/login`
- Patient login: `http://localhost:5000/patient/login`
- Doctor login: `http://localhost:5000/doctor/login`

