from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_mail import Message
from werkzeug.utils import secure_filename
import sqlite3
import os

farmer_bp = Blueprint('farmer', __name__, url_prefix='/farmer')

def get_db_connection():
    conn = sqlite3.connect('agrilink.db')
    conn.row_factory = sqlite3.Row
    return conn

@farmer_bp.record_once
def on_load(state):
    farmer_bp.app_config = state.app.config
    farmer_bp.mail = state.app.extensions['mail']

@farmer_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'farmer':
        return redirect(url_for('main.homepage'))

    page = request.args.get('page', 1, type=int)
    PER_PAGE = 6
    offset = (page - 1) * PER_PAGE
    search_query = request.args.get('search_query', '')
    location = request.args.get('location', '')

    conn = get_db_connection()
    demands_select_query = "SELECT d.*, u.name as buyer_name, u.profile_pic FROM demands d JOIN users u ON d.buyer_id = u.id"
    demands_count_query = "SELECT COUNT(d.id) FROM demands d"
    demands_conditions = []
    demands_params = []

    if search_query:
        demands_conditions.append("d.crop_name LIKE ?")
        demands_params.append(f"%{search_query}%")
    if location:
        demands_conditions.append("d.location = ?")
        demands_params.append(location)

    if demands_conditions:
        where_clause = " WHERE " + " AND ".join(demands_conditions)
        demands_select_query += where_clause
        demands_count_query += where_clause

    total_demands = conn.execute(demands_count_query, tuple(demands_params)).fetchone()[0]
    total_pages = (total_demands + PER_PAGE - 1) // PER_PAGE

    demands_select_query += " ORDER BY d.id DESC LIMIT ? OFFSET ?"
    demands_params.extend([PER_PAGE, offset])
    demands = conn.execute(demands_select_query, tuple(demands_params)).fetchall()
    conn.close()

    return render_template('farmer dashboard.html', demands=demands, search_query=search_query, location=location, page=page, total_pages=total_pages)

@farmer_bp.route('/add_crop', methods=['GET', 'POST'])
@login_required
def add_crop():
    if request.method == 'POST':
        crop_name = request.form['crop_name']
        quantity = request.form['quantity']
        price = request.form['price']
        quality = request.form['quality']
        crop_grade = request.form['crop_grade']
        harvest_date = request.form['harvest_date']
        location = request.form['location']
        image = request.files.get('image')

        filename = None
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image.save(os.path.join(farmer_bp.app_config['UPLOAD_FOLDER'], filename))

        conn = get_db_connection()
        conn.execute('INSERT INTO crops (farmer_id, crop_name, quantity, price, quality, crop_grade, harvest_date, location, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                     (current_user.id, crop_name, quantity, price, quality, crop_grade, harvest_date, location, filename))
        conn.commit()
        conn.close()
        flash('Crop registered successfully!', 'success')
        return redirect(url_for('farmer.view_my_listings'))

    return render_template('add_form.html', form_type='crop')

@farmer_bp.route('/my_listings')
@login_required
def view_my_listings():
    conn = get_db_connection()
    my_crops = conn.execute("SELECT c.*, u.name as farmer_name, u.profile_pic FROM crops c JOIN users u ON c.farmer_id = u.id WHERE c.farmer_id = ?", (current_user.id,)).fetchall()
    conn.close()
    return render_template('data_page_wrapper.html', title="My Crop Listings", items=my_crops, list_type='crops', is_owner_view=True)

@farmer_bp.route('/edit_crop/<int:crop_id>', methods=['GET', 'POST'])
@login_required
def edit_crop(crop_id):
    conn = get_db_connection()
    crop = conn.execute('SELECT * FROM crops WHERE id = ? AND farmer_id = ?', (crop_id, current_user.id)).fetchone()

    if not crop:
        flash('Crop not found or you do not have permission to edit it.', 'danger')
        conn.close()
        return redirect(url_for('farmer.view_my_listings'))

    if request.method == 'POST':
        crop_name = request.form['crop_name']
        quantity = request.form['quantity']
        price = request.form['price']
        quality = request.form['quality']
        harvest_date = request.form['harvest_date']
        image = request.files.get('image')
        current_image = crop['image']
        filename = current_image

        if 'delete_image' in request.form and current_image:
            os.remove(os.path.join(farmer_bp.app_config['UPLOAD_FOLDER'], current_image))
            filename = None

        if image and image.filename != '':
            if current_image:
                try:
                    os.remove(os.path.join(farmer_bp.app_config['UPLOAD_FOLDER'], current_image))
                except OSError:
                    pass
            filename = secure_filename(image.filename)
            image.save(os.path.join(farmer_bp.app_config['UPLOAD_FOLDER'], filename))

        conn.execute("UPDATE crops SET crop_name = ?, quantity = ?, price = ?, quality = ?, harvest_date = ?, image = ? WHERE id = ?",
                     (crop_name, quantity, price, quality, harvest_date, filename, crop_id))
        conn.commit()
        conn.close()
        flash('Crop listing updated successfully!', 'success')
        return redirect(url_for('farmer.view_my_listings'))

    conn.close()
    return render_template('data_edit_form.html', form_type='crop', data=crop)

@farmer_bp.route('/delete_crop/<int:crop_id>', methods=['POST'])
@login_required
def delete_crop(crop_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM crops WHERE id = ? AND farmer_id = ?', (crop_id, current_user.id))
    conn.commit()
    conn.close()
    flash('Crop listing deleted successfully.', 'success')
    return redirect(url_for('farmer.view_my_listings'))

@farmer_bp.route('/my_sales')
@login_required
def my_sales():
    conn = get_db_connection()
    orders = conn.execute("SELECT o.id, o.quantity, o.total_price, o.order_status, o.order_date, c.crop_name, u.name as buyer_name FROM orders o JOIN crops c ON o.crop_id = c.id JOIN users u ON o.buyer_id = u.id WHERE c.farmer_id = ? ORDER BY o.order_date DESC", (current_user.id,)).fetchall()
    conn.close()
    return render_template('farmer_sales.html', orders=orders)

@farmer_bp.route('/update_order_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    new_status = request.form.get('status')
    if not new_status:
        flash('No status provided.', 'warning')
        return redirect(url_for('farmer.my_sales'))

    conn = get_db_connection()
    order_details = conn.execute("SELECT o.id, c.crop_name, u.email as buyer_email, u.name as buyer_name FROM orders o JOIN users u ON o.buyer_id = u.id JOIN crops c ON o.crop_id = c.id WHERE o.id = ? AND c.farmer_id = ?", (order_id, current_user.id)).fetchone()

    if not order_details:
        flash('Order not found or you do not have permission to update it.', 'danger')
        conn.close()
        return redirect(url_for('farmer.my_sales'))

    conn.execute("UPDATE orders SET order_status = ? WHERE id = ? AND crop_id IN (SELECT id FROM crops WHERE farmer_id = ?)", (new_status, order_id, current_user.id))
    conn.commit()
    conn.close()

    msg = Message(f"Update on your AgriLink Order #{order_id}", recipients=[order_details['buyer_email']])
    msg.body = f"Hello {order_details['buyer_name']},\n\nThe status of your order for '{order_details['crop_name']}' has been updated to: {new_status}.\n\nYou can view your full order history here: {url_for('buyer.view_my_orders', _external=True)}\n\nThank you for using AgriLink Malawi!"
    farmer_bp.mail.send(msg)

    flash(f'Order #{order_id} status has been updated to {new_status}.', 'success')
    return redirect(url_for('farmer.my_sales'))