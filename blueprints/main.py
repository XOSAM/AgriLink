from flask import Blueprint, render_template, request, session, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os

main_bp = Blueprint('main', __name__)

def get_db_connection():
    conn = sqlite3.connect('agrilink.db')
    conn.row_factory = sqlite3.Row
    return conn

@main_bp.route('/')
def homepage():
    conn = get_db_connection()
    featured_crops = conn.execute("""
        SELECT c.*, u.name as farmer_name
        FROM crops c JOIN users u ON c.farmer_id = u.id
        ORDER BY c.id DESC
        LIMIT 3
    """).fetchall()
    conn.close()
    return render_template('homepage.html', featured_crops=featured_crops)

@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    return redirect(url_for('main.view_user_profile', user_id=current_user.id))

@main_bp.route('/profile/<int:user_id>', methods=['GET', 'POST'])
@login_required
def view_user_profile(user_id):
    conn = get_db_connection()
    app_config = current_app.config # Access app config using current_app

    if user_id == current_user.id and request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Update farmer-specific fields
        if current_user.role == 'farmer':
            phone_number = request.form.get('phone_number')
            bank_name = request.form.get('bank_name')
            bank_account_number = request.form.get('bank_account_number')
            conn.execute('UPDATE users SET phone_number = ?, bank_name = ?, bank_account_number = ? WHERE id = ?', (phone_number, bank_name, bank_account_number, user_id))

        conn.execute('UPDATE users SET name = ?, email = ? WHERE id = ?', (name, email, user_id))
        session['name'] = name

        if password:
            hashed_password = generate_password_hash(password)
            conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user_id))

        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '':
                filename = secure_filename(file.filename)
                save_path = os.path.join(app_config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                conn.execute('UPDATE users SET profile_pic = ? WHERE id = ?', (filename, user_id))
                session['profile_pic'] = filename

        conn.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.view_user_profile', user_id=user_id))

    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    reviews = conn.execute("SELECT r.rating, r.comment, r.created_at as review_date, u.name as reviewer_name FROM reviews r JOIN users u ON r.reviewer_id = u.id WHERE r.reviewed_user_id = ? ORDER BY r.created_at DESC", (user_id,)).fetchall()
    avg_rating_data = conn.execute('SELECT AVG(rating) as avg_rating FROM reviews WHERE reviewed_user_id = ?', (user_id,)).fetchone()
    avg_rating = avg_rating_data['avg_rating'] if avg_rating_data['avg_rating'] else 0
    conn.close()

    if not user_data:
        flash('User not found.', 'danger')
        return redirect(url_for('main.homepage'))

    return render_template('user_profile.html', user=user_data, reviews=reviews, avg_rating=avg_rating)