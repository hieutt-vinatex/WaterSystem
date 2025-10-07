from app import app
# Đăng ký các blueprint đã tách
from blueprints import auth_bp, dashboard_bp, data_entry_bp, reports_bp, charts_bp, customers_bp, admin_bp

# ...existing code...

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(data_entry_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(charts_bp)
app.register_blueprint(customers_bp)
app.register_blueprint(admin_bp)

# ---- Legacy endpoint aliases (giữ nguyên url_for('...') kiểu cũ) ----
def add_alias(rule: str, endpoint: str, real_endpoint: str, methods=None):
    # tránh đăng ký trùng
    if endpoint in app.view_functions:
        return
    view = app.view_functions[real_endpoint]
    app.add_url_rule(rule, endpoint=endpoint, view_func=view, methods=methods)

# Auth
add_alias('/login',  'login',  'auth.login')
add_alias('/logout', 'logout', 'auth.logout')

# Dashboard
add_alias('/', 'dashboard', 'dashboard.dashboard')

# Data entry
add_alias('/data-entry', 'data_entry', 'data_entry.data_entry')
add_alias('/submit-well-data',     'submit_well_data',        'data_entry.submit_well_data', methods=['POST'])
add_alias('/submit-clean-water-plant', 'submit_clean_water_plant', 'data_entry.submit_clean_water_plant', methods=['POST'])
add_alias('/submit-wastewater-plant',  'submit_wastewater_plant',  'data_entry.submit_wastewater_plant', methods=['POST'])
add_alias('/submit-tank-levels',   'submit_tank_levels', 'data_entry.submit_tank_levels', methods=['POST'])
add_alias('/submit-customer-readings', 'submit_customer_readings', 'data_entry.submit_customer_readings', methods=['POST'])

# Reports
add_alias('/reports',                        'reports',          'reports.reports')
add_alias('/generate-report/<report_type>',  'generate_report',  'reports.generate_report')
add_alias('/reports/export',                 'export_reports',   'reports.export_reports')
add_alias('/reports/export-csv',             'export_reports_csv','reports.export_reports_csv')

# Charts / APIs
add_alias('/chart-details/<chart_type>',     'chart_details',    'charts.chart_details')
add_alias('/api/chart-details/<chart_type>','api_chart_details','charts.api_chart_details')
add_alias('/api/dashboard-data',             'dashboard_data',   'charts.dashboard_data')

# Admin
add_alias('/admin', 'admin', 'admin.admin')

add_alias('/customers/new', 'new_customer', 'customers.new_customer', methods=['GET', 'POST'])
add_alias('/customers/<int:customer_id>/edit', 'edit_customer', 'customers.edit_customer', methods=['GET', 'POST'])
add_alias('/customers/<int:customer_id>/delete', 'delete_customer', 'customers.delete_customer', methods=['POST'])

add_alias('/users/new', 'new_user', 'admin.new_user', methods=['GET', 'POST'])
add_alias('/users/<int:user_id>/edit', 'edit_user', 'admin.edit_user', methods=['GET', 'POST'])
add_alias('/users/<int:user_id>/delete', 'delete_user', 'admin.delete_user', methods=['POST'])


# KPI API alias (giữ /api/kpi-data hoạt động dù chuyển blueprint)
add_alias('/api/kpi-data', 'kpi_data', 'charts.kpi_data')

# ...sau khi register blueprint và khai báo add_alias()...
add_alias('/api/clean-water-plant/exists', 'clean_water_plant_exists', 'data_entry.clean_water_plant_exists')

# ...existing code after registering blueprints and add_alias() helper...
add_alias('/api/exists/<model_key>', 'model_exists', 'data_entry.model_exists')

add_alias('/api/well-production/exists', 'well_production_exists', 'data_entry.well_production_exists')
add_alias('/api/wastewater-plant/exists', 'wastewater_plant_exists', 'data_entry.wastewater_plant_exists')
add_alias('/api/customer-readings/exists', 'customer_readings_exists', 'data_entry.customer_readings_exists')



# from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response, send_file
# from flask_login import login_user, logout_user, login_required, current_user
# from werkzeug.security import check_password_hash
# from app import app, db
# from models import *
# from utils import generate_daily_report, generate_monthly_report, check_permissions
# from datetime import datetime, date, timedelta
# import json
# import random
# import logging
# import io
# import csv
# from openpyxl import Workbook

# logger = logging.getLogger(__name__)

# @app.route('/')
# @login_required
# def dashboard():
#     return render_template('dashboard.html', user=current_user)

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']

#         user = User.query.filter_by(username=username).first()

#         if user and check_password_hash(user.password_hash, password):
#             login_user(user)
#             next_page = request.args.get('next')
#             return redirect(next_page) if next_page else redirect(url_for('dashboard'))
#         else:
#             flash('Invalid username or password', 'error')

#     return render_template('login.html')

# @app.route('/logout')
# @login_required
# def logout():
#     logout_user()
#     return redirect(url_for('login'))

# @app.route('/data-entry')
# @login_required
# def data_entry():
#     if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
#         flash('You do not have permission to access this page', 'error')
#         return redirect(url_for('dashboard'))

#     # Get data for forms
#     wells = Well.query.filter_by(is_active=True).all()
#     customers = Customer.query.filter_by(is_active=True).all()
#     tanks = WaterTank.query.all()

#     return render_template('data_entry.html', wells=wells, customers=customers, tanks=tanks, date=date)

# @app.route('/submit-well-data', methods=['POST'])
# @login_required
# def submit_well_data():
#     if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
#         flash('You do not have permission to perform this action', 'error')
#         return redirect(url_for('dashboard'))

#     try:
#         entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()

#         for well_id in request.form.getlist('well_ids'):
#             production = float(request.form.get(f'production_{well_id}', 0))

#             # Check if entry already exists
#             existing = WellProduction.query.filter_by(
#                 well_id=well_id, date=entry_date
#             ).first()

#             if existing:
#                 existing.production = production
#             else:
#                 well_production = WellProduction(
#                     well_id=well_id,
#                     date=entry_date,
#                     production=production,
#                     created_by=current_user.id
#                 )
#                 db.session.add(well_production)

#         db.session.commit()
#         flash('Well production data saved successfully', 'success')
#     except Exception as e:
#         db.session.rollback()
#         flash(f'Error saving data: {str(e)}', 'error')

#     return redirect(url_for('data_entry'))

# @app.route('/submit-clean-water-plant', methods=['POST'])
# @login_required
# def submit_clean_water_plant():
#     if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
#         flash('You do not have permission to perform this action', 'error')
#         return redirect(url_for('dashboard'))

#     try:
#         entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()

#         # Check if entry already exists
#         existing = CleanWaterPlant.query.filter_by(date=entry_date).first()

#         if existing:
#             existing.electricity = float(request.form.get('electricity', 0))
#             existing.pac_usage = float(request.form.get('pac_usage', 0))
#             existing.naoh_usage = float(request.form.get('naoh_usage', 0))
#             existing.polymer_usage = float(request.form.get('polymer_usage', 0))
#             existing.clean_water_output = float(request.form.get('clean_water_output', 0))
#             existing.raw_water_jasan = float(request.form.get('raw_water_jasan', 0))
#         else:
#             clean_water_plant = CleanWaterPlant(
#                 date=entry_date,
#                 electricity=float(request.form.get('electricity', 0)),
#                 pac_usage=float(request.form.get('pac_usage', 0)),
#                 naoh_usage=float(request.form.get('naoh_usage', 0)),
#                 polymer_usage=float(request.form.get('polymer_usage', 0)),
#                 clean_water_output=float(request.form.get('clean_water_output', 0)),
#                 raw_water_jasan=float(request.form.get('raw_water_jasan', 0)),
#                 created_by=current_user.id
#             )
#             db.session.add(clean_water_plant)

#         db.session.commit()
#         flash('Clean water plant data saved successfully', 'success')
#     except Exception as e:
#         db.session.rollback()
#         flash(f'Error saving data: {str(e)}', 'error')

#     return redirect(url_for('data_entry'))

# @app.route('/submit-wastewater-plant', methods=['POST'])
# @login_required
# def submit_wastewater_plant():
#     if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
#         flash('You do not have permission to perform this action', 'error')
#         return redirect(url_for('dashboard'))

#     try:
#         entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
#         plant_number = int(request.form['plant_number'])

#         # Check if entry already exists
#         existing = WastewaterPlant.query.filter_by(
#             date=entry_date, plant_number=plant_number
#         ).first()

#         if existing:
#             existing.wastewater_meter = float(request.form.get('wastewater_meter', 0))
#             existing.input_flow_tqt = float(request.form.get('input_flow_tqt', 0))
#             existing.output_flow_tqt = float(request.form.get('output_flow_tqt', 0))
#             existing.sludge_output = float(request.form.get('sludge_output', 0))
#             existing.electricity = float(request.form.get('electricity', 0))
#             existing.chemical_usage = float(request.form.get('chemical_usage', 0))
#         else:
#             wastewater_plant = WastewaterPlant(
#                 plant_number=plant_number,
#                 date=entry_date,
#                 wastewater_meter=float(request.form.get('wastewater_meter', 0)),
#                 input_flow_tqt=float(request.form.get('input_flow_tqt', 0)),
#                 output_flow_tqt=float(request.form.get('output_flow_tqt', 0)),
#                 sludge_output=float(request.form.get('sludge_output', 0)),
#                 electricity=float(request.form.get('electricity', 0)),
#                 chemical_usage=float(request.form.get('chemical_usage', 0)),
#                 created_by=current_user.id
#             )
#             db.session.add(wastewater_plant)

#         db.session.commit()
#         flash(f'Wastewater plant {plant_number} data saved successfully', 'success')
#     except Exception as e:
#         db.session.rollback()
#         flash(f'Error saving data: {str(e)}', 'error')

#     return redirect(url_for('data_entry'))

# @app.route('/submit-tank-levels', methods=['POST'])
# @login_required
# def submit_tank_levels():
#     if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
#         flash('You do not have permission to perform this action', 'error')
#         return redirect(url_for('dashboard'))

#     try:
#         entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()

#         for tank_id in request.form.getlist('tank_ids'):
#             level = float(request.form.get(f'level_{tank_id}', 0))

#             # Check if entry already exists
#             existing = WaterTankLevel.query.filter_by(
#                 tank_id=tank_id, date=entry_date
#             ).first()

#             if existing:
#                 existing.level = level
#             else:
#                 tank_level = WaterTankLevel(
#                     tank_id=tank_id,
#                     date=entry_date,
#                     level=level,
#                     created_by=current_user.id
#                 )
#                 db.session.add(tank_level)

#         db.session.commit()
#         flash('Mức nước bể chứa đã được lưu thành công', 'success')
#     except Exception as e:
#         db.session.rollback()
#         flash(f'Lỗi khi lưu dữ liệu: {str(e)}', 'error')

#     return redirect(url_for('data_entry'))

# @app.route('/submit-customer-readings', methods=['POST'])
# @login_required
# def submit_customer_readings():
#     if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
#         flash('You do not have permission to perform this action', 'error')
#         return redirect(url_for('dashboard'))

#     try:
#         entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()

#         for customer_id in request.form.getlist('customer_ids'):
#             clean_water_reading = float(request.form.get(f'clean_water_{customer_id}', 0))
#             wastewater_reading = request.form.get(f'wastewater_{customer_id}')

#             customer = Customer.query.get(customer_id)

#             # Calculate wastewater if not provided
#             if wastewater_reading:
#                 wastewater_reading = float(wastewater_reading)
#                 wastewater_calculated = None
#             else:
#                 wastewater_reading = None
#                 wastewater_calculated = clean_water_reading * customer.water_ratio

#             # Check if entry already exists
#             existing = CustomerReading.query.filter_by(
#                 customer_id=customer_id, date=entry_date
#             ).first()

#             if existing:
#                 existing.clean_water_reading = clean_water_reading
#                 existing.wastewater_reading = wastewater_reading
#                 existing.wastewater_calculated = wastewater_calculated
#             else:
#                 customer_reading = CustomerReading(
#                     customer_id=customer_id,
#                     date=entry_date,
#                     clean_water_reading=clean_water_reading,
#                     wastewater_reading=wastewater_reading,
#                     wastewater_calculated=wastewater_calculated,
#                     created_by=current_user.id
#                 )
#                 db.session.add(customer_reading)

#         db.session.commit()
#         flash('Customer readings saved successfully', 'success')
#     except Exception as e:
#         db.session.rollback()
#         flash(f'Error saving data: {str(e)}', 'error')

#     return redirect(url_for('data_entry'))

# @app.route('/reports')
# @login_required
# def reports():
#     if not check_permissions(current_user.role, ['accounting', 'plant_manager', 'leadership', 'admin']):
#         flash('You do not have permission to access this page', 'error')
#         return redirect(url_for('dashboard'))

#     return render_template('reports.html')

# def _xlsx_response(wb: Workbook, filename_base: str):
#     """
#     Serialize openpyxl Workbook to an in-memory XLSX and return send_file response.
#     """
#     buf = io.BytesIO()
#     wb.save(buf)
#     buf.seek(0)
#     return send_file(
#         buf,
#         as_attachment=True,
#         download_name=f"{filename_base}.xlsx",
#         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )

# def _build_sample_report_wb(report_type: str, start_dt: date, end_dt: date) -> Workbook:
#     """
#     TẠM THỜI: Tạo workbook mẫu có dữ liệu tối thiểu để đảm bảo mở được bằng Excel.
#     Bạn có thể thay phần fill data bằng truy vấn thực tế.
#     """
#     wb = Workbook()
#     ws = wb.active
#     ws.title = 'BaoCao'
#     ws.append(['Báo cáo', report_type])
#     ws.append(['Từ ngày', start_dt.strftime('%Y-%m-%d')])
#     ws.append(['Đến ngày', end_dt.strftime('%Y-%m-%d')])
#     ws.append([])

#     # Header dữ liệu ví dụ
#     ws.append(['Ngày', 'Mô tả', 'Giá trị'])
#     cur = start_dt
#     v = 1000
#     while cur <= end_dt:
#         ws.append([cur.strftime('%Y-%m-%d'), 'Dữ liệu mẫu', v])
#         v += 37
#         cur += timedelta(days=1)
#     return wb

# @app.route('/generate-report/<report_type>')
# @login_required
# def generate_report(report_type):
#     try:
#         start_date = request.args.get('start_date')
#         end_date = request.args.get('end_date')
#         format_type = request.args.get('format', 'excel')  # excel or pdf

#         # Parse ngày hợp lệ
#         if start_date and end_date:
#             start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
#             end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
#         else:
#             end_dt = date.today()
#             start_dt = end_dt - timedelta(days=30)

#         if format_type == 'excel':
#             # TẠO XLSX THẬT bằng openpyxl (KHÔNG dùng utils để tránh sai định dạng)
#             wb = _build_sample_report_wb(report_type, start_dt, end_dt)
#             filename = f"{report_type}_{date.today().strftime('%Y%m%d')}"
#             return _xlsx_response(wb, filename)

#         # Các định dạng khác (ví dụ pdf) vẫn dùng utils nếu bạn đã có sẵn
#         if report_type == 'daily_clean_water':
#             return generate_daily_report(start_date, end_date, format_type)
#         else:
#             return generate_monthly_report(report_type, start_date, end_date, format_type)

#     except Exception as e:
#         app.logger.exception("Error generating report")
#         flash(f'Error generating report: {str(e)}', 'error')
#         return redirect(url_for('reports'))

# @app.route('/admin')
# @login_required
# def admin():
#     if not check_permissions(current_user.role, ['admin']):
#         flash('You do not have permission to access this page', 'error')
#         return redirect(url_for('dashboard'))
#     # Allow explicit active_tab via query param (used by Cancel buttons)
#     active_tab = request.args.get('active_tab')
#     if not active_tab:
#         active_tab = session.pop('active_tab', 'users')
#     users = User.query.all()
#     customers = Customer.query.all()
#     wells = Well.query.all()
#     tanks = WaterTank.query.all()
#     active_tab=active_tab

#     return render_template('admin/admin.html', users=users, customers=customers, active_tab=active_tab, wells=wells, tanks=tanks)

# @app.route('/api/dashboard-data')
# @login_required
# def dashboard_data():
#     """API endpoint for dashboard charts data"""
#     try:
#         # Get date range from request
#         start_date_str = request.args.get('start_date')
#         end_date_str = request.args.get('end_date')

#         if start_date_str and end_date_str:
#             start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
#             end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
#         else:
#             days = int(request.args.get('days', 30))
#             end_date = date.today()
#             start_date = end_date - timedelta(days=days)

#         # Well production data
#         well_data = db.session.query(
#             WellProduction.date,
#             db.func.sum(WellProduction.production).label('total_production')
#         ).filter(
#             WellProduction.date >= start_date,
#             WellProduction.date <= end_date
#         ).group_by(WellProduction.date).all()

#         # Clean water production
#         clean_water_data = CleanWaterPlant.query.filter(
#             CleanWaterPlant.date >= start_date,
#             CleanWaterPlant.date <= end_date
#         ).all()

#         # Wastewater treatment
#         wastewater_data = db.session.query(
#             WastewaterPlant.date,
#             db.func.sum(WastewaterPlant.input_flow_tqt).label('total_input'),
#             db.func.sum(WastewaterPlant.output_flow_tqt).label('total_output')
#         ).filter(
#             WastewaterPlant.date >= start_date,
#             WastewaterPlant.date <= end_date
#         ).group_by(WastewaterPlant.date).all()

#         # Customer consumption
#         customer_data = db.session.query(
#             CustomerReading.date,
#             db.func.sum(CustomerReading.clean_water_reading).label('total_clean_water'),
#             db.func.sum(
#                 db.case(
#                     (CustomerReading.wastewater_reading.isnot(None), CustomerReading.wastewater_reading),
#                     else_=CustomerReading.wastewater_calculated
#                 )
#             ).label('total_wastewater')
#         ).filter(
#             CustomerReading.date >= start_date,
#             CustomerReading.date <= end_date
#         ).group_by(CustomerReading.date).all()

#         return jsonify({
#             'well_production': [{'date': str(d.date), 'production': float(d.total_production or 0)} for d in well_data],
#             'clean_water': [{'date': str(d.date), 'output': float(d.clean_water_output or 0)} for d in clean_water_data],
#             'wastewater': [{'date': str(d.date), 'input': float(d.total_input or 0), 'output': float(d.total_output or 0)} for d in wastewater_data],
#             'customer_consumption': [{'date': str(d.date), 'clean_water': float(d.total_clean_water or 0), 'wastewater': float(d.total_wastewater or 0)} for d in customer_data]
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/chart-details/<chart_type>')
# @login_required
# def chart_details(chart_type):
#     """Display detailed chart page for specific chart type"""

#     # Chart configuration mapping
#     chart_configs = {
#         'wells': {
#             'name': 'Sản lượng tổng các giếng khoan theo ngày',
#             'icon': 'fa-water',
#             'description': 'Theo dõi sản lượng nước từ 5 giếng khoan hoạt động (GK1, GK2, GK3, GK5, GK5-TT)'
#         },
#         'clean-water': {
#             'name': 'Sản lượng nước sạch từ nhà máy',
#             'icon': 'fa-tint',
#             'description': 'Bao gồm nước từ giếng khoan + nước thô Jasan với công suất 12,000 m³/ngày'
#         },
#         'wastewater': {
#             'name': 'Lưu lượng nước thải qua nhà máy xử lý',
#             'icon': 'fa-recycle',
#             'description': 'NMNT1: 12,000 m³/ngày, NMNT2: 8,000 m³/ngày'
#         },
#         'customers': {
#             'name': 'Tiêu thụ nước của khách hàng',
#             'icon': 'fa-users',
#             'description': 'Theo dõi tiêu thụ nước sạch và phát sinh nước thải của 50 khách hàng'
#         }
#     }

#     config = chart_configs.get(chart_type)
#     if not config:
#         flash('Loại biểu đồ không hợp lệ', 'error')
#         return redirect(url_for('dashboard'))

#     wells_list = []
#     if chart_type == 'wells':
#         wells_list = Well.query.filter_by(is_active=True).order_by(Well.code).all()
#     return render_template(
#         'chart_details.html',
#         chart_type=chart_type,
#         chart_type_name=config['name'],
#         chart_icon=config['icon'],
#         chart_description=config['description'],
#         wells=wells_list
#     )

# @app.route('/api/chart-details/<chart_type>')
# @login_required
# def api_chart_details(chart_type):
#     try:
#         days = request.args.get('days', 30, type=int)
#         start_date = request.args.get('start_date')
#         end_date = request.args.get('end_date')

#         if start_date and end_date:
#             start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
#             end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
#         else:
#             end_dt = datetime.now().date()
#             start_dt = end_dt - timedelta(days=days)

#         if chart_type == 'wells':
#             well_ids_param = request.args.get('well_ids')
#             well_ids = [int(x) for x in well_ids_param.split(',') if x.strip().isdigit()] if well_ids_param else None
#             data = get_well_production_range(start_dt, end_dt, well_ids)
#         elif chart_type == 'clean-water':
#             data = generate_clean_water_details(start_dt, end_dt)
#         elif chart_type == 'wastewater':
#             data = generate_wastewater_details(start_dt, end_dt)
#         elif chart_type == 'customers':
#             data = generate_customer_details(start_dt, end_dt)
#         else:
#             return jsonify({'error': 'Invalid chart type'}), 400

#         return jsonify(data)
#     except Exception as e:
#         logger.error(f"Error in chart details API: {str(e)}")
#         return jsonify({'error': 'Lỗi khi tải dữ liệu chi tiết'}), 500


# def get_well_production_range(start_date, end_date, well_ids=None):
#     """
#     Trả dữ liệu sản lượng theo ngày cho từng giếng + đường công suất danh định.
#     """
#     q = db.session.query(
#         WellProduction.date,
#         Well.id.label('well_id'),
#         Well.code.label('well_code'),
#         Well.capacity.label('capacity'),
#         db.func.sum(WellProduction.production).label('production')
#     ).join(Well).filter(
#         WellProduction.date >= start_date,
#         WellProduction.date <= end_date
#     )
#     if well_ids:
#         q = q.filter(Well.id.in_(well_ids))
#     q = q.group_by(
#         WellProduction.date, Well.id, Well.code, Well.capacity
#     ).order_by(WellProduction.date, Well.code)

#     rows = q.all()

#     dates_set = sorted({r.date for r in rows})
#     labels = [d.strftime('%d/%m') for d in dates_set]

#     # Map well_code -> {date: production}
#     wells_map = {}
#     capacities_map = {}
#     for r in rows:
#         wells_map.setdefault(r.well_code, {})[r.date] = float(r.production or 0)
#         # Lưu capacity giếng (nếu None thì 0)
#         capacities_map[r.well_code] = float(r.capacity or 0)

#     palette = [
#         'rgb(54,162,235)', 'rgb(255,99,132)', 'rgb(75,192,192)',
#         'rgb(255,206,86)', 'rgb(153,102,255)', 'rgb(255,159,64)'
#     ]

#     datasets = []
#     well_colors = {}

#     # Dataset sản lượng
#     for i, (well_code, date_dict) in enumerate(sorted(wells_map.items())):
#         color = palette[i % len(palette)]
#         well_colors[well_code] = color
#         datasets.append({
#             'label': well_code,
#             'data': [date_dict.get(d, 0) for d in dates_set],
#             'borderColor': color,
#             'backgroundColor': color.replace('rgb', 'rgba').replace(')', ',0.15)'),
#             'fill': False,
#             'tension': 0.3
#         })

#     # Dataset công suất (dashed)
#     for well_code, capacity in sorted(capacities_map.items()):
#         color = well_colors.get(well_code, 'rgb(100,100,100)')
#         datasets.append({
#             'label': f'{well_code} - Công suất',
#             'data': [capacity for _ in dates_set],
#             'borderColor': color,
#             'backgroundColor': 'rgba(0,0,0,0)',
#             'fill': False,
#             'tension': 0.0,
#             'borderDash': [6, 6],
#             'pointRadius': 0
#             # 'hidden': True  # bật dòng này nếu muốn mặc định ẩn các đường công suất
#         })

#     total_each_day = [sum(ds['data'][idx] for ds in datasets
#                           if 'Công suất' not in ds['label'])
#                       for idx in range(len(labels))]
#     summary = {
#         'total': sum(total_each_day),
#         'average': (sum(total_each_day) / len(total_each_day)) if total_each_day else 0,
#         'max': max(total_each_day) if total_each_day else 0,
#         'min': min([v for v in total_each_day if v > 0]) if any(total_each_day) else 0
#     }

#     table_data = []
#     for idx, d in enumerate(dates_set):
#         row = {'date': d.strftime('%d/%m/%Y')}
#         daily_total = 0
#         for ds in datasets:
#             if 'Công suất' in ds['label']:
#                 # Bỏ qua cột công suất trong bảng (nếu muốn hiển thị thì thêm vào)
#                 continue
#             v = ds['data'][idx]
#             row[ds['label']] = v
#             daily_total += v
#         row['total'] = daily_total
#         table_data.append(row)

#     return {
#         'chart_data': {
#             'labels': labels,
#             'datasets': datasets
#         },
#         'summary': summary,
#         'table_data': table_data
#     }


# def generate_well_production_details(start_date, end_date):
#     """Generate detailed well production data"""
#     dates = []
#     current_date = start_date
#     while current_date <= end_date:
#         dates.append(current_date)
#         current_date += timedelta(days=1)

#     chart_data = {
#         'labels': [d.strftime('%d/%m') for d in dates],
#         'datasets': [{
#             'label': 'Tổng sản lượng (m³)',
#             'data': [random.uniform(8000, 10000) for _ in dates],
#             'borderColor': 'rgb(54, 162, 235)',
#             'backgroundColor': 'rgba(54, 162, 235, 0.1)',
#             'fill': True,
#             'tension': 0.4
#         }]
#     }

#     # Calculate summary
#     total_production = sum(chart_data['datasets'][0]['data'])
#     summary = {
#         'total': total_production,
#         'average': total_production / len(dates),
#         'max': max(chart_data['datasets'][0]['data']),
#         'min': min(chart_data['datasets'][0]['data'])
#     }

#     # Generate table data
#     table_data = []
#     for i, date in enumerate(dates):
#         table_data.append({
#             'date': date.strftime('%d/%m/%Y'),
#             'production': chart_data['datasets'][0]['data'][i]
#         })

#     return {
#         'chart_data': chart_data,
#         'summary': summary,
#         'table_data': table_data
#     }

# def generate_clean_water_details(start_date, end_date):
#     """Generate detailed clean water production data"""
#     dates = []
#     current_date = start_date
#     while current_date <= end_date:
#         dates.append(current_date)
#         current_date += timedelta(days=1)

#     chart_data = {
#         'labels': [d.strftime('%d/%m') for d in dates],
#         'datasets': [{
#             'label': 'Nước sạch sản xuất (m³)',
#             'data': [random.uniform(9000, 12000) for _ in dates],
#             'backgroundColor': 'rgba(75, 192, 192, 0.6)',
#             'borderColor': 'rgb(75, 192, 192)',
#             'borderWidth': 1
#         }]
#     }

#     total_production = sum(chart_data['datasets'][0]['data'])
#     summary = {
#         'total': total_production,
#         'average': total_production / len(dates),
#         'max': max(chart_data['datasets'][0]['data']),
#         'min': min(chart_data['datasets'][0]['data'])
#     }

#     table_data = []
#     for i, date in enumerate(dates):
#         table_data.append({
#             'date': date.strftime('%d/%m/%Y'),
#             'clean_water_output': chart_data['datasets'][0]['data'][i]
#         })

#     return {
#         'chart_data': chart_data,
#         'summary': summary,
#         'table_data': table_data
#     }

# def generate_wastewater_details(start_date, end_date):
#     """Generate detailed wastewater data"""
#     dates = []
#     current_date = start_date
#     while current_date <= end_date:
#         dates.append(current_date)
#         current_date += timedelta(days=1)

#     input_data = [random.uniform(15000, 18000) for _ in dates]
#     output_data = [random.uniform(14000, 17000) for _ in dates]

#     chart_data = {
#         'labels': [d.strftime('%d/%m') for d in dates],
#         'datasets': [
#             {
#                 'label': 'Nước thải đầu vào (m³)',
#                 'data': input_data,
#                 'borderColor': 'rgb(255, 99, 132)',
#                 'backgroundColor': 'rgba(255, 99, 132, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             },
#             {
#                 'label': 'Nước thải đầu ra (m³)',
#                 'data': output_data,
#                 'borderColor': 'rgb(54, 162, 235)',
#                 'backgroundColor': 'rgba(54, 162, 235, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             }
#         ]
#     }

#     total_input = sum(input_data)
#     total_output = sum(output_data)

#     summary = {
#         'total': total_input + total_output,
#         'average': (total_input + total_output) / (2 * len(dates)),
#         'max': max(max(input_data), max(output_data)),
#         'min': min(min(input_data), min(output_data))
#     }

#     table_data = []
#     for i, date in enumerate(dates):
#         table_data.append({
#             'date': date.strftime('%d/%m/%Y'),
#             'input_flow': input_data[i],
#             'output_flow': output_data[i]
#         })

#     return {
#         'chart_data': chart_data,
#         'summary': summary,
#         'table_data': table_data
#     }

# def generate_customer_details(start_date, end_date):
#     """Generate detailed customer consumption data"""
#     dates = []
#     current_date = start_date
#     while current_date <= end_date:
#         dates.append(current_date)
#         current_date += timedelta(days=1)

#     clean_water_data = [random.uniform(8000, 11000) for _ in dates]
#     wastewater_data = [random.uniform(7000, 10000) for _ in dates]

#     chart_data = {
#         'labels': [d.strftime('%d/%m') for d in dates],
#         'datasets': [
#             {
#                 'label': 'Nước sạch tiêu thụ (m³)',
#                 'data': clean_water_data,
#                 'borderColor': 'rgb(54, 162, 235)',
#                 'backgroundColor': 'rgba(54, 162, 235, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             },
#             {
#                 'label': 'Nước thải phát sinh (m³)',
#                 'data': wastewater_data,
#                 'borderColor': 'rgb(255, 206, 86)',
#                 'backgroundColor': 'rgba(255, 206, 86, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             }
#         ]
#     }

#     total_clean = sum(clean_water_data)
#     total_waste = sum(wastewater_data)

#     summary = {
#         'total': total_clean + total_waste,
#         'average': (total_clean + total_waste) / (2 * len(dates)),
#         'max': max(max(clean_water_data), max(wastewater_data)),
#         'min': min(min(clean_water_data), min(wastewater_data))
#     }

#     table_data = []
#     for i, date in enumerate(dates):
#         table_data.append({
#             'date': date.strftime('%d/%m/%Y'),
#             'clean_water': clean_water_data[i],
#             'wastewater': wastewater_data[i]
#         })

#     return {
#         'chart_data': chart_data,
#         'summary': summary,
#         'table_data': table_data
#     }



# def get_wells_detail_data(start_date, end_date):
#     """Get detailed well production data"""
#     # Individual well production data
#     well_data = db.session.query(
#         WellProduction.date,
#         Well.code,
#         Well.name,
#         WellProduction.production
#     ).join(Well).filter(
#         WellProduction.date >= start_date,
#         WellProduction.date <= end_date,
#         Well.is_active == True
#     ).order_by(WellProduction.date, Well.code).all()

#     # Group data by date and well
#     wells_by_date = {}
#     well_names = {}

#     for item in well_data:
#         date_str = item.date.strftime('%d/%m')
#         if date_str not in wells_by_date:
#             wells_by_date[date_str] = {}
#         wells_by_date[date_str][item.code] = float(item.production or 0)
#         well_names[item.code] = item.name

#     # Prepare chart data
#     labels = sorted(wells_by_date.keys(), key=lambda x: datetime.strptime(x, '%d/%m'))
#     datasets = []

#     colors = ['rgb(54, 162, 235)', 'rgb(255, 99, 132)', 'rgb(75, 192, 192)', 
#               'rgb(255, 206, 86)', 'rgb(153, 102, 255)']

#     for i, well_code in enumerate(sorted(well_names.keys())):
#         data = [wells_by_date.get(date, {}).get(well_code, 0) for date in labels]
#         datasets.append({
#             'label': f'{well_code} - {well_names[well_code]}',
#             'data': data,
#             'borderColor': colors[i % len(colors)],
#             'backgroundColor': colors[i % len(colors)].replace('rgb', 'rgba').replace(')', ', 0.1)'),
#             'fill': False,
#             'tension': 0.4
#         })

#     chart_data = {
#         'labels': labels,
#         'datasets': datasets
#     }

#     # Summary statistics
#     total_production = sum([sum(day.values()) for day in wells_by_date.values()])
#     days_count = len(wells_by_date)

#     summary = {
#         'total': total_production,
#         'average': total_production / days_count if days_count > 0 else 0,
#         'max': max([sum(day.values()) for day in wells_by_date.values()]) if wells_by_date else 0,
#         'min': min([sum(day.values()) for day in wells_by_date.values() if sum(day.values()) > 0]) if wells_by_date else 0
#     }

#     # Table data
#     table_data = []
#     for date in labels:
#         date_obj = datetime.strptime(date, '%d/%m').replace(year=datetime.now().year)
#         row = {'date': date_obj.strftime('%d/%m/%Y')}
#         total = 0
#         for well_code in sorted(well_names.keys()):
#             value = wells_by_date.get(date, {}).get(well_code, 0)
#             row[well_code] = value
#             total += value
#         row['total'] = total
#         table_data.append(row)

#     return jsonify({
#         'chart_data': chart_data,
#         'summary': summary,
#         'table_data': table_data
#     })

# def get_clean_water_detail_data(start_date, end_date):
#     """Get detailed clean water production data"""
#     clean_water_data = CleanWaterPlant.query.filter(
#         CleanWaterPlant.date >= start_date,
#         CleanWaterPlant.date <= end_date
#     ).order_by(CleanWaterPlant.date).all()

#     # Prepare chart data
#     labels = [item.date.strftime('%d/%m') for item in clean_water_data]
#     clean_output = [float(item.clean_water_output or 0) for item in clean_water_data]
#     raw_jasan = [float(item.raw_water_jasan or 0) for item in clean_water_data]

#     chart_data = {
#         'labels': labels,
#         'datasets': [
#             {
#                 'label': 'Nước sạch sản xuất (m³)',
#                 'data': clean_output,
#                 'borderColor': 'rgb(75, 192, 192)',
#                 'backgroundColor': 'rgba(75, 192, 192, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             },
#             {
#                 'label': 'Nước thô Jasan (m³)',
#                 'data': raw_jasan,
#                 'borderColor': 'rgb(255, 159, 64)',
#                 'backgroundColor': 'rgba(255, 159, 64, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             }
#         ]
#     }

#     # Summary statistics
#     total_clean = sum(clean_output)
#     total_raw = sum(raw_jasan)
#     days_count = len(clean_output)

#     summary = {
#         'total': total_clean + total_raw,
#         'average': (total_clean + total_raw) / days_count if days_count > 0 else 0,
#         'max': max(clean_output + raw_jasan) if clean_output + raw_jasan else 0,
#         'min': min([x for x in clean_output + raw_jasan if x > 0]) if clean_output + raw_jasan else 0
#     }

#     # Table data
#     table_data = []
#     for item in clean_water_data:
#         table_data.append({
#             'date': item.date.strftime('%d/%m/%Y'),
#             'clean_water_output': float(item.clean_water_output or 0),
#             'raw_water_jasan': float(item.raw_water_jasan or 0),
#             'electricity': float(item.electricity or 0),
#             'pac_usage': float(item.pac_usage or 0),
#             'naoh_usage': float(item.naoh_usage or 0),
#             'polymer_usage': float(item.polymer_usage or 0)
#         })

#     return jsonify({
#         'chart_data': chart_data,
#         'summary': summary,
#         'table_data': table_data
#     })

# def get_wastewater_detail_data(start_date, end_date):
#     """Get detailed wastewater treatment data"""
#     wastewater_data = db.session.query(
#         WastewaterPlant.date,
#         WastewaterPlant.plant_number,
#         WastewaterPlant.input_flow_tqt,
#         WastewaterPlant.output_flow_tqt,
#         WastewaterPlant.wastewater_meter,
#         WastewaterPlant.sludge_output,
#         WastewaterPlant.electricity,
#         WastewaterPlant.chemical_usage
#     ).filter(
#         WastewaterPlant.date >= start_date,
#         WastewaterPlant.date <= end_date
#     ).order_by(WastewaterPlant.date, WastewaterPlant.plant_number).all()

#     # Group data by date and plant
#     plants_by_date = {}

#     for item in wastewater_data:
#         date_str = item.date.strftime('%d/%m')
#         if date_str not in plants_by_date:
#             plants_by_date[date_str] = {'plant1_input': 0, 'plant1_output': 0, 
#                                        'plant2_input': 0, 'plant2_output': 0}

#         if item.plant_number == 1:
#             plants_by_date[date_str]['plant1_input'] = float(item.input_flow_tqt or 0)
#             plants_by_date[date_str]['plant1_output'] = float(item.output_flow_tqt or 0)
#         else:
#             plants_by_date[date_str]['plant2_input'] = float(item.input_flow_tqt or 0)
#             plants_by_date[date_str]['plant2_output'] = float(item.output_flow_tqt or 0)

#     # Prepare chart data
#     labels = sorted(plants_by_date.keys(), key=lambda x: datetime.strptime(x, '%d/%m'))

#     chart_data = {
#         'labels': labels,
#         'datasets': [
#             {
#                 'label': 'NMNT1 - Đầu vào (m³)',
#                 'data': [plants_by_date[date]['plant1_input'] for date in labels],
#                 'borderColor': 'rgb(255, 99, 132)',
#                 'backgroundColor': 'rgba(255, 99, 132, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             },
#             {
#                 'label': 'NMNT1 - Đầu ra (m³)',
#                 'data': [plants_by_date[date]['plant1_output'] for date in labels],
#                 'borderColor': 'rgb(54, 162, 235)',
#                 'backgroundColor': 'rgba(54, 162, 235, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             },
#             {
#                 'label': 'NMNT2 - Đầu vào (m³)',
#                 'data': [plants_by_date[date]['plant2_input'] for date in labels],
#                 'borderColor': 'rgb(255, 206, 86)',
#                 'backgroundColor': 'rgba(255, 206, 86, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             },
#             {
#                 'label': 'NMNT2 - Đầu ra (m³)',
#                 'data': [plants_by_date[date]['plant2_output'] for date in labels],
#                 'borderColor': 'rgb(75, 192, 192)',
#                 'backgroundColor': 'rgba(75, 192, 192, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             }
#         ]
#     }

#     # Summary statistics
#     total_input = sum([day['plant1_input'] + day['plant2_input'] for day in plants_by_date.values()])
#     total_output = sum([day['plant1_output'] + day['plant2_output'] for day in plants_by_date.values()])
#     days_count = len(plants_by_date)

#     summary = {
#         'total': total_input + total_output,
#         'average': (total_input + total_output) / days_count if days_count > 0 else 0,
#         'max': max([day['plant1_input'] + day['plant2_input'] + day['plant1_output'] + day['plant2_output'] 
#                    for day in plants_by_date.values()]) if plants_by_date else 0,
#         'min': 0
#     }

#     # Table data
#     table_data = []
#     for item in wastewater_data:
#         table_data.append({
#             'date': item.date.strftime('%d/%m/%Y'),
#             'plant_number': item.plant_number,
#             'input_flow': float(item.input_flow_tqt or 0),
#             'output_flow': float(item.output_flow_tqt or 0),
#             'wastewater_meter': float(item.wastewater_meter or 0),
#             'sludge_output': float(item.sludge_output or 0),
#             'electricity': float(item.electricity or 0),
#             'chemical_usage': float(item.chemical_usage or 0)
#         })

#     return jsonify({
#         'chart_data': chart_data,
#         'summary': summary,
#         'table_data': table_data
#     })

# def get_customers_detail_data(start_date, end_date):
#     """Get detailed customer consumption data"""
#     # Customer consumption data - using correct field names from model
#     customer_data = db.session.query(
#         CustomerReading.date,
#         db.func.sum(CustomerReading.clean_water_reading).label('clean_water'),
#         db.func.sum(
#             db.case(
#                 (CustomerReading.wastewater_reading.isnot(None), CustomerReading.wastewater_reading),
#                 else_=CustomerReading.wastewater_calculated
#             )
#         ).label('wastewater')
#     ).filter(
#         CustomerReading.date >= start_date,
#         CustomerReading.date <= end_date
#     ).group_by(CustomerReading.date).order_by(CustomerReading.date).all()

#     # Prepare chart data
#     labels = [item.date.strftime('%d/%m') for item in customer_data]
#     clean_water_values = [float(item.clean_water or 0) for item in customer_data]
#     wastewater_values = [float(item.wastewater or 0) for item in customer_data]

#     chart_data = {
#         'labels': labels,
#         'datasets': [
#             {
#                 'label': 'Nước sạch tiêu thụ (m³)',
#                 'data': clean_water_values,
#                 'borderColor': 'rgb(54, 162, 235)',
#                 'backgroundColor': 'rgba(54, 162, 235, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             },
#             {
#                 'label': 'Nước thải phát sinh (m³)',
#                 'data': wastewater_values,
#                 'borderColor': 'rgb(255, 206, 86)',
#                 'backgroundColor': 'rgba(255, 206, 86, 0.1)',
#                 'fill': False,
#                 'tension': 0.4
#             }
#         ]
#     }

#     # Summary statistics
#     total_clean = sum(clean_water_values)
#     total_wastewater = sum(wastewater_values)
#     days_count = len(clean_water_values)

#     summary = {
#         'total': total_clean + total_wastewater,
#         'average': (total_clean + total_wastewater) / days_count if days_count > 0 else 0,
#         'max': max(clean_water_values + wastewater_values) if clean_water_values + wastewater_values else 0,
#         'min': min([x for x in clean_water_values + wastewater_values if x > 0]) if clean_water_values + wastewater_values else 0
#     }

#     # Table data
#     table_data = []
#     for item in customer_data:
#         table_data.append({
#             'date': item.date.strftime('%d/%m/%Y'),
#             'clean_water': float(item.clean_water or 0),
#             'wastewater': float(item.wastewater or 0),
#             'total': float(item.clean_water or 0) + float(item.wastewater or 0)
#         })

#     return jsonify({
#         'chart_data': chart_data,
#         'summary': summary,
#         'table_data': table_data
#     })

# @app.route('/api/kpi-data')
# @login_required
# def kpi_data():
#     """API endpoint for KPI dashboard data"""
#     try:
#         today = date.today()
#         month_start = today.replace(day=1)

#         # Today's production
#         today_well_production = db.session.query(
#             db.func.sum(WellProduction.production)
#         ).filter(WellProduction.date == today).scalar() or 0

#         # Monthly production
#         month_well_production = db.session.query(
#             db.func.sum(WellProduction.production)
#         ).filter(WellProduction.date >= month_start).scalar() or 0

#         # Clean water output today
#         today_clean_water = CleanWaterPlant.query.filter_by(date=today).first()
#         today_clean_output = today_clean_water.clean_water_output if today_clean_water else 0

#         # Wastewater treatment today
#         today_wastewater = db.session.query(
#             db.func.sum(WastewaterPlant.input_flow_tqt)
#         ).filter(WastewaterPlant.date == today).scalar() or 0

#         # Active customers
#         active_customers = Customer.query.filter_by(is_active=True).count()

#         return jsonify({
#             'today_well_production': float(today_well_production),
#             'month_well_production': float(month_well_production),
#             'today_clean_water': float(today_clean_output),
#             'today_wastewater': float(today_wastewater),
#             'active_customers': active_customers
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


# @app.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
# @login_required
# def edit_customer(customer_id):
#     customer = Customer.query.get_or_404(customer_id)

#     if request.method == 'POST':
#         # Lấy dữ liệu từ form
#         customer.company_name = request.form.get('company_name', customer.company_name)
#         customer.contact_person = request.form.get('contact_person', customer.contact_person)
#         customer.phone = request.form.get('phone', customer.phone)
#         customer.email = request.form.get('email', customer.email)
#         customer.address = request.form.get('address', customer.address)
#         customer.notes = request.form.get('notes', customer.notes)
#         customer.daily_reading = True if request.form.get('daily_reading') == 'on' else False
#         customer.is_active = True if request.form.get('is_active') == 'on' else False
#         customer.location = request.form.get('location', customer.location)
#         customer.water_ratio = request.form.get('water_ratio', '').strip()
#         db.session.add(customer)
#         db.session.commit()
#         flash('Cập nhật khách hàng thành công.', 'success')
#         session['active_tab'] = 'customers'
#         return redirect(url_for('admin'))
#     # GET
#     # store previous active tab so template Cancel can return there
#     session['prev_active_tab'] = session.get('active_tab', 'customers')
#     return render_template('edit_page/customer_edit.html', customer=customer)


# @app.route('/customers/new', methods=['GET', 'POST'])
# @login_required
# def new_customer():
#     if request.method == 'POST':
#         company_name = request.form.get('company_name', '').strip()
#         contact_person = request.form.get('contact_person', '').strip()
#         phone = request.form.get('phone', '').strip()
#         email = request.form.get('email', '').strip()
#         address = request.form.get('address', '').strip()
#         notes = request.form.get('notes', '').strip()
#         location = request.form.get('location').strip()
#         water_ratio_str = request.form.get('water_ratio', '').strip()
#         try:
#             water_ratio = float(water_ratio_str) if water_ratio_str != '' else None
#         except ValueError:
#             water_ratio = None
#         daily_reading = True if request.form.get('daily_reading') == 'on' else False
#         is_active = True if request.form.get('is_active') == 'on' else False

#         all_empty = not any([
#             company_name, contact_person, phone, email, address,
#             notes, water_ratio_str, daily_reading, is_active, location
#         ])

#         if all_empty:
#             flash('Vui lòng nhập ít nhất một trường thông tin khách hàng.', 'danger')
#             temp = Customer(
#                 company_name=company_name,
#                 contact_person=contact_person,
#                 phone=phone,
#                 email=email,
#                 address=address,
#                 notes=notes if hasattr(Customer, 'notes') else None,
#                 location=location,
#                 water_ratio=water_ratio or 0,
#                 daily_reading=daily_reading,
#                 is_active=is_active
#             )
#             return render_template('new_page/customer_new.html', customer=temp)

#         if not company_name:
#             flash('Tên công ty là bắt buộc.', 'danger')
#             temp = Customer(
#                 company_name='',
#                 contact_person=contact_person,
#                 phone=phone,
#                 email=email,
#                 address=address,
#                 notes=notes if hasattr(Customer, 'notes') else None,
#                 location=location,
#                 water_ratio=water_ratio or 0,
#                 daily_reading=daily_reading,
#                 is_active=is_active
#             )
#             return render_template('new_page/customer_new.html', customer=temp)

#         customer = Customer(
#             company_name=company_name,
#             contact_person=contact_person or None,
#             phone=phone or None,
#             email=email or None,
#             address=address or None,
#             notes=notes or None,
#             location=location,
#             water_ratio=water_ratio or 0,
#             daily_reading=daily_reading,
#             is_active=is_active
#         )
#         db.session.add(customer)
#         db.session.commit()
#         flash('Thêm khách hàng thành công.', 'success')
#         session['active_tab'] = 'customers'
#         session['prev_active_tab'] = session.get('prev_active_tab', 'customers')
#         return redirect(url_for('admin'))
 
#     empty_customer = Customer()
#     # store previous active tab so template Cancel can return there
#     session['prev_active_tab'] = session.get('active_tab', 'customers')
#     return render_template('new_page/customer_new.html', customer=empty_customer)


# @app.route('/customers/<int:customer_id>/delete', methods=['POST'])
# @login_required
# def delete_customer(customer_id):
#     # Kiểm tra phân quyền (chỉ admin hoặc data entry có thể xóa tuỳ logic của project)
#     if not check_permissions(current_user.role, ['admin']):
#         flash('Không có quyền xóa khách hàng.', 'danger')
#         return redirect(url_for('admin') + '#customers')
#     customer = Customer.query.get_or_404(customer_id)
#     try:
#         # Xóa các CustomerReading liên quan trước (bulk delete)
#         CustomerReading.query.filter_by(customer_id=customer.id).delete()
#         db.session.delete(customer)
#         db.session.commit()
#         flash(f"Đã xóa khách hàng #{customer.id} - {customer.company_name}.", 'success')
#     except Exception as e:
#         db.session.rollback()
#         logger.exception("Error deleting customer")
#         flash('Xóa khách hàng thất bại.', 'danger')

#     # đảm bảo admin mở tab customers
#     session['active_tab'] = 'customers'
#     return redirect(url_for('admin') + '#customers')

# Ví dụ export Excel chuẩn
# @app.route('/reports/export', methods=['GET'])
# @login_required
# def export_reports():
#     # TODO: thay data bằng dữ liệu thực tế của bạn
#     headers = ['Ngày', 'Giếng', 'Sản lượng (m³)']
#     rows = [
#         ['2025-10-01', 'W1', 1234],
#         ['2025-10-01', 'W2', 1456],
#     ]

#     wb = Workbook()
#     ws = wb.active
#     ws.title = 'BaoCao'
#     ws.append(headers)
#     for r in rows:
#         ws.append(r)

#     buffer = io.BytesIO()
#     wb.save(buffer)
#     buffer.seek(0)  # QUAN TRỌNG

#     filename = f"bao_cao_{date.today().strftime('%Y%m%d')}.xlsx"
#     return send_file(
#         buffer,
#         as_attachment=True,
#         download_name=filename,  # thay cho attachment_filename
#         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )

# @app.route('/reports/export-csv', methods=['GET'])
# @login_required
# def export_reports_csv():
#     output = io.StringIO()
#     writer = csv.writer(output)
#     writer.writerow(['Ngày', 'Giếng', 'Sản lượng (m³)'])
#     writer.writerow(['2025-10-01', 'W1', 1234])

#     data = output.getvalue()
#     resp = make_response(data.encode('utf-8-sig'))  # BOM để Excel mở đúng UTF-8
#     resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
#     resp.headers['Content-Disposition'] = 'attachment; filename=bao_cao.csv'
#     return resp