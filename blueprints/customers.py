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
        # Lấy dữ liệu form
        company_name = (request.form.get('company_name') or '').strip()
        contact_person = (request.form.get('contact_person') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        email = (request.form.get('email') or '').strip()
        address = (request.form.get('address') or '').strip()
        notes = (request.form.get('notes') or '').strip()
        location = (request.form.get('location') or '').strip()
        daily_reading = (request.form.get('daily_reading') == 'on')
        is_active = (request.form.get('is_active') == 'on')
        water_ratio_str = (request.form.get('water_ratio') or '').strip()
        try:
            water_ratio = float(water_ratio_str) if water_ratio_str != '' else None
        except ValueError:
            water_ratio = None  # không chặn lỗi, coi như để trống

        # Validate duy nhất: tên công ty là bắt buộc
        if not company_name:
            flash('Tên công ty là bắt buộc.', 'danger')
            # Gán tạm vào object để giữ lại dữ liệu hiển thị, không commit
            customer.company_name = company_name
            customer.contact_person = contact_person or None
            customer.phone = phone or None
            customer.email = email or None
            customer.address = address or None
            if hasattr(Customer, 'notes'):
                customer.notes = notes or None
            customer.location = location or None
            customer.daily_reading = daily_reading
            customer.is_active = is_active
            if water_ratio is not None:
                customer.water_ratio = water_ratio
            return render_template('edit_page/customer_edit.html', customer=customer)

        # Hợp lệ: cập nhật và lưu
        customer.company_name = company_name
        customer.contact_person = contact_person or None
        customer.phone = phone or None
        customer.email = email or None
        customer.address = address or None
        if hasattr(Customer, 'notes'):
            customer.notes = notes or None
        customer.location = location or None
        customer.daily_reading = daily_reading
        customer.is_active = is_active
        if water_ratio is not None:
            customer.water_ratio = water_ratio
        db.session.add(customer)
        db.session.commit()
        flash('Cập nhật khách hàng thành công.', 'success')
        session['active_tab'] = 'customers'
        return redirect(url_for('admin.admin'))

    session['prev_active_tab'] = session.get('active_tab', 'customers')
    return render_template('edit_page/customer_edit.html', customer=customer)


@bp.route('/customers/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    if request.method == 'POST':
        company_name = (request.form.get('company_name') or '').strip()
        contact_person = (request.form.get('contact_person') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        email = (request.form.get('email') or '').strip()
        address = (request.form.get('address') or '').strip()
        notes = (request.form.get('notes') or '').strip()
        location = (request.form.get('location') or '').strip()
        water_ratio_str = (request.form.get('water_ratio') or '').strip()
        try:
            water_ratio = float(water_ratio_str) if water_ratio_str != '' else None
        except ValueError:
            water_ratio = None
        daily_reading = (request.form.get('daily_reading') == 'on')
        is_active = (request.form.get('is_active') == 'on')

        # Chỉ bắt buộc tên công ty
        if not company_name:
            flash('Tên công ty là bắt buộc.', 'danger')
            temp = Customer(
                company_name=company_name,
                contact_person=contact_person or None,
                phone=phone or None,
                email=email or None,
                address=address or None,
                notes=(notes or None) if hasattr(Customer, 'notes') else None,
                location=location or None,
                water_ratio=(water_ratio if water_ratio is not None else 0),
                daily_reading=daily_reading,
                is_active=is_active
            )
            return render_template('new_page/customer_new.html', customer=temp)

        # Tạo mới
        customer = Customer(
            company_name=company_name,
            contact_person=contact_person or None,
            phone=phone or None,
            email=email or None,
            address=address or None,
            notes=(notes or None) if hasattr(Customer, 'notes') else None,
            location=location or None,
            water_ratio=(water_ratio if water_ratio is not None else 0),
            daily_reading=daily_reading,
            is_active=is_active
        )
        db.session.add(customer)
        db.session.commit()
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