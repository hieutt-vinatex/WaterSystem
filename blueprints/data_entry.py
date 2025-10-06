import logging
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from models import Well, Customer, WaterTank, WellProduction, CleanWaterPlant, WastewaterPlant, WaterTankLevel, CustomerReading
from utils import check_permissions
from model_helper import exists_by_keys, partial_update_fields, build_insert_payload, coerce_opt

bp = Blueprint('data_entry', __name__)
logger = logging.getLogger(__name__)

# Whitelist model + khóa duy nhất và kiểu dữ liệu cho khóa
MODEL_EXISTS_MAP = {
    'clean_water_plant': (CleanWaterPlant, {'date': 'date'}),
    'wastewater_plant': (WastewaterPlant, {'date': 'date', 'plant_number': 'int'}),
    'customer_reading': (CustomerReading, {'date': 'date', 'customer_id': 'int'}),
    'well_production': (WellProduction, {'date': 'date', 'well_id': 'int'}),
    'water_tank_level': (WaterTankLevel, {'date': 'date', 'tank_id': 'int'}),
}

@bp.route('/data-entry')
@login_required
def data_entry():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard.dashboard'))
    wells = Well.query.filter_by(is_active=True).all()
    customers = Customer.query.filter_by(is_active=True).all()
    tanks = WaterTank.query.all()
    return render_template('data_entry.html', wells=wells, customers=customers, tanks=tanks, date=date)

@bp.route('/api/exists/<model_key>')
@login_required
def model_exists(model_key):
    """
    API tổng quát kiểm tra trùng dữ liệu theo khóa.
    Ví dụ:
      /api/exists/clean_water_plant?date=2025-10-06
      /api/exists/wastewater_plant?date=2025-10-06&plant_number=1
    """
    item = MODEL_EXISTS_MAP.get(model_key)
    if not item:
        return jsonify({'error': 'model not allowed', 'exists': False}), 400
    Model, key_types = item
    filters = {}
    for k, t in key_types.items():
        v = coerce_opt(request.args.get(k), t)
        if v is None:
            return jsonify({'error': f'missing or invalid key {k}', 'exists': False}), 400
        filters[k] = v
    return jsonify({'exists': exists_by_keys(Model, filters)})

# Back-compat: endpoint cũ cho CleanWaterPlant (gọi hàm tổng quát)
@bp.route('/api/clean-water-plant/exists')
@login_required
def clean_water_plant_exists():
    date_str = request.args.get('date')
    v = coerce_opt(date_str, 'date')
    if v is None:
        return jsonify({'exists': False})
    return jsonify({'exists': exists_by_keys(CleanWaterPlant, {'date': v})})


@bp.route('/submit-well-data', methods=['POST'])
@login_required
def submit_well_data():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard.dashboard'))
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        for well_id in request.form.getlist('well_ids'):
            production = float(request.form.get(f'production_{well_id}', 0))
            existing = WellProduction.query.filter_by(well_id=well_id, date=entry_date).first()
            if existing:
                existing.production = production
            else:
                db.session.add(WellProduction(
                    well_id=well_id, date=entry_date, production=production, created_by=current_user.id
                ))
        db.session.commit()
        flash('Well production data saved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    return redirect(url_for('data_entry.data_entry'))


@bp.route('/submit-clean-water-plant', methods=['POST'])
@login_required
def submit_clean_water_plant():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard.dashboard'))
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        overwrite = request.form.get('overwrite') == '1'

        existing = CleanWaterPlant.query.filter_by(date=entry_date).first()
        if existing and not overwrite:
            flash('Đã có dữ liệu cho ngày này. Chọn "Ghi đè" nếu muốn thay thế.', 'warning')
            return redirect(url_for('data_entry.data_entry') + '#clean-water')

        field_types = {
            'electricity': 'float',
            'pac_usage': 'float',
            'naoh_usage': 'float',
            'polymer_usage': 'float',
            'clean_water_output': 'float',
            'raw_water_jasan': 'float',
        }

        if existing:
            # Cập nhật một phần: ô nào để trống sẽ không thay đổi
            partial_update_fields(existing, request.form, field_types)
        else:
            payload = build_insert_payload(request.form, field_types)
            db.session.add(CleanWaterPlant(date=entry_date, **payload, created_by=current_user.id))

        db.session.commit()
        flash('Clean water plant data saved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    return redirect(url_for('data_entry.data_entry') + '#clean-water')

@bp.route('/submit-wastewater-plant', methods=['POST'])
@login_required
def submit_wastewater_plant():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard.dashboard'))
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        plant_number = int(request.form['plant_number'])
        existing = WastewaterPlant.query.filter_by(date=entry_date, plant_number=plant_number).first()
        if existing:
            existing.wastewater_meter = float(request.form.get('wastewater_meter', 0))
            existing.input_flow_tqt = float(request.form.get('input_flow_tqt', 0))
            existing.output_flow_tqt = float(request.form.get('output_flow_tqt', 0))
            existing.sludge_output = float(request.form.get('sludge_output', 0))
            existing.electricity = float(request.form.get('electricity', 0))
            existing.chemical_usage = float(request.form.get('chemical_usage', 0))
        else:
            db.session.add(WastewaterPlant(
                plant_number=plant_number, date=entry_date,
                wastewater_meter=float(request.form.get('wastewater_meter', 0)),
                input_flow_tqt=float(request.form.get('input_flow_tqt', 0)),
                output_flow_tqt=float(request.form.get('output_flow_tqt', 0)),
                sludge_output=float(request.form.get('sludge_output', 0)),
                electricity=float(request.form.get('electricity', 0)),
                chemical_usage=float(request.form.get('chemical_usage', 0)),
                created_by=current_user.id
            ))
        db.session.commit()
        flash(f'Wastewater plant {plant_number} data saved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    return redirect(url_for('data_entry.data_entry'))

@bp.route('/submit-tank-levels', methods=['POST'])
@login_required
def submit_tank_levels():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard.dashboard'))
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        for tank_id in request.form.getlist('tank_ids'):
            level = float(request.form.get(f'level_{tank_id}', 0))
            existing = WaterTankLevel.query.filter_by(tank_id=tank_id, date=entry_date).first()
            if existing:
                existing.level = level
            else:
                db.session.add(WaterTankLevel(tank_id=tank_id, date=entry_date, level=level, created_by=current_user.id))
        db.session.commit()
        flash('Mức nước bể chứa đã được lưu thành công', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi lưu dữ liệu: {str(e)}', 'error')
    return redirect(url_for('data_entry.data_entry'))

@bp.route('/submit-customer-readings', methods=['POST'])
@login_required
def submit_customer_readings():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard.dashboard'))
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        for customer_id in request.form.getlist('customer_ids'):
            clean_water_reading = float(request.form.get(f'clean_water_{customer_id}', 0))
            wastewater_reading = request.form.get(f'wastewater_{customer_id}')
            customer = Customer.query.get(customer_id)
            if wastewater_reading:
                wastewater_reading = float(wastewater_reading)
                wastewater_calculated = None
            else:
                wastewater_reading = None
                wastewater_calculated = clean_water_reading * customer.water_ratio
            existing = CustomerReading.query.filter_by(customer_id=customer_id, date=entry_date).first()
            if existing:
                existing.clean_water_reading = clean_water_reading
                existing.wastewater_reading = wastewater_reading
                existing.wastewater_calculated = wastewater_calculated
            else:
                db.session.add(CustomerReading(
                    customer_id=customer_id, date=entry_date,
                    clean_water_reading=clean_water_reading,
                    wastewater_reading=wastewater_reading,
                    wastewater_calculated=wastewater_calculated,
                    created_by=current_user.id
                ))
        db.session.commit()
        flash('Customer readings saved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    return redirect(url_for('data_entry.data_entry'))