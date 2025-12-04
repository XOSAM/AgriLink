import sqlite3
from werkzeug.security import generate_password_hash

# Connect to the database
conn = sqlite3.connect('agrilink.db')
c = conn.cursor()

# Update admin user role to 'admin'
c.execute("UPDATE users SET role = 'admin' WHERE email = 'admin@agrilink.com'")

# Commit and close
conn.commit()
conn.close()

print("Admin user role updated to 'admin'.")
