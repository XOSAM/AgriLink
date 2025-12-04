import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import login_required, LoginManager, UserMixin, login_user, logout_user, current_user
from flask_mail import Mail
from werkzeug.utils import secure_filename
import os
import requests

from blueprints.main import main_bp
from blueprints.auth import auth_bp
from blueprints.farmer import farmer_bp
from blueprints.buyer import buyer_bp
from blueprints.messaging import messaging_bp
from models import User

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure key
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

# --- Email and Password Reset Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com') # Use your email
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-gmail-app-password') # Use your App Password
app.config['MAIL_DEFAULT_SENDER'] = ('AgriLink Malawi', app.config['MAIL_USERNAME'])

# Initialize extensions
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.auth' # Use the blueprint name

# Register Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(farmer_bp)
app.register_blueprint(buyer_bp)
app.register_blueprint(messaging_bp)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['email'], user['name'], user['role'])
    return None

def get_db_connection():
    conn = sqlite3.connect('agrilink.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/admin/reports')
@login_required
def admin_reports():
    conn = get_db_connection()
    c = conn.cursor()

    # Get statistics
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM crops")
    total_crops = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM demands")
    total_demands = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM messages")
    total_messages = c.fetchone()[0]

    # Active farmers (with crops)
    c.execute("SELECT COUNT(DISTINCT farmer_id) FROM crops")
    active_farmers = c.fetchone()[0]

    # Active buyers (with demands)
    c.execute("SELECT COUNT(DISTINCT buyer_id) FROM demands")
    active_buyers = c.fetchone()[0]

    conn.close()

    return render_template('admin_reports.html',
                         total_users=total_users,
                         total_crops=total_crops,
                         total_demands=total_demands,
                         total_messages=total_messages,
                         active_farmers=active_farmers,
                         active_buyers=active_buyers)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('homepage'))
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE role='farmer'")
    farmers_count_result = c.fetchone()
    farmers_count = farmers_count_result[0] if farmers_count_result else 0
    c.execute("SELECT COUNT(*) FROM users WHERE role='buyer'")
    buyers_count_result = c.fetchone()
    buyers_count = buyers_count_result[0] if buyers_count_result else 0
    c.execute("SELECT COUNT(*) FROM orders")
    total_transactions_result = c.fetchone()
    total_transactions = total_transactions_result[0] if total_transactions_result else 0
    conn.close()
    return render_template('admin dashboard.html', farmers_count=farmers_count, buyers_count=buyers_count, total_transactions=total_transactions)

@app.route('/purchase/<int:crop_id>', methods=['POST'])
@login_required
def purchase_crop(crop_id):
    if current_user.role != 'buyer':
        flash('Only buyers can purchase crops.', 'danger')
        return redirect(url_for('homepage'))

    conn = get_db_connection()
    crop = conn.execute('SELECT * FROM crops WHERE id = ?', (crop_id,)).fetchone()

    if not crop:
        flash('Crop not found.', 'danger')
        conn.close()
        return redirect(url_for('buyer.dashboard'))

    # Use .get() to avoid BadRequest errors and provide clearer feedback
    form_data = request.form
    required_fields = ['quantity', 'deliveryOption', 'network']
    for field in required_fields:
        if field not in form_data:
            flash(f"The form is missing the required '{field}' field. Please try again.", 'danger')
            return redirect(url_for('buyer.view_crop', crop_id=crop_id))

    try:
        quantity = float(request.form['quantity'])
        delivery_option = request.form['deliveryOption']
        network = request.form['network'] # e.g., 'airtel', 'mpamba'
        # Basic validation
        if quantity <= 0:
            flash('Quantity must be a positive number.', 'danger')
            return redirect(url_for('buyer.dashboard'))

        # Calculate total price
        total_price = quantity * crop['price']
        if delivery_option == 'delivery':
            total_price += 5000  # Add estimated delivery fee

        print(f"DEBUG: Incoming request form data: {request.form}")
        print(f"DEBUG: Calculated total_price: {total_price}")

        # Insert order into the database first
        cursor = conn.execute("""
            INSERT INTO orders (buyer_id, crop_id, quantity, total_price, delivery_option, payment_number, order_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (current_user.id, crop_id, quantity, total_price, delivery_option, None, 'pending'))
        order_id = cursor.lastrowid
        conn.commit()

        # Prepare data for the PayChangu Popup
        payment_data = {
            'public_key': 'PUB-W9OMGGMvPMmbmXKgMRskty1lfpk0zguo', # Your public key
            'amount': int(total_price),  # PayChangu expects integer amount in MWK
            'currency': 'MWK',
            'tx_ref': f'agri_order_{order_id}',
            'callback_url': url_for('payment_webhook', _external=True),
            'return_url': url_for('payment_confirmation', _external=True),
            'customer': {
                'email': current_user.email,
                'first_name': current_user.name.split()[0] if current_user.name.split() else current_user.name,
                'last_name': current_user.name.split()[1] if len(current_user.name.split()) > 1 else '',
            },
            'customization': {
                'title': f'Payment for {crop["crop_name"]}',
                'description': f'Order #{order_id}: {quantity}kg of {crop["crop_name"]}'
            }
        }

        # Render a page that will trigger the payment popup
        return render_template('payment_popup.html', payment_data=payment_data)

    except KeyError as e:
        # This is a fallback, but the check above should catch it.
        flash(f"An error occurred: Missing form field {e}. Please check the form and try again.", 'danger')
    except Exception as e:
        flash(f'An unexpected error occurred: {e}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('buyer.dashboard'))

@app.route('/admin/farmers')
@login_required
def admin_farmers():
    if current_user.role != 'admin':
        return redirect(url_for('homepage'))
    conn = get_db_connection()
    farmers = conn.execute("SELECT id, name, email FROM users WHERE role = 'farmer'").fetchall()
    conn.close()
    return render_template('admin_farmers.html', farmers=farmers)

@app.route('/admin/buyers')
@login_required
def admin_buyers():
    if current_user.role != 'admin':
        return redirect(url_for('homepage'))
    conn = get_db_connection()
    buyers = conn.execute("SELECT id, name, email FROM users WHERE role = 'buyer'").fetchall()
    conn.close()
    return render_template('admin_buyers.html', buyers=buyers)

@app.route('/admin/all_orders')
@login_required
def admin_all_orders():
    """Displays a list of all orders on the platform for the admin."""
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.homepage'))

    conn = get_db_connection()
    orders = conn.execute("""
        SELECT 
            o.id, o.order_date, o.total_price, o.order_status,
            c.crop_name,
            b.name as buyer_name,
            f.name as farmer_name
        FROM orders o
        JOIN crops c ON o.crop_id = c.id
        JOIN users b ON o.buyer_id = b.id
        JOIN users f ON c.farmer_id = f.id
        ORDER BY o.order_date DESC
    """).fetchall()
    conn.close()
    return render_template('admin_all_orders.html', orders=orders)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    """Allows admin to delete a user and their associated data."""
    if current_user.role != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.homepage'))

    conn = get_db_connection()
    try:
        # To maintain data integrity, we should delete related records first.
        # This is a basic implementation. For production, consider soft deletes or more robust cascading.
        conn.execute("DELETE FROM reviews WHERE reviewer_id = ? OR reviewed_user_id = ?", (user_id, user_id))
        conn.execute("DELETE FROM messages WHERE sender_id = ? OR receiver_id = ?", (user_id, user_id))
        conn.execute("DELETE FROM orders WHERE buyer_id = ?", (user_id,))
        conn.execute("DELETE FROM crops WHERE farmer_id = ?", (user_id,))
        conn.execute("DELETE FROM demands WHERE buyer_id = ?", (user_id,))
        
        # Finally, delete the user
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        flash(f'User ID {user_id} and all their associated data have been deleted.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred while deleting the user: {e}', 'danger')
    finally:
        conn.close()

    # Redirect back to the page the admin came from
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/admin/messages')
@login_required
def admin_messages():
    """Allows admin to view all messages on the platform."""
    if current_user.role != 'admin':
        return redirect(url_for('homepage'))
    
    conn = get_db_connection()
    messages = conn.execute("""
        SELECT m.id, m.message, m.sent_at, s.name as sender_name, r.name as receiver_name 
        FROM messages m
        JOIN users s ON m.sender_id = s.id
        JOIN users r ON m.receiver_id = r.id
        ORDER BY m.sent_at DESC
    """).fetchall()
    conn.close()
    return render_template('admin_messages.html', messages=messages)

@app.route('/admin/settings')
def admin_settings():
    return render_template('admin_settings.html')

@app.route('/payment/confirmation')
@login_required
def payment_confirmation():
    """Display payment confirmation page based on return URL from PayChangu."""
    status = request.args.get('status')
    tx_ref = request.args.get('tx_ref')
    order_id = None

    # Try to get the order ID for a more personalized message
    if tx_ref:
        try:
            order_id = int(tx_ref.split('_')[-1])
        except (ValueError, IndexError):
            order_id = None

    return render_template('payment_confirmation.html', status=status, order_id=order_id)

@app.route('/payment/webhook', methods=['POST'])
def payment_webhook():
    """Handle PayChangu payment callback"""
    try:
        callback_data = request.get_json()
        print(f"DEBUG: Received webhook data: {callback_data}")

        # Extract transaction reference and status
        tx_ref = callback_data.get('data', {}).get('tx_ref')
        status = callback_data.get('status')

        if not tx_ref:
            print("Webhook error: tx_ref not found in payload")
            return {'status': 'error', 'message': 'tx_ref not found'}, 400

        # Extract order_id from tx_ref (e.g., 'agri_order_123')
        try:
            order_id = int(tx_ref.split('_')[-1])
        except (ValueError, IndexError):
            print(f"Webhook error: Could not parse order_id from tx_ref: {tx_ref}")
            return {'status': 'error', 'message': 'Invalid tx_ref format'}, 400

        # Verify the callback (in production, you should verify the signature)
        if status == 'success':
            conn = get_db_connection()
            # Update order status to paid
            conn.execute("UPDATE orders SET order_status = 'paid' WHERE id = ?", (order_id,))
            conn.commit()
            conn.close()
            print(f"SUCCESS: Order {order_id} status updated to 'paid'.")

        return {'status': 'success'}, 200

    except Exception as e:
        print(f"Payment webhook processing error: {e}")
        return {'status': 'error'}, 400

@app.route('/about-us', methods=['GET', 'POST'])
def about_us():
    """Displays the combined info page and handles the public contact form."""
    if request.method == 'POST':
        sender_name = request.form.get('name')
        sender_contact = request.form.get('contact')
        message_text = request.form.get('message')

        if not all([sender_name, sender_contact, message_text]):
            flash('Please fill out all fields in the contact form.', 'danger')
            return redirect(url_for('about_us') + '#contact-form')

        try:
            conn = get_db_connection()
            # Assuming admin user has id=1. Change if your admin user has a different ID.
            admin_receiver_id = 1 
            conn.execute("""
                INSERT INTO messages (receiver_id, sender_name, sender_contact, subject, message)
                VALUES (?, ?, ?, ?, ?)
            """, (admin_receiver_id, sender_name, sender_contact, 'Contact Form Submission', message_text))
            conn.commit()
            conn.close()
            flash('Thank you for your message! We will get back to you soon.', 'success')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
        
        return redirect(url_for('about_us') + '#contact-form')

    return render_template('about_us.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
