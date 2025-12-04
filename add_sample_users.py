import sqlite3
from werkzeug.security import generate_password_hash

# Connect to the database
conn = sqlite3.connect('agrilink.db')
c = conn.cursor()

# Sample users data (farmers)
sample_users = [
    ('Farmer John', 'john@example.com', generate_password_hash('password'), 'farmer', 'farmer1.jpg'),
    ('Farmer Mary', 'mary@example.com', generate_password_hash('password'), 'farmer', 'farmer2.jpg'),
    ('Farmer Peter', 'peter@example.com', generate_password_hash('password'), 'farmer', 'farmer3.jpg'),
]

# Insert sample users (skip if email exists)
for user in sample_users:
    c.execute("SELECT id FROM users WHERE email=?", (user[1],))
    if not c.fetchone():
        c.execute("INSERT INTO users (name, email, password, role, profile_pic) VALUES (?, ?, ?, ?, ?)", user)

# Commit and close
conn.commit()
conn.close()

print("Sample users added successfully!")
