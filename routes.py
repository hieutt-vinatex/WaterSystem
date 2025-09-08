from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app import app, db
from models import *
from utils import generate_daily_report, generate_monthly_report, check_permissions
from datetime import datetime, date, timedelta
import json

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/data-entry')
@login_required
def data_entry():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))
    
    # Get data for forms
    wells = Well.query.filter_by(is_active=True).all()
    customers = Customer.query.filter_by(is_active=True).all()
    tanks = WaterTank.query.all()
    
    return render_template('data_entry.html', wells=wells, customers=customers, tanks=tanks, date=date)

@app.route('/submit-well-data', methods=['POST'])
@login_required
def submit_well_data():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        
        for well_id in request.form.getlist('well_ids'):
            production = float(request.form.get(f'production_{well_id}', 0))
            
            # Check if entry already exists
            existing = WellProduction.query.filter_by(
                well_id=well_id, date=entry_date
            ).first()
            
            if existing:
                existing.production = production
            else:
                well_production = WellProduction(
                    well_id=well_id,
                    date=entry_date,
                    production=production,
                    created_by=current_user.id
                )
                db.session.add(well_production)
        
        db.session.commit()
        flash('Well production data saved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    
    return redirect(url_for('data_entry'))

@app.route('/submit-clean-water-plant', methods=['POST'])
@login_required
def submit_clean_water_plant():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        
        # Check if entry already exists
        existing = CleanWaterPlant.query.filter_by(date=entry_date).first()
        
        if existing:
            existing.electricity = float(request.form.get('electricity', 0))
            existing.pac_usage = float(request.form.get('pac_usage', 0))
            existing.naoh_usage = float(request.form.get('naoh_usage', 0))
            existing.polymer_usage = float(request.form.get('polymer_usage', 0))
            existing.clean_water_output = float(request.form.get('clean_water_output', 0))
            existing.raw_water_jasan = float(request.form.get('raw_water_jasan', 0))
        else:
            clean_water_plant = CleanWaterPlant(
                date=entry_date,
                electricity=float(request.form.get('electricity', 0)),
                pac_usage=float(request.form.get('pac_usage', 0)),
                naoh_usage=float(request.form.get('naoh_usage', 0)),
                polymer_usage=float(request.form.get('polymer_usage', 0)),
                clean_water_output=float(request.form.get('clean_water_output', 0)),
                raw_water_jasan=float(request.form.get('raw_water_jasan', 0)),
                created_by=current_user.id
            )
            db.session.add(clean_water_plant)
        
        db.session.commit()
        flash('Clean water plant data saved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    
    return redirect(url_for('data_entry'))

@app.route('/submit-wastewater-plant', methods=['POST'])
@login_required
def submit_wastewater_plant():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        plant_number = int(request.form['plant_number'])
        
        # Check if entry already exists
        existing = WastewaterPlant.query.filter_by(
            date=entry_date, plant_number=plant_number
        ).first()
        
        if existing:
            existing.wastewater_meter = float(request.form.get('wastewater_meter', 0))
            existing.input_flow_tqt = float(request.form.get('input_flow_tqt', 0))
            existing.output_flow_tqt = float(request.form.get('output_flow_tqt', 0))
            existing.sludge_output = float(request.form.get('sludge_output', 0))
            existing.electricity = float(request.form.get('electricity', 0))
            existing.chemical_usage = float(request.form.get('chemical_usage', 0))
        else:
            wastewater_plant = WastewaterPlant(
                plant_number=plant_number,
                date=entry_date,
                wastewater_meter=float(request.form.get('wastewater_meter', 0)),
                input_flow_tqt=float(request.form.get('input_flow_tqt', 0)),
                output_flow_tqt=float(request.form.get('output_flow_tqt', 0)),
                sludge_output=float(request.form.get('sludge_output', 0)),
                electricity=float(request.form.get('electricity', 0)),
                chemical_usage=float(request.form.get('chemical_usage', 0)),
                created_by=current_user.id
            )
            db.session.add(wastewater_plant)
        
        db.session.commit()
        flash(f'Wastewater plant {plant_number} data saved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    
    return redirect(url_for('data_entry'))

@app.route('/submit-customer-readings', methods=['POST'])
@login_required
def submit_customer_readings():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        
        for customer_id in request.form.getlist('customer_ids'):
            clean_water_reading = float(request.form.get(f'clean_water_{customer_id}', 0))
            wastewater_reading = request.form.get(f'wastewater_{customer_id}')
            
            customer = Customer.query.get(customer_id)
            
            # Calculate wastewater if not provided
            if wastewater_reading:
                wastewater_reading = float(wastewater_reading)
                wastewater_calculated = None
            else:
                wastewater_reading = None
                wastewater_calculated = clean_water_reading * customer.water_ratio
            
            # Check if entry already exists
            existing = CustomerReading.query.filter_by(
                customer_id=customer_id, date=entry_date
            ).first()
            
            if existing:
                existing.clean_water_reading = clean_water_reading
                existing.wastewater_reading = wastewater_reading
                existing.wastewater_calculated = wastewater_calculated
            else:
                customer_reading = CustomerReading(
                    customer_id=customer_id,
                    date=entry_date,
                    clean_water_reading=clean_water_reading,
                    wastewater_reading=wastewater_reading,
                    wastewater_calculated=wastewater_calculated,
                    created_by=current_user.id
                )
                db.session.add(customer_reading)
        
        db.session.commit()
        flash('Customer readings saved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    
    return redirect(url_for('data_entry'))

@app.route('/reports')
@login_required
def reports():
    if not check_permissions(current_user.role, ['accounting', 'plant_manager', 'leadership', 'admin']):
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('reports.html')

@app.route('/generate-report/<report_type>')
@login_required
def generate_report(report_type):
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        format_type = request.args.get('format', 'excel')  # excel or pdf
        
        if report_type == 'daily_clean_water':
            response = generate_daily_report(start_date, end_date, format_type)
        else:
            response = generate_monthly_report(report_type, start_date, end_date, format_type)
        
        return response
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/admin')
@login_required
def admin():
    if not check_permissions(current_user.role, ['admin']):
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    customers = Customer.query.all()
    wells = Well.query.all()
    tanks = WaterTank.query.all()
    
    return render_template('admin.html', users=users, customers=customers, wells=wells, tanks=tanks)

@app.route('/api/dashboard-data')
@login_required
def dashboard_data():
    """API endpoint for dashboard charts data"""
    try:
        # Get date range from request
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            days = int(request.args.get('days', 30))
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
        
        # Well production data
        well_data = db.session.query(
            WellProduction.date,
            db.func.sum(WellProduction.production).label('total_production')
        ).filter(
            WellProduction.date >= start_date,
            WellProduction.date <= end_date
        ).group_by(WellProduction.date).all()
        
        # Clean water production
        clean_water_data = CleanWaterPlant.query.filter(
            CleanWaterPlant.date >= start_date,
            CleanWaterPlant.date <= end_date
        ).all()
        
        # Wastewater treatment
        wastewater_data = db.session.query(
            WastewaterPlant.date,
            db.func.sum(WastewaterPlant.input_flow_tqt).label('total_input'),
            db.func.sum(WastewaterPlant.output_flow_tqt).label('total_output')
        ).filter(
            WastewaterPlant.date >= start_date,
            WastewaterPlant.date <= end_date
        ).group_by(WastewaterPlant.date).all()
        
        # Customer consumption
        customer_data = db.session.query(
            CustomerReading.date,
            db.func.sum(CustomerReading.clean_water_reading).label('total_clean_water'),
            db.func.sum(
                db.case(
                    (CustomerReading.wastewater_reading.isnot(None), CustomerReading.wastewater_reading),
                    else_=CustomerReading.wastewater_calculated
                )
            ).label('total_wastewater')
        ).filter(
            CustomerReading.date >= start_date,
            CustomerReading.date <= end_date
        ).group_by(CustomerReading.date).all()
        
        return jsonify({
            'well_production': [{'date': str(d.date), 'production': float(d.total_production or 0)} for d in well_data],
            'clean_water': [{'date': str(d.date), 'output': float(d.clean_water_output or 0)} for d in clean_water_data],
            'wastewater': [{'date': str(d.date), 'input': float(d.total_input or 0), 'output': float(d.total_output or 0)} for d in wastewater_data],
            'customer_consumption': [{'date': str(d.date), 'clean_water': float(d.total_clean_water or 0), 'wastewater': float(d.total_wastewater or 0)} for d in customer_data]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chart-details/<chart_type>')
@login_required
def chart_details(chart_type):
    """Chart details page"""
    if not check_permissions(current_user.role, ['leadership', 'plant_manager', 'admin']):
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))
    
    # Chart type configurations
    chart_configs = {
        'wells': {
            'name': 'Sản lượng Giếng khoan',
            'description': 'Theo dõi sản lượng hàng ngày từ 5 giếng khoan hoạt động',
            'icon': 'fa-water'
        },
        'clean-water': {
            'name': 'Sản lượng Nhà máy Nước sạch',
            'description': 'Sản lượng nước sạch từ giếng khoan và nước thô Jasan',
            'icon': 'fa-tint'
        },
        'wastewater': {
            'name': 'Lưu lượng Nước thải',
            'description': 'Lưu lượng xử lý tại 2 nhà máy nước thải',
            'icon': 'fa-recycle'
        },
        'customers': {
            'name': 'Tiêu thụ Khách hàng',
            'description': 'Theo dõi tiêu thụ nước sạch và phát sinh nước thải của 50 khách hàng',
            'icon': 'fa-users'
        }
    }
    
    config = chart_configs.get(chart_type)
    if not config:
        flash('Invalid chart type', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('chart_details.html', 
                         chart_type=chart_type,
                         chart_type_name=config['name'],
                         chart_description=config['description'],
                         chart_icon=config['icon'])

@app.route('/api/chart-details/<chart_type>')
@login_required
def api_chart_details(chart_type):
    """API endpoint for detailed chart data"""
    try:
        # Get date range
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            days = int(request.args.get('days', 30))
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
        
        if chart_type == 'wells':
            return get_wells_detail_data(start_date, end_date)
        elif chart_type == 'clean-water':
            return get_clean_water_detail_data(start_date, end_date)
        elif chart_type == 'wastewater':
            return get_wastewater_detail_data(start_date, end_date)
        elif chart_type == 'customers':
            return get_customers_detail_data(start_date, end_date)
        else:
            return jsonify({'error': 'Invalid chart type'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_customers_detail_data(start_date, end_date):
    """Get detailed customer consumption data"""
    # Customer consumption data - fixed to show actual data instead of zeros
    customer_data = db.session.query(
        CustomerReading.date,
        func.sum(CustomerReading.clean_water_usage).label('clean_water'),
        func.sum(CustomerReading.wastewater_discharge).label('wastewater')
    ).filter(
        CustomerReading.date >= start_date,
        CustomerReading.date <= end_date
    ).group_by(CustomerReading.date).order_by(CustomerReading.date).all()
    
    # Prepare chart data
    labels = [item.date.strftime('%d/%m') for item in customer_data]
    clean_water_values = [float(item.clean_water or 0) for item in customer_data]
    wastewater_values = [float(item.wastewater or 0) for item in customer_data]
    
    chart_data = {
        'labels': labels,
        'datasets': [
            {
                'label': 'Nước sạch tiêu thụ (m³)',
                'data': clean_water_values,
                'borderColor': 'rgb(54, 162, 235)',
                'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                'fill': False,
                'tension': 0.4
            },
            {
                'label': 'Nước thải phát sinh (m³)',
                'data': wastewater_values,
                'borderColor': 'rgb(255, 206, 86)',
                'backgroundColor': 'rgba(255, 206, 86, 0.1)',
                'fill': False,
                'tension': 0.4
            }
        ]
    }
    
    # Summary statistics
    total_clean = sum(clean_water_values)
    total_wastewater = sum(wastewater_values)
    days_count = len(clean_water_values)
    
    summary = {
        'total': total_clean + total_wastewater,
        'average': (total_clean + total_wastewater) / days_count if days_count > 0 else 0,
        'max': max(clean_water_values + wastewater_values) if clean_water_values + wastewater_values else 0,
        'min': min([x for x in clean_water_values + wastewater_values if x > 0]) if clean_water_values + wastewater_values else 0
    }
    
    # Table data
    table_data = []
    for item in customer_data:
        table_data.append({
            'date': item.date.strftime('%d/%m/%Y'),
            'clean_water': float(item.clean_water or 0),
            'wastewater': float(item.wastewater or 0),
            'total': float(item.clean_water or 0) + float(item.wastewater or 0)
        })
    
    return jsonify({
        'chart_data': chart_data,
        'summary': summary,
        'table_data': table_data
    })

@app.route('/api/kpi-data')
@login_required
def kpi_data():
    """API endpoint for KPI dashboard data"""
    try:
        today = date.today()
        month_start = today.replace(day=1)
        
        # Today's production
        today_well_production = db.session.query(
            db.func.sum(WellProduction.production)
        ).filter(WellProduction.date == today).scalar() or 0
        
        # Monthly production
        month_well_production = db.session.query(
            db.func.sum(WellProduction.production)
        ).filter(WellProduction.date >= month_start).scalar() or 0
        
        # Clean water output today
        today_clean_water = CleanWaterPlant.query.filter_by(date=today).first()
        today_clean_output = today_clean_water.clean_water_output if today_clean_water else 0
        
        # Wastewater treatment today
        today_wastewater = db.session.query(
            db.func.sum(WastewaterPlant.input_flow_tqt)
        ).filter(WastewaterPlant.date == today).scalar() or 0
        
        # Active customers
        active_customers = Customer.query.filter_by(is_active=True).count()
        
        return jsonify({
            'today_well_production': float(today_well_production),
            'month_well_production': float(month_well_production),
            'today_clean_water': float(today_clean_output),
            'today_wastewater': float(today_wastewater),
            'active_customers': active_customers
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
