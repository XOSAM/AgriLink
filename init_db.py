import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_FILE = 'agrilink.db'
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print("Old database removed.")

# Connect to the database
conn = sqlite3.connect('agrilink.db')
c = conn.cursor()

# Create users table
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    profile_pic TEXT,
    phone_number TEXT,
    bank_name TEXT,
    bank_account_number TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create crops table
c.execute('''
CREATE TABLE IF NOT EXISTS crops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id INTEGER NOT NULL,
    crop_name TEXT NOT NULL,
    quantity TEXT NOT NULL,
    price REAL NOT NULL,
    quality TEXT,
    crop_grade TEXT,
    harvest_date TEXT,
    location TEXT,
    image TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (farmer_id) REFERENCES users (id)
)
''')

# Create demands table
c.execute('''
CREATE TABLE IF NOT EXISTS demands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER NOT NULL,
    crop_name TEXT NOT NULL,
    quantity TEXT NOT NULL,
    location TEXT,
    quality TEXT,
    message TEXT,
    image TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (buyer_id) REFERENCES users (id)
)
''')

# Create orders table
c.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER NOT NULL,
    crop_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    total_price REAL NOT NULL,
    delivery_option TEXT NOT NULL,
    payment_number TEXT,
    order_status TEXT DEFAULT 'pending',
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (buyer_id) REFERENCES users (id),
    FOREIGN KEY (crop_id) REFERENCES crops (id)
)
''')

# Create messages table
c.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER,
    receiver_id INTEGER NOT NULL,
    crop_id INTEGER,
    demand_id INTEGER,
    sender_name TEXT,
    sender_contact TEXT,
    subject TEXT,
    message TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users (id),
    FOREIGN KEY (receiver_id) REFERENCES users (id),
    FOREIGN KEY (crop_id) REFERENCES crops (id),
    FOREIGN KEY (demand_id) REFERENCES demands (id)
)
''')

# Create reviews table
c.execute('''
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    reviewer_id INTEGER NOT NULL,
    reviewed_user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders (id),
    FOREIGN KEY (reviewer_id) REFERENCES users (id),
    FOREIGN KEY (reviewed_user_id) REFERENCES users (id)
)
''')

# Insert a default admin user
admin_email = 'admin@agrilink.com'
admin_password = 'adminpassword'
hashed_password = generate_password_hash(admin_password)
c.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
          ('Admin User', admin_email, hashed_password, 'admin'))

# Commit and close
conn.commit()
conn.close()

print("Database tables created successfully!")
