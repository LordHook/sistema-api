import sqlite3
conn = sqlite3.connect('instance/cco.db')
cursor = conn.cursor()
try:
    cursor.execute('ALTER TABLE workers ADD COLUMN start_date DATE')
    print("Added start_date to workers")
except Exception as e:
    print(e)
try:
    cursor.execute('ALTER TABLE users ADD COLUMN assigned_group INTEGER')
    print("Added assigned_group to users")
except Exception as e:
    print(e)
conn.commit()
conn.close()
