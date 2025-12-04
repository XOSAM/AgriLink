from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import sqlite3

buyer_bp = Blueprint('buyer', __name__, url_prefix='/buyer')

def get_db_connection():
    conn = sqlite3.connect('agrilink.db')
    conn.row_factory = sqlite3.Row
    return conn

@buyer_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'buyer':
        return redirect(url_for('main.homepage'))
    
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 6
    offset = (page - 1) * PER_PAGE
    search_query = request.args.get('search_query', '')
    location = request.args.get('location', '')
    crop_category = request.args.get('crop_category', '')

    conn = get_db_connection()

    # Get unique crop names for categories
    crop_categories = conn.execute("SELECT DISTINCT crop_name FROM crops ORDER BY crop_name").fetchall()

    select_query = "SELECT c.*, u.name as farmer_name, u.profile_pic FROM crops c JOIN users u ON c.farmer_id = u.id"
    count_query = "SELECT COUNT(c.id) FROM crops c"
    conditions = ["c.farmer_id != ?"]
    params = [current_user.id]

    if search_query:
        conditions.append("c.crop_name LIKE ?")
        params.append(f"%{search_query}%")
    if location:
        conditions.append("c.location = ?")
        params.append(location)
    if crop_category:
        conditions.append("c.crop_name = ?")
        params.append(crop_category)

    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)
        select_query += where_clause
        count_query += where_clause

    total_crops = conn.execute(count_query, tuple(params)).fetchone()[0]
    total_pages = (total_crops + PER_PAGE - 1) // PER_PAGE

    select_query += " ORDER BY c.id DESC LIMIT ? OFFSET ?"
    params.extend([PER_PAGE, offset])
    crops = conn.execute(select_query, tuple(params)).fetchall()

    my_demands = conn.execute('SELECT * FROM demands WHERE buyer_id = ? ORDER BY id DESC', (current_user.id,)).fetchall()
    conn.close()

    return render_template('buyer dashboard.html',
                           crops=crops, my_demands=my_demands,
                           user=current_user.name,
                           search_query=search_query, location=location, crop_category=crop_category,
                           crop_categories=crop_categories,
                           page=page, total_pages=total_pages)

@buyer_bp.route('/add_demand', methods=['GET', 'POST'])
@login_required
def add_demand():
    if request.method == 'POST':
        crop_name = request.form['crop_name']
        quantity = request.form['quantity']
        location = request.form['location']
        quality = request.form.get('quality')
        message = request.form.get('message')

        conn = get_db_connection()
        conn.execute('INSERT INTO demands (buyer_id, crop_name, quantity, location, quality, message) VALUES (?, ?, ?, ?, ?, ?)',
                     (current_user.id, crop_name, quantity, location, quality, message))
        conn.commit()
        conn.close()
        flash('Your demand has been posted successfully!', 'success')
        return redirect(url_for('buyer.view_my_demands'))

    return render_template('add_form.html', form_type='demand')

@buyer_bp.route('/my_demands')
@login_required
def view_my_demands():
    conn = get_db_connection()
    my_demands = conn.execute("SELECT d.*, u.name as buyer_name FROM demands d JOIN users u ON d.buyer_id = u.id WHERE d.buyer_id = ?", (current_user.id,)).fetchall()
    conn.close()
    return render_template('data_page_wrapper.html', title="My Demands", items=my_demands, list_type='demands', is_owner_view=True)

@buyer_bp.route('/crop/<int:crop_id>')
@login_required
def view_crop(crop_id):
    """Displays details for a single crop."""
    if current_user.role != 'buyer':
        return redirect(url_for('main.homepage'))

    conn = get_db_connection()
    crop = conn.execute("SELECT c.*, u.name as farmer_name, u.profile_pic FROM crops c JOIN users u ON c.farmer_id = u.id WHERE c.id = ?", (crop_id,)).fetchone()
    conn.close()

    if not crop:
        flash('Crop not found.', 'danger')
        return redirect(url_for('buyer.dashboard'))

    return render_template('view_crop.html', crop=crop)

@buyer_bp.route('/edit_demand/<int:demand_id>', methods=['GET', 'POST'])
@login_required
def edit_demand(demand_id):
    conn = get_db_connection()
    demand = conn.execute('SELECT * FROM demands WHERE id = ? AND buyer_id = ?', (demand_id, current_user.id)).fetchone()

    if not demand:
        flash('Demand not found or you do not have permission to edit it.', 'danger')
        conn.close()
        return redirect(url_for('buyer.view_my_demands'))

    if request.method == 'POST':
        crop_name = request.form['crop_name']
        quantity = request.form['quantity']
        location = request.form['location']
        quality = request.form.get('quality')
        message = request.form.get('message')
        image = request.files.get('image')
        current_image = demand['image']
        filename = current_image

        if 'delete_image' in request.form and current_image:
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], current_image))
            except OSError:
                pass
            filename = None

        if image and image.filename != '':
            if current_image:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], current_image))
                except OSError:
                    pass
            filename = secure_filename(image.filename)
            image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        conn.execute("UPDATE demands SET crop_name = ?, quantity = ?, location = ?, quality = ?, message = ?, image = ? WHERE id = ?",
                     (crop_name, quantity, location, quality, message, filename, demand_id))
        conn.commit()
        conn.close()
        flash('Demand updated successfully!', 'success')
        return redirect(url_for('buyer.view_my_demands'))

    conn.close()
    return render_template('data_edit_form.html', form_type='demand', data=demand)

@buyer_bp.route('/delete_demand/<int:demand_id>', methods=['POST'])
@login_required
def delete_demand(demand_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM demands WHERE id = ? AND buyer_id = ?', (demand_id, current_user.id))
    conn.commit()
    conn.close()
    flash('Demand deleted successfully.', 'success')
    return redirect(url_for('buyer.view_my_demands'))

@buyer_bp.route('/my_orders')
@login_required
def view_my_orders():
    conn = get_db_connection()
    # Corrected the query to select r.created_at instead of the non-existent r.review_date
    orders = conn.execute("""
        SELECT 
            o.id, o.quantity, o.total_price, o.order_status, o.order_date, 
            c.crop_name, 
            u.name as farmer_name, 
            c.farmer_id, 
            r.id as review_id 
        FROM orders o 
        JOIN crops c ON o.crop_id = c.id 
        JOIN users u ON c.farmer_id = u.id 
        LEFT JOIN reviews r ON o.id = r.order_id AND r.reviewer_id = o.buyer_id 
        WHERE o.buyer_id = ? ORDER BY o.order_date DESC
    """, (current_user.id,)).fetchall()
    conn.close()
    return render_template('order_history.html', orders=orders)

@buyer_bp.route('/leave_review/<int:order_id>', methods=['GET', 'POST'])
@login_required
def leave_review(order_id):
    conn = get_db_connection()
    order = conn.execute('SELECT o.*, c.farmer_id FROM orders o JOIN crops c ON o.crop_id = c.id WHERE o.id = ? AND o.buyer_id = ?', (order_id, current_user.id)).fetchone()

    if not order:
        flash('Order not found or you do not have permission to review it.', 'danger')
        conn.close()
        return redirect(url_for('buyer.view_my_orders'))

    if request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        conn.execute("INSERT INTO reviews (order_id, reviewer_id, reviewed_user_id, rating, comment) VALUES (?, ?, ?, ?, ?)", (order_id, current_user.id, order['farmer_id'], rating, comment))
        conn.commit()
        conn.close()
        flash('Thank you for your review!', 'success')
        return redirect(url_for('buyer.view_my_orders'))

    conn.close()
    return render_template('leave_review.html', order=order)