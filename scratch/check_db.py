import sqlite3
import os

db_path = r'D:\11\EASY-INTERVIEW\db.sqlite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='myapp_systemsettings'")
if cursor.fetchone():
    cursor.execute("SELECT COUNT(*) FROM myapp_systemsettings")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("INSERT INTO myapp_systemsettings (allow_registration, interview_timer, maintenance_mode, interview_duration, site_base_url) VALUES (1, 30, 0, 30, 'http://127.0.0.1:8000')")
        conn.commit()
        print("Inserted default SystemSettings.")
    else:
        print("SystemSettings already exists.")
else:
    print("Table myapp_systemsettings does not exist yet. Run migrations.")

conn.close()
