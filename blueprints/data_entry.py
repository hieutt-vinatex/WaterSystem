import logging
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func
from flask_login import login_required, current_user
from app import db
from models import Well, Customer, WaterTank, WellProduction, CleanWaterPlant, WastewaterPlant, WaterTankLevel, CustomerReading
from utils import check_permissions
from model_helper import exists_by_keys, partial_update_fields, build_insert_payload, coerce_opt

bp = Blueprint('data_entry', __name__)
logger = logging.getLogger(__name__)
EDIT_WINDOW_HOURS = 48 # cho phép sửa dữ liệu nhập liệu trong vòng 48h
COMPANIES_OUTSOURCE = [
    'Công ty TNHH May Minh Anh',
    'Công ty TNHH mây tre xuất khẩu Phú Minh',
    'Công ty TNHH XNK Top Việt Nam',
    'Công ty TNHH Dệt kim Banjie VN',
    'Công ty TNHH Maximus Dyeing House',
    'Công ty TNHH DK Hà Nội SB',
    'Cty TNHH dệt may Lee Hing Việt Nam',
    'Công ty TNHH Lucky St Vina',
    'Công ty TNHH SX và TM Trung Dũng',
]

# Whitelist model + khóa duy nhất và kiểu dữ liệu cho khóa
MODEL_EXISTS_MAP = {
    'clean_water_plant': (CleanWaterPlant, {'date': 'date'}),
    'wastewater_plant': (WastewaterPlant, {'date': 'date', 'plant_number': 'int'}),
    'customer_reading': (CustomerReading, {'date': 'date', 'customer_id': 'int'}),
    'well_production': (WellProduction, {'date': 'date', 'well_id': 'int'}),
    'water_tank_level': (WaterTankLevel, {'date': 'date', 'tank_id': 'int'}),
}

def can_edit(instance) -> bool:
    """Cho phép sửa trong vòng 48h từ lúc tạo."""
    if not getattr(instance, "created_at", None):
        return False
    return (datetime.utcnow() - instance.created_at) <= timedelta(hours=EDIT_WINDOW_HOURS)

def parse_ymd(s: str) -> date:
    if not s:
        raise ValueError("Missing date")
    # Chuẩn định dạng input 'YYYY-MM-DD'
    return datetime.strptime(s, "%Y-%m-%d").date()
@bp.route('/data-entry')
@login_required
def data_entry():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard.dashboard'))
    wells = Well.query.filter_by(is_active=True).all()
    customers = Customer.query.filter_by(is_active=True).all()
    tanks = WaterTank.query.all()
    return render_template(
        'data_entry.html',
        wells=wells,
        customers=customers,
        tanks=tanks,
        date=date,
        companies_outsource=COMPANIES_OUTSOURCE,
    )

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
    """
    GET ?date=YYYY-MM-DD
    Trả: {exists: bool, editable: bool, locked: bool}
    """
    date_str = request.args.get('date')
    the_date = coerce_opt(date_str, 'date')
    if the_date is None:
        return jsonify({'exists': False, 'editable': False, 'locked': False}), 400

    entry = db.session.query(CleanWaterPlant).filter(
        CleanWaterPlant.date == the_date
    ).first()

    if not entry:
        return jsonify({'exists': False, 'editable': False, 'locked': False})

    editable = can_edit(entry)
    return jsonify({'exists': True, 'editable': editable, 'locked': not editable})

def _clean_water_production_today_entry(today):
    # Lấy tổng production của giếng ngày hôm nay
    cur_sum = db.session.query(
        db.func.sum(WellProduction.production)
    ).filter(WellProduction.date == today).scalar() or 0
    
    # Kiểm tra xem có phải ngày đầu tháng không
    if today.day == 1:
        # Ngày đầu tháng: sum(production) - 0
        return float(cur_sum)
    else:
        # Các ngày khác: today - yesterday
        prev_day = today - timedelta(days=1)
        prev_sum = db.session.query(
            db.func.sum(WellProduction.production)
        ).filter(WellProduction.date == prev_day).scalar() or 0
        
        return float(cur_sum) - float(prev_sum)
def _compute_clean_water_output_for_date(the_date: date, jasan_raw:float):
    """
    NS SX ngày n = 0.97 * ( H(n) - J(n) )
    H(n): tổng sản lượng giếng trong ngày n (sum(today) - sum(yesterday))
    J(n): Jasan thô trong ngày n
    """
    try:
        # H(n): tổng giếng theo ngày
        wells_delta = float(_clean_water_production_today_entry(the_date))  # đã là today - yesterday
        print('test',wells_delta)

        # J(n): Jasan thô trong ngày
        # jasan_raw = db.session.query(
        #     db.func.sum(CleanWaterPlant.raw_water_jasan)
        # ).filter(CleanWaterPlant.date == the_date).scalar() or 0.0
        jasan_raw = max(float(jasan_raw), 0.0)

        # NS SX ngày (clamp về 0 nếu âm)
        value = 0.97 * max(wells_delta - jasan_raw, 0.0)

        return {
            'ready': True,
            'value': value,
            'detail': {
                'wells_delta': wells_delta,   # H(n)
                'jasan_raw': jasan_raw,       # J(n)
                'factor': 0.97
            }
        }
    except Exception as e:
        logger.exception("Failed to compute daily clean water output: %s", e)
        return {'ready': False, 'value': None, 'detail': {'error': str(e)}}


# Helper: ở lại đúng tab
def _redirect_to_tab(anchor: str):
    return redirect(url_for('data_entry.data_entry') + f'#{anchor}')

# Helper: parse số, rỗng -> None (để bỏ qua cập nhật)
def parse_float_opt(val):
    s = ('' if val is None else str(val).strip())
    if not s:
        return None
    if s.count(',') and s.count('.') == 0:
        s = s.replace(',', '.')
    else:
        s = s.replace(',', '')
    try:
        return float(s)
    except ValueError:
        return None

@bp.route('/api/well-production/exists')
@login_required
def well_production_exists():
    """
    Input: date, well_ids=[]
    Output: {
      exists: bool,
      editable_ids: [well_id],
      locked_ids: [well_id]
    }
    """
    date_str = request.args.get('date')
    entry_date = parse_ymd(date_str)  # <-- CHUYỂN THÀNH date

    raw_ids = request.args.getlist('well_ids') or request.args.get('well_ids', '')
    well_ids = [int(x) for x in (raw_ids if isinstance(raw_ids, list) else raw_ids.split(',')) if str(x).strip().isdigit()]

    rows = db.session.query(WellProduction).filter(
        WellProduction.date == entry_date,            # <-- so sánh bằng date
        WellProduction.well_id.in_(well_ids)
    ).all()

    editable, locked = [], []
    for r in rows:
        (editable if can_edit(r) else locked).append(r.well_id)

    return jsonify({
        "exists": bool(rows),
        "editable_ids": editable,
        "locked_ids": locked,
    })
    # date_str = request.args.get('date')
    # the_date = coerce_opt(date_str, 'date')
    # if the_date is None:
    #     return jsonify({'exists': False, 'wells': []}), 400

    # ids_param = request.args.get('well_ids', '')
    # well_ids = [int(x) for x in ids_param.split(',') if x.strip().isdigit()]
    # if not well_ids:
    #     return jsonify({'exists': False, 'wells': []})

    # rows = db.session.query(WellProduction.well_id).filter(
    #     WellProduction.date == the_date,
    #     WellProduction.well_id.in_(well_ids)
    # ).all()
    # exist_ids = sorted({r.well_id for r in rows})
    # return jsonify({'exists': len(exist_ids) > 0, 'wells': exist_ids ,})

@bp.route('/api/wastewater-plant/exists')
@login_required
def wastewater_plant_exists():
    # GET ?date=YYYY-MM-DD&plant_numbers=1,2
    date_str = request.args.get('date')
    the_date = coerce_opt(date_str, 'date')
    if the_date is None:
        return jsonify({'exists': False, 'plants': [], 'editable_numbers': [], 'locked_numbers': []}), 400

    pn_param = request.args.get('plant_numbers') or request.args.get('plant_number', '')
    try:
        numbers = [int(x) for x in str(pn_param).split(',') if str(x).strip().isdigit()]
    except Exception:
        numbers = []
    if not numbers:
        return jsonify({'exists': False, 'plants': [], 'editable_numbers': [], 'locked_numbers': []})

    rows = db.session.query(WastewaterPlant).filter(
        WastewaterPlant.date == the_date,
        WastewaterPlant.plant_number.in_(numbers)
    ).all()
    exist_nums = sorted({r.plant_number for r in rows})
    editable, locked = set(), set()
    for r in rows:
        (editable if can_edit(r) else locked).add(r.plant_number)

    return jsonify({
        'exists': bool(exist_nums),
        'plants': exist_nums,
        'editable_numbers': sorted(editable),
        'locked_numbers': sorted(locked),
    })

@bp.route('/api/water-tank-level/exists')
@login_required
def water_tank_level_exists():
    """GET ?date=YYYY-MM-DD&tank_ids=1,2,3 -> {exists: bool, tanks: [ids]}"""
    date_str = request.args.get('date')
    the_date = coerce_opt(date_str, 'date')
    if the_date is None:
        return jsonify({'exists': False, 'tanks': [], 'editable_ids': [], 'locked_ids': []}), 400

    ids_param = request.args.get('tank_ids', '')
    try:
        tank_ids = [int(x) for x in ids_param.split(',') if str(x).strip().isdigit()]
    except Exception:
        tank_ids = []
    if not tank_ids:
        return jsonify({'exists': False, 'tanks': [], 'editable_ids': [], 'locked_ids': []})

    rows = db.session.query(WaterTankLevel).filter(
        WaterTankLevel.date == the_date,
        WaterTankLevel.tank_id.in_(tank_ids)
    ).all()
    exist_ids = sorted({r.tank_id for r in rows})
    editable, locked = set(), set()
    for r in rows:
        (editable if can_edit(r) else locked).add(r.tank_id)

    return jsonify({
        'exists': bool(exist_ids),
        'tanks': exist_ids,
        'editable_ids': sorted(editable),
        'locked_ids': sorted(locked),
    })

@bp.route('/submit-well-data', methods=['POST'])
@login_required
def submit_well_data():
    try:
        entry_date = parse_ymd(request.form['date'])  # <-- CHUYỂN THÀNH date
        flag = 0
        for well_id in request.form.getlist('well_ids'):
            wid = int(well_id)
            raw = (request.form.get(f'production_{wid}', '') or '').strip()
            production = float(raw) if raw != '' else 0.0
            existing = db.session.query(WellProduction).filter_by(
                well_id=wid, date=entry_date                # <-- dùng date
            ).first()

            if not existing:
                db.session.add(WellProduction(
                    well_id=wid,
                    date=entry_date,                        # <-- date object
                    production=production,
                    created_by=current_user.id
                ))
                flag = 1
                # print("1",flag)
            else:
                if not can_edit(existing):
                    flash(f"Ngày {entry_date.strftime('%d/%m/%Y')} đã khóa (quá 24 giờ).", "warning")
                    return redirect(url_for('data_entry.data_entry'))
                existing.production = production
                flag = 1
                # print(2,flag)
        db.session.commit()
        if flag: flash('Đã lưu dữ liệu giếng.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi lưu dữ liệu giếng: {e}', 'danger')

    return redirect(url_for('data_entry.data_entry'))



@bp.route('/clean-water/submit', methods=['POST'], endpoint='submit_clean_water_plant')
@login_required
def submit_clean_water_plant():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard.dashboard'))
    try:
        entry_date = parse_ymd(request.form['date'])
        existing = CleanWaterPlant.query.filter_by(date=entry_date).first()
        field_types = {
            'electricity': 'float',
            'pac_usage': 'float',
            'naoh_usage': 'float',
            'polymer_usage': 'float',
            'clean_water_output': 'float',
            'raw_water_jasan': 'float',
        }

        jasan_val = parse_float_opt(request.form.get('raw_water_jasan')) or 0.0
        compute_res = _compute_clean_water_output_for_date(entry_date, jasan_val)

        payload = build_insert_payload(request.form, field_types)
        payload['clean_water_output'] = compute_res.get('value') if compute_res.get('ready') else None

        if existing:
            if not can_edit(existing):
                flash(f'Ngày {entry_date:%d/%m/%Y} đã khóa (quá 24 giờ).', 'warning')
                return redirect(url_for('data_entry.data_entry') + '#clean-water')
            for field, value in payload.items():
                setattr(existing, field, value)
            db.session.commit()
            flash('Cập nhật dữ liệu nhà máy nước sạch thành công', 'success')
        else:
            db.session.add(CleanWaterPlant(date=entry_date, **payload, created_by=current_user.id))
            db.session.commit()
            flash('Thêm mới dữ liệu nhà máy nước sạch thành công', 'success')
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
        entry_date = parse_ymd(request.form['date'])
        plant_number = int(request.form['plant_number'])
        anchor = f'wastewater-{plant_number}'

        existing = WastewaterPlant.query.filter_by(date=entry_date, plant_number=plant_number).first()
        fields = ['wastewater_meter', 'input_flow_tqt', 'output_flow_tqt', 'sludge_output', 'electricity', 'chemical_usage']
        payload = {}
        for f in fields:
            v = parse_float_opt(request.form.get(f))
            payload[f] = v if v is not None else 0.0

        if existing:
            if not can_edit(existing):
                flash(f'Ngày {entry_date:%d/%m/%Y} cho NMNT {plant_number} đã khóa (quá 24 giờ).', 'warning')
                return _redirect_to_tab(anchor)
            for field, value in payload.items():
                setattr(existing, field, value)
            db.session.commit()
            flash(f'Cập nhật dữ liệu NMNT {plant_number} thành công', 'success')
        else:
            db.session.add(WastewaterPlant(
                plant_number=plant_number, date=entry_date, created_by=current_user.id, **payload
            ))
            db.session.commit()
            flash(f'Thêm mới dữ liệu NMNT {plant_number} thành công', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    return _redirect_to_tab(anchor)


@bp.route('/submit-tank-levels', methods=['POST'])
@login_required
def submit_tank_levels():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard.dashboard'))
    try:
        entry_date = parse_ymd(request.form['date'])
        inserted = 0
        updated = 0
        locked_ids = []

        for tank_id_raw in request.form.getlist('tank_ids'):
            try:
                tank_id = int(tank_id_raw)
            except (TypeError, ValueError):
                continue

            raw_val = request.form.get(f'level_{tank_id}', None)
            level = parse_float_opt(raw_val)
            if level is None:
                continue  # không nhập

            existing = WaterTankLevel.query.filter_by(tank_id=tank_id, date=entry_date).first()
            if existing:
                if not can_edit(existing):
                    locked_ids.append(tank_id)
                    continue
                existing.level = level
                updated += 1
                continue

            db.session.add(WaterTankLevel(
                tank_id=tank_id,
                date=entry_date,
                level=level,
                created_by=current_user.id
            ))
            inserted += 1

        if inserted == 0 and updated == 0:
            if locked_ids:
                flash(f'Các bể {", ".join(str(i) for i in locked_ids)} đã khóa (quá 24 giờ).', 'warning')
            else:
                flash('Không có dữ liệu để lưu', 'warning')
            return redirect(url_for('data_entry.data_entry') + '#tanks')

        db.session.commit()
        parts = []
        if inserted:
            parts.append(f'Thêm mới {inserted} bể')
        if updated:
            parts.append(f'Cập nhật {updated} bể')
        flash(f'Đã lưu dữ liệu bể chứa: {"; ".join(parts)}.', 'success')
        if locked_ids:
            flash(f'Bỏ qua các bể đã khóa (quá 24 giờ): {", ".join(str(i) for i in locked_ids)}.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi lưu dữ liệu: {str(e)}', 'error')
    return redirect(url_for('data_entry.data_entry') + '#tanks')


@bp.route('/api/customer-readings/exists')
@login_required
def customer_readings_exists():
    # GET ?date=YYYY-MM-DD&customer_ids=1,2,3
    date_str = request.args.get('date')
    try:
        the_date = parse_ymd(date_str)
    except Exception:
        return jsonify({'exists': False, 'customers': [], 'editable_ids': [], 'locked_ids': []}), 400

    ids_param = request.args.get('customer_ids', '')
    ids = [int(x) for x in ids_param.split(',') if x.strip().isdigit()]
    if not ids:
        return jsonify({'exists': False, 'customers': [], 'editable_ids': [], 'locked_ids': []})

    rows = db.session.query(CustomerReading).filter(
        CustomerReading.date == the_date,
        CustomerReading.customer_id.in_(ids)
    ).all()
    exist_ids = sorted({r.customer_id for r in rows})
    editable, locked = set(), set()
    for r in rows:
        (editable if can_edit(r) else locked).add(r.customer_id)

    return jsonify({
        'exists': bool(exist_ids),
        'customers': exist_ids,
        'editable_ids': sorted(editable),
        'locked_ids': sorted(locked),
    })

@bp.route('/submit-customer-readings', methods=['POST'])
@login_required
def submit_customer_readings():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard.dashboard'))
    try:
        entry_date = parse_ymd(request.form['date'])
        customer_ids = [int(x) for x in request.form.getlist('customer_ids') if str(x).isdigit()]
        if not customer_ids:
            flash('Không có khách hàng nào để lưu', 'warning')
            return redirect(url_for('data_entry.data_entry') + '#customers')

        def _pfloat(val):
            s = ('' if val is None else str(val).strip())
            if s == '':
                return None
            if s.count(',') and s.count('.') == 0:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
            try:
                return float(s)
            except ValueError:
                return None

        filled = {}
        for cid in customer_ids:
            cw1_raw = request.form.get(f'clean_water_{cid}', '')
            cw2_raw = request.form.get(f'clean_water_2_{cid}', '')
            cw3_raw = request.form.get(f'clean_water_3_{cid}', '')
            ww_raw  = request.form.get(f'wastewater_{cid}', '')
            outsource_raw = request.form.get(f'clean_water_outsource_{cid}', '')
            cw1_val = _pfloat(cw1_raw)
            cw2_val = _pfloat(cw2_raw)
            cw3_val = _pfloat(cw3_raw)
            outsource_val = _pfloat(outsource_raw)
            ww_val  = _pfloat(ww_raw) if ww_raw != '' else None
            if any(val is not None for val in (cw1_val, cw2_val, cw3_val, outsource_val, ww_val)):
                filled[cid] = {
                    'cw1': cw1_val,
                    'cw2': cw2_val,
                    'cw3': cw3_val,
                    'outsource': outsource_val,
                    'ww': ww_val,
                }

        if not filled:
            flash('Không có dữ liệu để lưu', 'warning')
            return redirect(url_for('data_entry.data_entry') + '#customers')

        existing_rows = CustomerReading.query.filter(
            CustomerReading.date == entry_date,
            CustomerReading.customer_id.in_(list(filled.keys()))
        ).all()
        exist_ids = {r.customer_id for r in existing_rows}
        existing_map = {r.customer_id: r for r in existing_rows}

        inserted = 0
        updated = 0
        locked_ids = []
        for cid, vals in filled.items():
            cw1_val, cw2_val,cw3_val, ww_val = vals['cw1'], vals['cw2'], vals['cw3'],vals['ww']
            customer = Customer.query.get(cid)
            try:
                ratio = float(customer.water_ratio or 0)
            except (TypeError, ValueError):
                ratio = 0.0

            outsource_val = vals['outsource']
            total_clean = (cw1_val or 0.0) + (cw2_val or 0.0) + (cw3_val or 0.0)
            total_with_outsource = total_clean + (outsource_val or 0.0)
            ww_calc = None if ww_val is not None else (
                total_with_outsource * ratio
                if any(v is not None for v in (cw1_val, cw2_val, cw3_val, outsource_val))
                else None
            )

            existing = existing_map.get(cid)
            if existing:
                if not can_edit(existing):
                    locked_ids.append(cid)
                    continue
                existing.clean_water_reading = (cw1_val if cw1_val is not None else 0.0)
                existing.clean_water_reading_2 = (cw2_val if cw2_val is not None else 0.0)
                existing.clean_water_reading_3 = (cw3_val if cw3_val is not None else 0.0)
                existing.clean_water_outsource = (outsource_val if outsource_val is not None else 0.0)
                existing.wastewater_reading = ww_val
                existing.wastewater_calculated = (ww_calc if ww_val is None else None)
                updated += 1
                continue

            db.session.add(CustomerReading(
                customer_id=cid,
                date=entry_date,
                clean_water_reading=(cw1_val if cw1_val is not None else 0.0),
                clean_water_reading_2=(cw2_val if cw2_val is not None else 0.0),
                clean_water_reading_3=(cw3_val if cw3_val is not None else 0.0),
                clean_water_outsource=(outsource_val if outsource_val is not None else 0.0),
                wastewater_reading=ww_val,
                wastewater_calculated=(ww_calc if ww_val is None else None),
                created_by=current_user.id
            ))
            inserted += 1

        if inserted == 0 and updated == 0:
            if locked_ids:
                flash(f'Các khách hàng {", ".join(str(i) for i in locked_ids)} đã khóa (quá 24 giờ).', 'warning')
            else:
                flash('Không có dữ liệu để lưu', 'warning')
            return redirect(url_for('data_entry.data_entry') + '#customers')

        db.session.commit()
        parts = []
        if inserted:
            parts.append(f'Thêm mới {inserted} khách hàng')
        if updated:
            parts.append(f'Cập nhật {updated} khách hàng')
        flash(f'Đã lưu dữ liệu khách hàng: {"; ".join(parts)}.', 'success')
        if locked_ids:
            flash(f'Bỏ qua các khách hàng đã khóa (quá 24 giờ): {", ".join(str(i) for i in locked_ids)}.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    return redirect(url_for('data_entry.data_entry') + '#customers')
