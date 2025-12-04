from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask_mail import Message
import sqlite3

auth_bp = Blueprint('auth', __name__)

def get_db_connection():
    conn = sqlite3.connect('agrilink.db')
    conn.row_factory = sqlite3.Row
    return conn

@auth_bp.record_once
def on_load(state):
    auth_bp.s = URLSafeTimedSerializer(state.app.secret_key)
    auth_bp.mail = state.app.extensions['mail']
    from models import User # Import from the new models file
    auth_bp.User = User

@auth_bp.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        if 'name' in request.form:  # Registration
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            role = request.form['role']
            conn = get_db_connection()
            existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
            if existing_user:
                flash('Email already registered')
                conn.close()
                return render_template('auth.html')
            hashed_password = generate_password_hash(password)

            if role == 'farmer':
                phone_number = request.form.get('phone_number')
                bank_name = request.form.get('bank_name')
                bank_account_number = request.form.get('bank_account_number')
                if not all([phone_number, bank_name, bank_account_number]):
                    flash('As a farmer, please provide all required bank and phone details.', 'danger')
                    return render_template('auth.html', form_data=request.form)
                conn.execute('INSERT INTO users (name, email, password, role, phone_number, bank_name, bank_account_number) VALUES (?, ?, ?, ?, ?, ?, ?)',
                             (name, email, hashed_password, role, phone_number, bank_name, bank_account_number))
            else:
                conn.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)', (name, email, hashed_password, role))

            conn.commit()
            conn.close()
            flash('Registration successful! Please login.')
            return render_template('auth.html')
        else:  # Login
            email = request.form['email']
            password = request.form['password']
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            conn.close()
            if user and check_password_hash(user['password'], password):
                user_obj = auth_bp.User(user['id'], user['email'], user['name'], user['role'])
                login_user(user_obj)
                session['logged_in'] = True
                session['role'] = user['role']
                session['name'] = user['name']
                session['profile_pic'] = user['profile_pic'] if user['profile_pic'] else 'default.jpg'
                if user['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user['role'] == 'farmer':
                    return redirect(url_for('farmer.dashboard'))
                elif user['role'] == 'buyer':
                    return redirect(url_for('buyer.dashboard'))
            flash('Invalid email or password')
    return render_template('auth.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('main.homepage'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user:
            token = auth_bp.s.dumps(email, salt='password-reset-salt')
            reset_url = url_for('auth.reset_with_token', token=token, _external=True)
            msg = Message('Password Reset Request for AgriLink Malawi', recipients=[email])
            msg.body = f"Hello,\n\nYou requested a password reset. Please click the link below to set a new password. This link will expire in 1 hour.\n\n{reset_url}\n\nIf you did not request this, please ignore this email.\n\nThanks,\nThe AgriLink Malawi Team"
            auth_bp.mail.send(msg)
        flash('If an account with that email exists, password reset instructions have been sent.', 'info')
        return redirect(url_for('auth.auth'))
    return render_template('forgot_password.html')

@auth_bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    try:
        email = auth_bp.s.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        flash('The password reset link has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    except:
        flash('The password reset link is invalid.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', token=token)
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        conn.execute('UPDATE users SET password = ? WHERE email = ?', (hashed_password, email))
        conn.commit()
        conn.close()
        flash('Your password has been updated successfully! Please login.', 'success')
        return redirect(url_for('auth.auth'))
    return render_template('reset_password.html', token=token)