import logging
from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import User, Customer, Well, WaterTank
from utils import check_permissions

bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

@bp.route('/admin')
@login_required
def admin():
    if not check_permissions(current_user.role, ['admin']):
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard.dashboard'))
    active_tab = request.args.get('active_tab') or session.pop('active_tab', 'users')
    users = User.query.all()
    customers = Customer.query.all()
    wells = Well.query.all()
    tanks = WaterTank.query.all()
    return render_template('admin/admin.html', users=users, customers=customers, active_tab=active_tab, wells=wells, tanks=tanks)