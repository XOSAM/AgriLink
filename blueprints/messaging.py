from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required

messaging_bp = Blueprint('messaging', __name__, url_prefix='/messaging')

@messaging_bp.route('/')
@login_required
def view_messages():
    # This is a placeholder. In a real app, you would fetch conversations from the database.
    return render_template('messages.html')

@messaging_bp.route('/send/<int:receiver_id>', methods=['GET', 'POST'])
@login_required
def send_message(receiver_id):
    crop_id = request.args.get('crop_id')
    demand_id = request.args.get('demand_id')

    if request.method == 'POST':
        # In a real app, you would save the message to the database here.
        flash('Message sent successfully!', 'success')
        if session.get('role') == 'farmer':
            return redirect(url_for('farmer.dashboard'))
        elif session.get('role') == 'buyer':
            return redirect(url_for('buyer.dashboard'))
        return redirect(url_for('main.homepage'))

    return render_template('send_message.html', receiver_id=receiver_id, crop_id=crop_id, demand_id=demand_id)