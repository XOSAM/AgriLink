import sqlite3
from werkzeug.security import generate_password_hash

# Connect to the database
conn = sqlite3.connect('agrilink.db')
c = conn.cursor()

# Admin user data
admin_user = ('Admin User', 'admin@agrilink.com', generate_password_hash('adminpass'), 'admin', 'admin.jpg')

# Insert admin user (skip if email exists)
c.execute("SELECT id FROM users WHERE email=?", (admin_user[1],))
if not c.fetchone():
    c.execute("INSERT INTO users (name, email, password, role, profile_pic) VALUES (?, ?, ?, ?, ?)", admin_user)

# Commit and close
conn.commit()
conn.close()

print("Admin user added successfully!")
