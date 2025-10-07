import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from models import User, Customer, Well, WaterTank
from utils import check_permissions

bp = Blueprint('admin', __name__, url_prefix='/admin')
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

@bp.route('/users', methods=['GET'])
@login_required
def users_admin():
    if not check_permissions(current_user.role, ['admin']):
        flash('Bạn không có quyền truy cập mục này', 'error')
        return redirect(url_for('dashboard.dashboard'))
    users = User.query.order_by(User.id).all()
    return render_template('admin/user.html', users=users)

@bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    # if not check_permissions(current_user.role, ['admin']):
    #     flash('Bạn không có quyền thực hiện hành động này', 'error')
    #     return redirect(url_for('admin.users_admin'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        role = (request.form.get('role') or '').strip()
        is_active = (request.form.get('active') == 'off')
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm_password') or ''

        errors = []
        if not username: errors.append('Tên đăng nhập là bắt buộc')
        if not password: errors.append('Mật khẩu là bắt buộc')
        if password != confirm: errors.append('Xác nhận mật khẩu không khớp')
        if role not in ['DATA_ENTRY', 'PLANT_MANAGER', 'ADMIN']:
            errors.append('Vai trò không hợp lệ')
        if db.session.query(User.id).filter(User.username == username).first():
            errors.append('Tên đăng nhập đã tồn tại')
        if email and db.session.query(User.id).filter(User.email == email).first():
            errors.append('Email đã tồn tại')

        if errors:
            for e in errors: flash(e, 'error')
            return render_template('new_page/user_new.html', form=request.form)

        try:
            user = User(
                username=username,
                full_name=full_name or None,
                email=email or None,
                role=role,
                is_active=is_active
            )
            if hasattr(user, 'set_password'):
                user.set_password(password)
            elif hasattr(user, 'password_hash'):
                user.password_hash = generate_password_hash(password)
            else:
                user.password = generate_password_hash(password)
            db.session.add(user)
            db.session.commit()
            flash('Tạo người dùng thành công', 'success')
            # return redirect(url_for('new_page.user_new'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi tạo người dùng: {str(e)}', 'error')
            return render_template('new_page/user_new.html', form=request.form)

    # GET
    # empty_user = User()
    return render_template('new_page/user_new.html')

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    # if not check_permissions(current_user.role, ['admin']):
    #     flash('Bạn không có quyền thực hiện hành động này', 'error')
    #     return redirect(url_for('admin.users_admin'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        role = (request.form.get('role') or '').strip()
        is_active = (request.form.get('active') == 'on')
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm_password') or ''

        errors = []
        if role not in ['DATA_ENTRY', 'PLANT_MANAGER', 'ADMIN']:
            errors.append('Vai trò không hợp lệ')
        if email and db.session.query(User.id).filter(User.email == email, User.id != user.id).first():
            errors.append('Email đã tồn tại')
        if password and password != confirm:
            errors.append('Xác nhận mật khẩu không khớp')

        if errors:
            for e in errors: flash(e, 'error')
            return render_template('admin/user.html', mode='edit', user=user, form=request.form)

        try:
            user.full_name = full_name or None
            user.email = email or None
            user.role = role
            user.is_active = is_active
            if password:
                if hasattr(user, 'set_password'):
                    user.set_password(password)
                elif hasattr(user, 'password_hash'):
                    user.password_hash = generate_password_hash(password)
                else:
                    user.password = generate_password_hash(password)
            db.session.commit()
            flash('Cập nhật người dùng thành công', 'success')
            return redirect(url_for('admin.admin'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi cập nhật: {str(e)}', 'error')
            return render_template('admin/user.html', mode='edit', user=user, form=request.form)

    # GET
    return render_template('edit_page/user_edit.html', mode='edit', user=user)

@bp.route('/users/<int:user_id>/delete', methods=['POST'], endpoint='delete_user')
@login_required
def delete_user(user_id):
    if not check_permissions(current_user.role, ['admin']):
        flash('Bạn không có quyền thực hiện hành động này', 'error')
        return redirect(url_for('admin.admin'))

    if current_user.id == user_id:
        flash('Không thể tự xóa tài khoản của chính bạn', 'error')
        return redirect(url_for('admin.users_admin'))

    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash('Đã xóa người dùng', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi xóa người dùng: {str(e)}', 'error')
    return redirect(url_for('admin.admin'))