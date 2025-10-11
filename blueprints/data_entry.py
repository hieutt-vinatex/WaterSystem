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
    """
    GET ?date=YYYY-MM-DD
    Trả: {exists: bool}
    """
    date_str = request.args.get('date')
    the_date = coerce_opt(date_str, 'date')
    if the_date is None:
        return jsonify({'exists': False}), 400

    exists = db.session.query(CleanWaterPlant.id).filter(
        CleanWaterPlant.date == the_date
    ).first() is not None

    return jsonify({'exists': exists})

# --- Tính Nước sạch sản xuất (m³) theo công thức yêu cầu ---
# NS cấp ngày n = Tổng NS (Bể 1200+2000+4000) ngày n-1
#                + Tổng SL giếng khoan ngày n
#                - Tổng NS (Bể 1200+2000+4000) ngày n
def _compute_clean_water_output_for_date(the_date: date):
    try:
        # Tìm 3 bể clean nước theo nhãn 1200/2000/4000 (tên có thể là "Bể chứa 1200"...)
        tank_ids = []
        missing_labels = []
        for label in ("1200", "2000", "4000"):
            tank = WaterTank.query.filter(
                WaterTank.tank_type == 'clean_water',
                WaterTank.name.ilike(f"%{label}%")
            ).first()
            if tank:
                tank_ids.append(tank.id)
            else:
                missing_labels.append(label)

        if missing_labels:
            return {'ready': False, 'value': None, 'detail': {'missing_tanks': missing_labels}}

        prev_date = the_date - timedelta(days=1)

        prev_levels = db.session.query(WaterTankLevel.tank_id, WaterTankLevel.level) \
            .filter(WaterTankLevel.date == prev_date, WaterTankLevel.tank_id.in_(tank_ids)).all()
        today_levels = db.session.query(WaterTankLevel.tank_id, WaterTankLevel.level) \
            .filter(WaterTankLevel.date == the_date, WaterTankLevel.tank_id.in_(tank_ids)).all()

        prev_map = {tid: lvl for tid, lvl in prev_levels}
        today_map = {tid: lvl for tid, lvl in today_levels}

        missing_prev = [tid for tid in tank_ids if tid not in prev_map]
        missing_today = [tid for tid in tank_ids if tid not in today_map]

        well_sum = db.session.query(func.sum(WellProduction.production)) \
            .filter(WellProduction.date == the_date).scalar()

        ready = (not missing_prev) and (not missing_today) and (well_sum is not None)
        if not ready:
            return {
                'ready': False,
                'value': None,
                'detail': {
                    'missing_prev_tanks': missing_prev,
                    'missing_today_tanks': missing_today,
                    'well_sum_today': float(well_sum) if well_sum is not None else None,
                }
            }

        sum_prev = float(sum(prev_map[tid] or 0.0 for tid in tank_ids))
        sum_today = float(sum(today_map[tid] or 0.0 for tid in tank_ids))
        sum_wells = float(well_sum or 0.0)
        value = sum_prev + sum_wells - sum_today

        return {'ready': True, 'value': value, 'detail': {
            'sum_prev_tanks': sum_prev,
            'sum_today_tanks': sum_today,
            'sum_wells_today': sum_wells,
        }}
    except Exception as e:
        logger.exception("Failed to compute clean water output: %s", e)
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
    GET ?date=YYYY-MM-DD&well_ids=1,2,3
    Trả: {exists: bool, wells: [well_id,...]}
    """
    date_str = request.args.get('date')
    the_date = coerce_opt(date_str, 'date')
    if the_date is None:
        return jsonify({'exists': False, 'wells': []}), 400

    ids_param = request.args.get('well_ids', '')
    well_ids = [int(x) for x in ids_param.split(',') if x.strip().isdigit()]
    if not well_ids:
        return jsonify({'exists': False, 'wells': []})

    rows = db.session.query(WellProduction.well_id).filter(
        WellProduction.date == the_date,
        WellProduction.well_id.in_(well_ids)
    ).all()
    exist_ids = sorted({r.well_id for r in rows})
    return jsonify({'exists': len(exist_ids) > 0, 'wells': exist_ids})

@bp.route('/api/wastewater-plant/exists')
@login_required
def wastewater_plant_exists():
    # GET ?date=YYYY-MM-DD&plant_numbers=1,2
    date_str = request.args.get('date')
    the_date = coerce_opt(date_str, 'date')
    if the_date is None:
        return jsonify({'exists': False, 'plants': []}), 400

    pn_param = request.args.get('plant_numbers') or request.args.get('plant_number', '')
    try:
        numbers = [int(x) for x in str(pn_param).split(',') if str(x).strip().isdigit()]
    except Exception:
        numbers = []
    if not numbers:
        return jsonify({'exists': False, 'plants': []})

    rows = db.session.query(WastewaterPlant.plant_number).filter(
        WastewaterPlant.date == the_date,
        WastewaterPlant.plant_number.in_(numbers)
    ).all()
    exist_nums = sorted({r.plant_number for r in rows})
    return jsonify({'exists': len(exist_nums) > 0, 'plants': exist_nums})

@bp.route('/api/water-tank-level/exists')
@login_required
def water_tank_level_exists():
    """GET ?date=YYYY-MM-DD&tank_ids=1,2,3 -> {exists: bool, tanks: [ids]}"""
    date_str = request.args.get('date')
    the_date = coerce_opt(date_str, 'date')
    if the_date is None:
        return jsonify({'exists': False, 'tanks': []}), 400

    ids_param = request.args.get('tank_ids', '')
    try:
        tank_ids = [int(x) for x in ids_param.split(',') if str(x).strip().isdigit()]
    except Exception:
        tank_ids = []
    if not tank_ids:
        return jsonify({'exists': False, 'tanks': []})

    rows = db.session.query(WaterTankLevel.tank_id).filter(
        WaterTankLevel.date == the_date,
        WaterTankLevel.tank_id.in_(tank_ids)
    ).all()
    exist_ids = sorted({r.tank_id for r in rows})
    return jsonify({'exists': len(exist_ids) > 0, 'tanks': exist_ids})

@bp.route('/submit-well-data', methods=['POST'])
@login_required
def submit_well_data():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard.dashboard'))
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()

        # Danh sách giếng trên form
        all_ids = [int(x) for x in request.form.getlist('well_ids') if str(x).isdigit()]

        # Chỉ lấy các giếng có nhập số (kể cả 0)
        filled = {}
        for wid in all_ids:
            v = parse_float_opt(request.form.get(f'production_{wid}'))
            if v is not None:
                filled[wid] = v

        if not filled:
            flash('Không có dữ liệu để lưu', 'warning')
            return redirect(url_for('data_entry.data_entry') + '#wells')

        # Lấy các bản ghi đã tồn tại của những giếng có nhập
        existing_rows = WellProduction.query.filter(
            WellProduction.date == entry_date,
            WellProduction.well_id.in_(list(filled.keys()))
        ).all()
        exist_map = {r.well_id: r for r in existing_rows}

        # Danh sách giếng cho phép ghi đè (từ hidden overwrite_ids: "2,5,7")
        overwrite_ids = set(int(x) for x in request.form.get('overwrite_ids', '').split(',') if x.strip().isdigit())

        # Lưu: chỉ ghi đè những giếng được xác nhận; giếng chưa có thì tạo mới
        for wid, val in filled.items():
            if wid in exist_map:
                if wid in overwrite_ids:
                    exist_map[wid].production = val
                # nếu không xác nhận ghi đè -> bỏ qua
            else:
                db.session.add(WellProduction(
                    well_id=wid, date=entry_date, production=val, created_by=current_user.id
                ))

        db.session.commit()
        flash('Well production data saved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    return redirect(url_for('data_entry.data_entry') + '#wells')


@bp.route('/clean-water/submit', methods=['POST'], endpoint='submit_clean_water_plant')
@login_required
def submit_clean_water_plant():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard.dashboard'))
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()

        existing = CleanWaterPlant.query.filter_by(date=entry_date).first()

        field_types = {
            'electricity': 'float',
            'pac_usage': 'float',
            'naoh_usage': 'float',
            'polymer_usage': 'float',
            'clean_water_output': 'float',
            'raw_water_jasan': 'float',
        }

        # Tính tự động theo dữ liệu bể & giếng nếu có đủ dữ liệu
        compute_res = _compute_clean_water_output_for_date(entry_date)

        if existing:
            # Luôn cập nhật các trường đã nhập (không cần cờ overwrite)
            partial_update_fields(existing, request.form, field_types)
            if compute_res.get('ready'):
                existing.clean_water_output = compute_res.get('value')
            msg = 'Cập nhật dữ liệu nhà máy nước sạch thành công'
        else:
            payload = build_insert_payload(request.form, field_types)
            if compute_res.get('ready'):
                payload['clean_water_output'] = compute_res.get('value')
            else:
                payload['clean_water_output'] = None  # Tránh lưu 0.0 mặc định nếu chưa đủ dữ liệu -> để NULL
            db.session.add(CleanWaterPlant(date=entry_date, **payload, created_by=current_user.id))
            msg = 'Thêm mới dữ liệu nhà máy nước sạch thành công'

        db.session.commit()
        flash(msg, 'success')
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
        overwrite = request.form.get('overwrite') == '1'
        anchor = f'wastewater-{plant_number}'

        existing = WastewaterPlant.query.filter_by(date=entry_date, plant_number=plant_number).first()
        if existing and not overwrite:
            flash(f'Đã có dữ liệu ngày {entry_date:%d/%m/%Y} cho NMNT {plant_number}. Chọn "Ghi đè" nếu muốn thay thế.', 'warning')
            return _redirect_to_tab(anchor)

        # Các trường số của NMNT
        fields = ['wastewater_meter', 'input_flow_tqt', 'output_flow_tqt', 'sludge_output', 'electricity', 'chemical_usage']

        if existing:
            # Cập nhật có chọn lọc: chỉ trường nào nhập giá trị mới
            for f in fields:
                v = parse_float_opt(request.form.get(f))
                if v is not None:
                    setattr(existing, f, v)
        else:
            # Tạo mới: trường rỗng -> 0
            payload = {}
            for f in fields:
                v = parse_float_opt(request.form.get(f))
                payload[f] = v if v is not None else 0.0
            db.session.add(WastewaterPlant(
                plant_number=plant_number, date=entry_date, created_by=current_user.id, **payload
            ))

        db.session.commit()
        flash(f'Wastewater plant {plant_number} data saved successfully', 'success')
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
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        changes = 0

        for tank_id_raw in request.form.getlist('tank_ids'):
            # Bỏ qua nếu tank_id không phải số
            try:
                tank_id = int(tank_id_raw)
            except (TypeError, ValueError):
                continue

            # Chỉ xử lý nếu người dùng có nhập (không rỗng)
            raw_val = request.form.get(f'level_{tank_id}', None)
            level = parse_float_opt(raw_val)  # rỗng/không hợp lệ -> None
            if level is None:
                # Không nhập gì -> giữ nguyên giá trị cũ (bỏ qua)
                continue

            existing = WaterTankLevel.query.filter_by(tank_id=tank_id, date=entry_date).first()
            if existing:
                # Cập nhật giá trị mới
                if existing.level != level:
                    existing.level = level
                    changes += 1
            else:
                # Tạo mới nếu chưa có bản ghi
                db.session.add(WaterTankLevel(
                    tank_id=tank_id,
                    date=entry_date,
                    level=level,
                    created_by=current_user.id
                ))
                changes += 1

        if changes == 0:
            flash('Không có thay đổi nào được áp dụng.', 'warning')
        else:
            db.session.commit()
            flash('Mức nước bể chứa đã được lưu thành công', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi lưu dữ liệu: {str(e)}', 'error')
    return redirect(url_for('data_entry.data_entry'))

@bp.route('/api/customer-readings/exists')
@login_required
def customer_readings_exists():
    # GET ?date=YYYY-MM-DD&customer_ids=1,2,3
    date_str = request.args.get('date')
    try:
        the_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'exists': False, 'customers': []}), 400

    ids_param = request.args.get('customer_ids', '')
    ids = [int(x) for x in ids_param.split(',') if x.strip().isdigit()]
    if not ids:
        return jsonify({'exists': False, 'customers': []})

    rows = db.session.query(CustomerReading.customer_id).filter(
        CustomerReading.date == the_date,
        CustomerReading.customer_id.in_(ids)
    ).all()
    exist_ids = sorted({r.customer_id for r in rows})
    return jsonify({'exists': len(exist_ids) > 0, 'customers': exist_ids})

@bp.route('/submit-customer-readings', methods=['POST'])
@login_required
def submit_customer_readings():
    if not check_permissions(current_user.role, ['data_entry', 'plant_manager', 'admin']):
        flash('You do not have permission to perform this action', 'error')
        return redirect(url_for('dashboard.dashboard'))
    try:
        entry_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        customer_ids = [int(x) for x in request.form.getlist('customer_ids') if str(x).isdigit()]
        if not customer_ids:
            flash('Không có khách hàng nào để lưu', 'warning')
            return redirect(url_for('data_entry.data_entry') + '#customers')

        # Chỉ xử lý KH có nhập số (kể cả "0")
        def parse_float_opt(val):
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
            cw2_raw = request.form.get(f'clean_water_2_{cid}', '')  #thêm ĐH2
            ww_raw  = request.form.get(f'wastewater_{cid}', '')
            print(cw2_raw)
            cw1_val = parse_float_opt(cw1_raw)
            cw2_val = parse_float_opt(cw2_raw)
            ww_val  = parse_float_opt(ww_raw) if ww_raw != '' else None

            # Có dữ liệu ở bất kỳ ô nào thì mới xử lý
            if cw1_val is not None or cw2_val is not None or ww_val is not None:
                filled[cid] = {'cw1': cw1_val, 'cw2': cw2_val, 'ww': ww_val}

        if not filled:
            flash('Không có dữ liệu để lưu', 'warning')
            return redirect(url_for('data_entry.data_entry') + '#customers')

        existing_rows = CustomerReading.query.filter(
            CustomerReading.date == entry_date,
            CustomerReading.customer_id.in_(list(filled.keys()))
        ).all()
        exist_map = {r.customer_id: r for r in existing_rows}

        # Danh sách KH cho phép ghi đè (từ popup)
        overwrite_raw = request.form.get('overwrite_customer_ids', '') or request.form.get('overwrite_ids', '')
        overwrite_ids = {int(x) for x in overwrite_raw.split(',') if x.strip().isdigit()}

        changes = 0
        for cid, vals in filled.items():
            cw1_val, cw2_val, ww_val = vals['cw1'], vals['cw2'], vals['ww']

            # Tính wastewater_calculated nếu không nhập wastewater
            customer = Customer.query.get(cid)
            try:
                ratio = float(customer.water_ratio or 0)
            except (TypeError, ValueError):
                ratio = 0.0

            total_clean = (cw1_val or 0.0) + (cw2_val or 0.0)  # ĐH1 + ĐH2 (ĐH2 null thì +0)
            ww_calc = None if ww_val is not None else (
                total_clean * ratio if (cw1_val is not None or cw2_val is not None) else None
            )

            if cid in exist_map:
                if cid in overwrite_ids:
                    before = (exist_map[cid].clean_water_reading,
                              getattr(exist_map[cid], 'clean_water_reading_2', None),
                              exist_map[cid].wastewater_reading,
                              exist_map[cid].wastewater_calculated)

                    # Cập nhật ĐH1/ĐH2 nếu có nhập
                    if cw1_val is not None:
                        exist_map[cid].clean_water_reading = cw1_val
                    if cw2_val is not None:
                        exist_map[cid].clean_water_reading_2 = cw2_val  # lưu ĐH2

                    # Xử lý nước thải: nếu nhập tay -> ưu tiên; nếu không -> tính lại theo tỷ lệ
                    if ww_val is not None:
                        exist_map[cid].wastewater_reading = ww_val
                        exist_map[cid].wastewater_calculated = None
                    else:
                        # Chỉ set lại calculated nếu có thay đổi ĐH1/ĐH2
                        if cw1_val is not None or cw2_val is not None:
                            exist_map[cid].wastewater_calculated = ww_calc

                    after = (exist_map[cid].clean_water_reading,
                             getattr(exist_map[cid], 'clean_water_reading_2', None),
                             exist_map[cid].wastewater_reading,
                             exist_map[cid].wastewater_calculated)
                    if before != after:
                        changes += 1
                # nếu không xác nhận ghi đè -> bỏ qua
            else:
                db.session.add(CustomerReading(
                    customer_id=cid,
                    date=entry_date,
                    clean_water_reading=(cw1_val if cw1_val is not None else 0.0),
                    clean_water_reading_2=(cw2_val if cw2_val is not None else 0.0),  # 👈 thêm field mới
                    wastewater_reading=ww_val,
                    wastewater_calculated=(ww_calc if ww_val is None else None),
                    created_by=current_user.id
                ))
                changes += 1

        if changes == 0:
            flash('Không có thay đổi nào được áp dụng. Có thể dữ liệu đã tồn tại và bạn không xác nhận ghi đè.', 'warning')
            return redirect(url_for('data_entry.data_entry') + '#customers')

        db.session.commit()
        flash('Customer readings saved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
    return redirect(url_for('data_entry.data_entry') + '#customers')
