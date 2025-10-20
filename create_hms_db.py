import sqlite3

def create_hms_db(db_name="hospital_management.db"):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Enable foreign keys
    c.execute("PRAGMA foreign_keys = ON;")

    schema = """
    -- -----------------------
    -- staff table
    -- -----------------------
    CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('doctor','nurse','pharmacist','phlebotomist','admin','head')),
        contact TEXT
    );

    -- -----------------------
    -- patients
    -- -----------------------
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        dob DATE,
        phone TEXT,
        address TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    -- -----------------------
    -- rooms and room_assignments
    -- -----------------------
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT UNIQUE NOT NULL,
        type TEXT,
        rate_per_day REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS room_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
        room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE SET NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        notes TEXT
    );

    -- -----------------------
    -- medications
    -- -----------------------
    CREATE TABLE IF NOT EXISTS medications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL DEFAULT 0
    );

    -- -----------------------
    -- appointments
    -- -----------------------
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
        doctor_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE SET NULL,
        appointment_datetime TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('booked','confirmed','cancelled','completed')) DEFAULT 'booked',
        notes TEXT,
        fee REAL DEFAULT 0
    );

    -- -----------------------
    -- treatments
    -- -----------------------
    CREATE TABLE IF NOT EXISTS treatments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
        doctor_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE SET NULL,
        description TEXT,
        start_date TEXT DEFAULT (datetime('now')),
        end_date TEXT,
        room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
        cost REAL DEFAULT 0,
        notes TEXT
    );

    -- -----------------------
    -- prescriptions
    -- -----------------------
    CREATE TABLE IF NOT EXISTS prescriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
        doctor_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE SET NULL,
        pharmacist_id INTEGER REFERENCES staff(id) ON DELETE SET NULL,
        created_at TEXT DEFAULT (datetime('now')),
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS prescription_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prescription_id INTEGER NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
        medication_id INTEGER NOT NULL REFERENCES medications(id) ON DELETE SET NULL,
        dosage TEXT,
        quantity INTEGER DEFAULT 1,
        unit_price REAL DEFAULT 0,
        fulfilled INTEGER DEFAULT 0,
        fulfilled_at TEXT
    );

    -- -----------------------
    -- med dispense
    -- -----------------------
    CREATE TABLE IF NOT EXISTS med_dispense (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prescription_item_id INTEGER NOT NULL REFERENCES prescription_items(id) ON DELETE CASCADE,
        pharmacist_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE SET NULL,
        dispensed_at TEXT DEFAULT (datetime('now')),
        quantity INTEGER NOT NULL,
        notes TEXT
    );

    -- -----------------------
    -- lab tests
    -- -----------------------
    CREATE TABLE IF NOT EXISTS lab_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
        doctor_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE SET NULL,
        phlebotomist_id INTEGER REFERENCES staff(id) ON DELETE SET NULL,
        test_name TEXT NOT NULL,
        requested_at TEXT DEFAULT (datetime('now')),
        performed_at TEXT,
        result TEXT,
        status TEXT NOT NULL CHECK(status IN ('ordered','in_progress','completed','cancelled')) DEFAULT 'ordered',
        cost REAL DEFAULT 0,
        notes TEXT
    );

    -- -----------------------
    -- bills
    -- -----------------------
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
        total_amount REAL DEFAULT 0,
        paid INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        paid_at TEXT
    );

    CREATE TABLE IF NOT EXISTS bill_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
        item_type TEXT NOT NULL,
        item_ref INTEGER,
        description TEXT,
        amount REAL NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );

    -- -----------------------
    -- Triggers
    -- -----------------------
    CREATE TRIGGER IF NOT EXISTS trg_ensure_open_bill_after_insert_treatment
    AFTER INSERT ON treatments
    BEGIN
        INSERT INTO bills(patient_id, total_amount, paid, created_at)
        SELECT NEW.patient_id, 0, 0, datetime('now')
        WHERE NOT EXISTS (SELECT 1 FROM bills b WHERE b.patient_id = NEW.patient_id AND b.paid = 0);

        INSERT INTO bill_items(bill_id, item_type, item_ref, description, amount, created_at)
        VALUES (
            (SELECT id FROM bills WHERE patient_id = NEW.patient_id AND paid = 0 ORDER BY created_at DESC LIMIT 1),
            'treatment',
            NEW.id,
            COALESCE(NEW.description,'Treatment'),
            COALESCE(NEW.cost,0),
            datetime('now')
        );

        UPDATE bills
        SET total_amount = total_amount + COALESCE(NEW.cost,0)
        WHERE id = (SELECT id FROM bills WHERE patient_id = NEW.patient_id AND paid = 0 ORDER BY created_at DESC LIMIT 1);
    END;

    CREATE TRIGGER IF NOT EXISTS trg_prescription_item_after_insert
    AFTER INSERT ON prescription_items
    BEGIN
        INSERT INTO bills(patient_id, total_amount, paid, created_at)
        SELECT p.patient_id, 0, 0, datetime('now')
        FROM prescriptions p
        WHERE p.id = NEW.prescription_id
          AND NOT EXISTS (SELECT 1 FROM bills b WHERE b.patient_id = p.patient_id AND b.paid = 0);

        INSERT INTO bill_items(bill_id, item_type, item_ref, description, amount, created_at)
        VALUES (
            (SELECT id FROM bills WHERE patient_id = (SELECT patient_id FROM prescriptions WHERE id = NEW.prescription_id) AND paid = 0 ORDER BY created_at DESC LIMIT 1),
            'medication',
            NEW.id,
            (SELECT m.name FROM medications m WHERE m.id = NEW.medication_id),
            COALESCE(NEW.unit_price,0) * COALESCE(NEW.quantity,1),
            datetime('now')
        );

        UPDATE bills
        SET total_amount = total_amount + (COALESCE(NEW.unit_price,0) * COALESCE(NEW.quantity,1))
        WHERE id = (SELECT id FROM bills WHERE patient_id = (SELECT patient_id FROM prescriptions WHERE id = NEW.prescription_id) AND paid = 0 ORDER BY created_at DESC LIMIT 1);
    END;

    CREATE TRIGGER IF NOT EXISTS trg_lab_test_after_update_completed
    AFTER UPDATE OF status ON lab_tests
    WHEN NEW.status = 'completed' AND (OLD.status IS NULL OR OLD.status != 'completed')
    BEGIN
        INSERT INTO bills(patient_id, total_amount, paid, created_at)
        SELECT NEW.patient_id, 0, 0, datetime('now')
        WHERE NOT EXISTS (SELECT 1 FROM bills b WHERE b.patient_id = NEW.patient_id AND b.paid = 0);

        INSERT INTO bill_items(bill_id, item_type, item_ref, description, amount, created_at)
        VALUES (
            (SELECT id FROM bills WHERE patient_id = NEW.patient_id AND paid = 0 ORDER BY created_at DESC LIMIT 1),
            'lab_test',
            NEW.id,
            NEW.test_name,
            COALESCE(NEW.cost,0),
            datetime('now')
        );

        UPDATE bills
        SET total_amount = total_amount + COALESCE(NEW.cost,0)
        WHERE id = (SELECT id FROM bills WHERE patient_id = NEW.patient_id AND paid = 0 ORDER BY created_at DESC LIMIT 1);
    END;
    """

    c.executescript(schema)
    conn.commit()
    conn.close()
    print(f"✅ Database '{db_name}' created successfully with all tables and triggers.")


if __name__ == "__main__":
    create_hms_db()
