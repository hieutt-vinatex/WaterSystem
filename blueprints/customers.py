import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app import db
from models import Customer, CustomerReading
from utils import check_permissions

bp = Blueprint('customers', __name__)
logger = logging.getLogger(__name__)

@bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if request.method == 'POST':
        customer.company_name = request.form.get('company_name', customer.company_name)
        customer.contact_person = request.form.get('contact_person', customer.contact_person)
        customer.phone = request.form.get('phone', customer.phone)
        customer.email = request.form.get('email', customer.email)
        customer.address = request.form.get('address', customer.address)
        customer.notes = request.form.get('notes', customer.notes)
        customer.daily_reading = True if request.form.get('daily_reading') == 'on' else False
        customer.is_active = True if request.form.get('is_active') == 'on' else False
        customer.location = request.form.get('location', customer.location)
        customer.water_ratio = request.form.get('water_ratio', '').strip()
        db.session.add(customer); db.session.commit()
        flash('Cập nhật khách hàng thành công.', 'success')
        session['active_tab'] = 'customers'
        return redirect(url_for('admin.admin'))
    session['prev_active_tab'] = session.get('active_tab', 'customers')
    return render_template('edit_page/customer_edit.html', customer=customer)

@bp.route('/customers/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()
        location = request.form.get('location').strip()
        water_ratio_str = request.form.get('water_ratio', '').strip()
        try:
            water_ratio = float(water_ratio_str) if water_ratio_str != '' else None
        except ValueError:
            water_ratio = None
        daily_reading = True if request.form.get('daily_reading') == 'on' else False
        is_active = True if request.form.get('is_active') == 'on' else False
        all_empty = not any([company_name, contact_person, phone, email, address, notes, water_ratio_str, daily_reading, is_active, location])
        if all_empty:
            flash('Vui lòng nhập ít nhất một trường thông tin khách hàng.', 'danger')
            temp = Customer(company_name=company_name, contact_person=contact_person, phone=phone, email=email,
                            address=address, notes=notes if hasattr(Customer, 'notes') else None,
                            location=location, water_ratio=water_ratio or 0, daily_reading=daily_reading, is_active=is_active)
            return render_template('new_page/customer_new.html', customer=temp)
        if not company_name:
            flash('Tên công ty là bắt buộc.', 'danger')
            temp = Customer(company_name='', contact_person=contact_person, phone=phone, email=email,
                            address=address, notes=notes if hasattr(Customer, 'notes') else None,
                            location=location, water_ratio=water_ratio or 0, daily_reading=daily_reading, is_active=is_active)
            return render_template('new_page/customer_new.html', customer=temp)
        customer = Customer(company_name=company_name, contact_person=contact_person or None, phone=phone or None,
                            email=email or None, address=address or None, notes=notes or None, location=location,
                            water_ratio=water_ratio or 0, daily_reading=daily_reading, is_active=is_active)
        db.session.add(customer); db.session.commit()
        flash('Thêm khách hàng thành công.', 'success')
        session['active_tab'] = 'customers'
        session['prev_active_tab'] = session.get('prev_active_tab', 'customers')
        return redirect(url_for('admin.admin'))
    empty_customer = Customer()
    session['prev_active_tab'] = session.get('active_tab', 'customers')
    return render_template('new_page/customer_new.html', customer=empty_customer)

@bp.route('/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
def delete_customer(customer_id):
    if not check_permissions(current_user.role, ['admin']):
        flash('Không có quyền xóa khách hàng.', 'danger')
        return redirect(url_for('admin.admin') + '#customers')
    customer = Customer.query.get_or_404(customer_id)
    try:
        CustomerReading.query.filter_by(customer_id=customer.id).delete()
        db.session.delete(customer); db.session.commit()
        flash(f"Đã xóa khách hàng #{customer.id} - {customer.company_name}.", 'success')
    except Exception:
        db.session.rollback()
        flash('Xóa khách hàng thất bại.', 'danger')
    session['active_tab'] = 'customers'
    return redirect(url_for('admin.admin') + '#customers')