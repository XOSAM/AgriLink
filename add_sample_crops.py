import sqlite3

# Connect to the database
conn = sqlite3.connect('agrilink.db')
c = conn.cursor()

# Sample crops data
sample_crops = [
    (1, 'Maize', '500kg', 150.0, 'Premium', '2024-10-01', 'maize.jpg'),
    (1, 'Tobacco', '200kg', 500.0, 'High Quality', '2024-09-15', 'tobacco.jpg'),
    (2, 'Tea', '100kg', 300.0, 'Organic', '2024-09-20', 'tea.jpg'),
    (2, 'Cotton', '300kg', 200.0, 'Grade A', '2024-09-25', 'cotton.jpg'),
    (3, 'Groundnuts', '150kg', 250.0, 'Fresh', '2024-10-05', 'groundnuts.jpg'),
    (3, 'Cassava', '400kg', 100.0, 'Staple', '2024-09-30', 'cassava.jpg'),
    (1, 'Rice', '250kg', 180.0, 'Long Grain', '2024-10-10', 'rice.jpg'),
    (2, 'Soybeans', '350kg', 220.0, 'High Protein', '2024-09-28', 'soybeans.jpg'),
    (3, 'Wheat', '200kg', 160.0, 'Winter Wheat', '2024-10-02', 'wheat.jpg'),
    (1, 'Sugarcane', '1000kg', 50.0, 'Sweet Variety', '2024-09-22', 'sugarcane.jpg'),
    (2, 'Coffee', '80kg', 600.0, 'Arabica', '2024-09-18', 'coffee.jpg'),
    (3, 'Bananas', '500 bunches', 120.0, 'Fresh', '2024-10-08', 'bananas.jpg'),
    (4, 'Maize', '300kg', 160.0, 'Grade A', '2024-10-15', 'maize2.jpg'),
    (4, 'Tobacco', '150kg', 550.0, 'Premium', '2024-09-20', 'tobacco2.jpg'),
    (4, 'Sugarcane', '800kg', 55.0, 'Organic', '2024-09-25', 'sugarcane2.jpg'),
    (4, 'Cassava', '250kg', 110.0, 'Fresh', '2024-10-05', 'cassava2.jpg'),
]

# Insert sample crops
c.executemany("INSERT INTO crops (farmer_id, crop_name, quantity, price, quality, harvest_date, image) VALUES (?, ?, ?, ?, ?, ?, ?)", sample_crops)

# Commit and close
conn.commit()
conn.close()

print("Sample crops added successfully!")
