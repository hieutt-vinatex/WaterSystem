import logging, random
from datetime import datetime, date, timedelta
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from flask_login import login_required,current_user
from app import db
from models import Well, WellProduction, CleanWaterPlant, WastewaterPlant, CustomerReading, Customer, WaterTankLevel
from sqlalchemy import func, case
from sqlalchemy.sql import over

bp = Blueprint('charts', __name__)
logger = logging.getLogger(__name__)


@bp.route('/api/kpi-data')
@login_required
def kpi_data():
    """API endpoint for KPI dashboard data"""
    try:
        # Optional date param to view historical KPI
        date_str = request.args.get('date')
        today = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
        month_start = today.replace(day=1)
        yesterday = today - timedelta(days=1)
        today_well_production = _clean_water_production_today(today)

        # Monthly production
        month_well_production = db.session.query(
            db.func.sum(WellProduction.production)
        ).filter(WellProduction.date >= month_start).scalar() or 0

        # Clean water output today
        # Logic mới: nước sạch không Jasan + tồn kho hôm qua - tồn kho hôm nay

        today_clean_output = _get_daily_production(today, yesterday)
        # Wastewater treatment today
        today_wastewater = db.session.query(
            db.func.sum(WastewaterPlant.input_flow_tqt)
        ).filter(WastewaterPlant.date == today).scalar() or 0

        # Active customers (not date dependent)
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


# tính sản lượng theo ngày
def _get_daily_production(today, yesterday):
    clean_without_jasan = _clean_water_without_jasan(today)
    today_jasan = _get_today_jasan(today)

    inventory_yesterday = _get_tank_inventory_yesterday(yesterday)
    inventory_today = _get_tank_inventory_today(today)
    return float((clean_without_jasan - today_jasan) * 0.98 + inventory_yesterday - inventory_today)


    #lượng nước sạch nhà máy nước sạch
def _clean_water_without_jasan(today):
    production_today = _clean_water_production_today(today)
    return float(production_today)


def _get_today_jasan(today):
    return db.session.query(
        db.func.sum(CleanWaterPlant.raw_water_jasan)
    ).filter(CleanWaterPlant.date == today).scalar() or 0

def _clean_water_production_today(today):
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

    
def _calculate_tank_inventory(tank_id: int, level: float) -> float:
    """
    Tính lượng nước tồn theo công thức riêng cho từng bể:
    - Tank 1: tồn = (9 - level) * 115
    - Tank 2: tồn = (12 - level) * 160  
    - Tank 3: tồn = (13 - level) * 300
    """
    # if tank_id == 1:
    #     return (9 - level) * 115
    # elif tank_id == 2:
    #     return (12 - level) * 160
    # elif tank_id == 3:
    #     return (13 - level) * 300
    # else:
    #     return 0.0  # Bể không xác định
    """level đã là thể tích m³ trong DB -> trả về trực tiếp."""
    return float(level or 0.0)


def _get_tank_inventory_yesterday(yesterday):
    """
    Tính tổng tồn kho ngày hôm qua và hôm nay của tất cả các bể
    Trả về tuple (tồn_hôm_qua, tồn_hôm_nay)
    """
    # Lấy mực nước của các bể ngày hôm qua
    yesterday_levels = db.session.query(
        WaterTankLevel.tank_id,
        WaterTankLevel.level
    ).filter(WaterTankLevel.date == yesterday).all()
    # Tính tổng tồn kho hôm qua
    total_yesterday = 0.0
    for tank_level in yesterday_levels:
        level = float(tank_level.level or 0)
        inventory = _calculate_tank_inventory(tank_level.tank_id, level)
        total_yesterday += inventory
    return total_yesterday

def _get_tank_inventory_today(today):
    # date_str = request.args.get('date')
    # today = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
    
    # Lấy mực nước của các bể ngày hôm nay
    today_levels = db.session.query(
        WaterTankLevel.tank_id,
        WaterTankLevel.level
    ).filter(WaterTankLevel.date == today).all()
    # Tính tổng tồn kho hôm nay
    total_today = 0.0
    for tank_level in today_levels:
        level = float(tank_level.level or 0)
        inventory = _calculate_tank_inventory(tank_level.tank_id, level)
        total_today += inventory
    print('total_today', total_today)

    return total_today


@bp.route('/api/dashboard-data')
@login_required
def dashboard_data():
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            days = int(request.args.get('days', 30))
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
        # Tính sản lượng giếng theo ngày: ngày n = tổng production ngày n - tổng production ngày (n-1)
        # Tạo dải ngày
        dates = []
        cur = start_date
        while cur <= end_date:
            dates.append(cur)
            cur += timedelta(days=1)

        # Lấy tổng production từ (start_date - 1) đến end_date
        prev_start = start_date - timedelta(days=1)
        well_rows = db.session.query(
            WellProduction.date,
            db.func.sum(WellProduction.production).label('total_production')
        ).filter(
            WellProduction.date >= prev_start,
            WellProduction.date <= end_date
        ).group_by(WellProduction.date).all()
        prod_map = {r.date: float(r.total_production or 0) for r in well_rows}
        well_series = []
        for d in dates:
            prev_day = d - timedelta(days=1)
            today_sum = prod_map.get(d, 0.0)
            yesterday_sum = prod_map.get(prev_day, 0.0)
            if d.day == 1:
                # Ngày đầu tháng: sum(production) - 0
                val = float(today_sum)
            else:
                val = float(today_sum) - float(yesterday_sum)
            print(d.day,float(today_sum),float(yesterday_sum))
            if val < 0:
                val = 0.0
            well_series.append({'date': str(d), 'production': val})
        # well_series = [v if v >= 0 else 0 for v in well_series]
        # Sản lượng nước sạch theo ngày dùng _get_daily_production, clamp <0 thành 0
        clean_water_series = []
        for d in dates:
            daily_val = float(_get_daily_production(d, d - timedelta(days=1)))
            if daily_val < 0:
                daily_val = 0.0
            clean_water_series.append({'date': str(d), 'output': daily_val})
        wastewater_data = db.session.query(
            WastewaterPlant.date,
            db.func.sum(WastewaterPlant.input_flow_tqt).label('total_input'),
            db.func.sum(WastewaterPlant.output_flow_tqt).label('total_output')
        ).filter(WastewaterPlant.date >= start_date, WastewaterPlant.date <= end_date)\
         .group_by(WastewaterPlant.date).all()

       # Hai đồng hồ nước sạch (nếu có)
        r1 = func.coalesce(CustomerReading.clean_water_reading, 0)
        r2 = func.coalesce(getattr(CustomerReading, 'clean_water_reading_2', 0), 0)
        total_ns = r1 + r2

        lag_total_ns = func.lag(total_ns).over(
            partition_by=CustomerReading.customer_id,
            order_by=CustomerReading.date
        )
        delta_ns = case(
            (((total_ns - func.coalesce(lag_total_ns, total_ns)) < 0), 0),
            else_=(total_ns - func.coalesce(lag_total_ns, total_ns))
        ).label('delta_ns')

        # Nước thải: nếu có đồng hồ NT thì lấy delta theo đồng hồ; nếu không, tính theo tỉ lệ KH
        r_nt = func.coalesce(CustomerReading.wastewater_reading, 0)
        lag_nt = func.lag(r_nt).over(
            partition_by=CustomerReading.customer_id,
            order_by=CustomerReading.date
        )
        delta_nt_meter = case(
            (CustomerReading.wastewater_reading.is_(None), None),
            else_=case(
                (((r_nt - func.coalesce(lag_nt, r_nt)) < 0), 0),
                else_=(r_nt - func.coalesce(lag_nt, r_nt))
            )
        )

        # Subquery: delta theo từng KH/ngày (không lọc ngày ở đây để xử lý đúng biên ngày đầu kỳ)
        subq = (
            db.session.query(
                CustomerReading.customer_id.label('cid'),
                CustomerReading.date.label('d'),
                delta_ns,
                # nếu không có đồng hồ NT, tính theo tỉ lệ nước thải của KH
                func.coalesce(delta_nt_meter, delta_ns * Customer.water_ratio).label('delta_nt')
            )
            .join(Customer, Customer.id == CustomerReading.customer_id)
            .filter(
                Customer.is_active.is_(True),
                Customer.daily_reading.is_(True)
            )
        ).subquery()

        # Tổng theo ngày trong khoảng yêu cầu
        customer_data = (
            db.session.query(
                subq.c.d.label('date'),
                func.sum(subq.c.delta_ns).label('total_clean_water'),
                func.sum(subq.c.delta_nt).label('total_wastewater')
            )
            .filter(
                subq.c.d >= start_date,
                subq.c.d <= end_date
            )
            .group_by(subq.c.d)
            .order_by(subq.c.d)
            .all()
        )
        return jsonify({
            'well_production': well_series,
            'clean_water': clean_water_series,
            'wastewater': [{'date': str(d.date), 'input': float(d.total_input or 0), 'output': float(d.total_output or 0)} for d in wastewater_data],
            'customer_consumption': [{'date': str(d.date), 'clean_water': float(d.total_clean_water or 0), 'wastewater': float(d.total_wastewater or 0)} for d in customer_data]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/chart-details/<chart_type>')
@login_required
def chart_details(chart_type):
    chart_configs = {
        'wells': {'name':'Sản lượng tổng các giếng khoan theo ngày','icon':'fa-water','description':'Theo dõi sản lượng nước theo giếng khoan'},
        'clean-water': {'name':'Sản lượng nước sạch cấp cho Khách hàng','icon':'fa-tint','description':'Bao gồm nước từ giếng khoan + Jasan'},
        'wastewater': {'name':'Lưu lượng nước thải qua nhà máy xử lý','icon':'fa-recycle','description':'NMNT1/2'},
        'customers': {'name':'Tiêu thụ nước sạch của TOP 4 khách hàng lớn nhất','icon':'fa-users','description':'Nước sạch và nước thải'},
    }
    config = chart_configs.get(chart_type)
    if not config:
        flash('Loại biểu đồ không hợp lệ', 'error')
        return redirect(url_for('dashboard.dashboard'))
    wells_list = []
    plants_list = []
    customers_list = []
    if chart_type == 'wells':
        wells_list = Well.query.filter_by(is_active=True).order_by(Well.code).all()
    elif chart_type == 'wastewater':
        # Get unique plant numbers from database
        plants_query = db.session.query(WastewaterPlant.plant_number).distinct().order_by(WastewaterPlant.plant_number).all()
        plants_list = [{'number': p.plant_number, 'name': f'NMNT{p.plant_number}'} for p in plants_query]
    elif chart_type == 'customers':
        # Chỉ lấy KH đang hoạt động và có đọc số hằng ngày
        customers_q = (
            db.session.query(Customer.id, Customer.company_name)
            .filter(
                Customer.is_active == True,
                Customer.daily_reading == True   # hoặc == 1 nếu cột là Integer
            )
            .order_by(Customer.company_name)
            .all()
        )

        customers_list = [
            {'id': c.id, 'name': c.company_name}
            for c in customers_q
        ]

    
    return render_template('chart_details.html',
                           chart_type=chart_type,
                           chart_type_name=config['name'],
                           chart_icon=config['icon'],
                           chart_description=config['description'],
                           wells=wells_list,
                           plants=plants_list,
                           customers=customers_list)

@bp.route('/api/chart-details/<chart_type>')
@login_required
def api_chart_details(chart_type):
    try:
        days = request.args.get('days', 30, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date and end_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_dt = datetime.now().date()
            start_dt = end_dt - timedelta(days=days)

        if chart_type == 'wells':
            well_ids_param = request.args.get('well_ids')
            # Danh sách ID được chọn (nếu có)
            well_ids = [int(x) for x in well_ids_param.split(',') if x.strip().isdigit()] if well_ids_param else None
            # Chế độ tổng khi chọn tất cả (well_ids trống/None/'all') hoặc aggregate=1
            agg_flag = request.args.get('aggregate', '0').lower() in ('1', 'true', 'yes')
            aggregate = agg_flag or (well_ids_param in (None, '', 'all'))
            data = get_well_production_range(start_dt, end_dt, well_ids, aggregate=aggregate)

        elif chart_type == 'clean-water':
            data = generate_clean_water_details(start_dt, end_dt)
        elif chart_type == 'wastewater':
            plant_ids_param = request.args.get('plant_ids')
            plant_ids = [int(x) for x in plant_ids_param.split(',') if x.strip().isdigit()] if plant_ids_param else None
            aggregate = request.args.get('aggregate', '0').lower() in ('1', 'true', 'yes') or (plant_ids_param in (None, '', 'all'))
            data = generate_wastewater_details(start_dt, end_dt, plant_ids, aggregate=aggregate)
        elif chart_type == 'customers':
            customer_ids_param = request.args.get('customer_ids')
            customer_ids = [int(x) for x in customer_ids_param.split(',') if x.strip().isdigit()] if customer_ids_param else None
            # For customers: aggregate when no selection (top 10), individual when specific customer selected
            aggregate = customer_ids_param in (None, '', 'all')
            data = generate_customer_details(start_dt, end_dt, customer_ids, aggregate=aggregate)
        else:
            return jsonify({'error': 'Invalid chart type'}), 400
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in chart details API: {str(e)}")
        return jsonify({'error': 'Lỗi khi tải dữ liệu chi tiết'}), 500

def get_well_production_range(start_date, end_date, well_ids=None, aggregate=False):
    # Danh sách ngày
    dates = []
    cur = start_date
    while cur <= end_date:
        dates.append(cur)
        cur += timedelta(days=1)

    if aggregate:
        # 1) Tổng sản lượng theo ngày:
        total_series = []
        for d in dates:
            total_series.append(_clean_water_production_today(d))
        # Hiển thị: nếu giá trị âm thì đưa về 0
        total_series = [v if v >= 0 else 0 for v in total_series]
        # 2) Tổng công suất (tổng capacity của các giếng được tính)
        qw = db.session.query(Well)
        if well_ids:
            qw = qw.filter(Well.id.in_(well_ids))
        else:
            # Nếu không chỉ định, mặc định lấy giếng đang hoạt động (nếu có cột is_active)
            try:
                qw = qw.filter(Well.is_active.is_(True))
            except Exception:
                pass
        wells = qw.all()
        total_capacity = float(sum([float(getattr(w, 'capacity', 0) or 0) for w in wells]))
        capacity_series = [total_capacity for _ in dates]

        labels = [d.strftime('%d/%m') for d in dates]
        datasets = [
            {
                'label': 'Tổng sản lượng giếng (m³/ngày)',
                'data': total_series,
                'borderColor': 'rgb(33, 150, 243)',
                'backgroundColor': 'rgba(33, 150, 243, 0.15)',
                'fill': False,
                'tension': 0.3
            },
            {
                'label': 'Tổng công suất',
                'data': capacity_series,
                'borderColor': 'rgb(120, 120, 120)',
                'backgroundColor': 'rgba(0,0,0,0)',
                'fill': False,
                'tension': 0.0,
                'borderDash': [6, 6],
                'pointRadius': 0
            }
        ]

        total_each_day = total_series[:]  # chính là chuỗi tổng
        summary = {
            'total': sum(total_each_day),
            'average': (sum(total_each_day) / len(dates)) if dates else 0,
            'max': max(total_each_day) if total_each_day else 0,
            'min': min([v for v in total_each_day if v > 0]) if any(total_each_day) else 0
        }
        table_data = [{'date': d.strftime('%d/%m/%Y'), 'total': total_each_day[i]} for i, d in enumerate(dates)]

        return {'chart_data': {'labels': labels, 'datasets': datasets}, 'summary': summary, 'table_data': table_data}

    # ===== Chế độ mặc định: từng giếng + đường công suất từng giếng =====
    q = db.session.query(
        WellProduction.date, Well.id.label('well_id'), Well.code.label('well_code'),
        Well.capacity.label('capacity'), db.func.sum(WellProduction.production).label('production')
    ).join(Well).filter(WellProduction.date >= start_date, WellProduction.date <= end_date)
    if well_ids:
        q = q.filter(Well.id.in_(well_ids))
    q = q.group_by(WellProduction.date, Well.id, Well.code, Well.capacity).order_by(WellProduction.date, Well.code)
    rows = q.all()

    dates_set = sorted({r.date for r in rows} or dates)
    labels = [d.strftime('%d/%m') for d in dates_set]
    wells_map, capacities_map = {}, {}
    for r in rows:
        wells_map.setdefault(r.well_code, {})[r.date] = float(r.production or 0)
        capacities_map[r.well_code] = float(r.capacity or 0)

    palette = ['rgb(54,162,235)', 'rgb(255,99,132)', 'rgb(75,192,192)', 'rgb(255,206,86)', 'rgb(153,102,255)', 'rgb(255,159,64)']
    datasets, well_colors = [], {}
    for i, (code, date_dict) in enumerate(sorted(wells_map.items())):
        color = palette[i % len(palette)]
        well_colors[code] = color
        # Tính sản lượng theo từng giếng: today - yesterday; nếu là ngày 1 thì lấy today
        series = []
        for d in dates_set:
            cur = float(date_dict.get(d, 0) or 0)
            if d.day == 1:
                val = cur
            else:
                prev = d - timedelta(days=1)
                prev_val = float(date_dict.get(prev, 0) or 0)
                val = cur - prev_val
            series.append(val)
        # Hiển thị: nếu giá trị âm thì đưa về 0
        series = [v if v >= 0 else 0 for v in series]

        datasets.append({
            'label': code,
            'data': series,
            'borderColor': color,
            'backgroundColor': color.replace('rgb', 'rgba').replace(')', ',0.15)'),
            'fill': False,
            'tension': 0.3
        })
    for code, cap in sorted(capacities_map.items()):
        color = well_colors.get(code, 'rgb(100,100,100)')
        datasets.append({
            'label': f'{code} - Công suất',
            'data': [cap for _ in dates_set],
            'borderColor': color,
            'backgroundColor': 'rgba(0,0,0,0)',
            'fill': False,
            'tension': 0.0,
            'borderDash': [6, 6],
            'pointRadius': 0
        })

    total_each_day = [sum(ds['data'][idx] for ds in datasets if 'Công suất' not in ds['label']) for idx in range(len(labels))]
    summary = {
        'total': sum(total_each_day),
        'average': (sum(total_each_day)/len(dates)) if dates else 0,
        'max': max(total_each_day) if total_each_day else 0,
        'min': min([v for v in total_each_day if v > 0]) if any(total_each_day) else 0
    }
    table_data = []
    for idx, d in enumerate(dates_set):
        row = {'date': d.strftime('%d/%m/%Y')}
        daily_total = 0
        for ds in datasets:
            if 'Công suất' in ds['label']: 
                continue
            v = ds['data'][idx]
            row[ds['label']] = v
            daily_total += v
        row['total'] = daily_total
        table_data.append(row)

    return {'chart_data': {'labels': labels, 'datasets': datasets}, 'summary': summary, 'table_data': table_data}

def generate_clean_water_details(start_date, end_date):
    """Generate clean water production details from database"""
    # Generate date range
    dates = []
    cur = start_date
    while cur <= end_date:
        dates.append(cur)
        cur += timedelta(days=1)
    
    # Query clean water plant data for table breakdown
    query = CleanWaterPlant.query.filter(
        CleanWaterPlant.date >= start_date,
        CleanWaterPlant.date <= end_date
    ).order_by(CleanWaterPlant.date).all()

    # Generate chart series using _get_daily_production for each day
    data = []
    for d in dates:
        daily_val = _clean_water_production_today(d)
        daily_jasan = _get_today_jasan(d)
        data.append(float(daily_val + daily_jasan))
    # Hiển thị trên chart: nếu giá trị âm thì = 0
    data = [v if v >= 0 else 0 for v in data]
    
    # Calculate summary statistics
    non_zero_data = [v for v in data if v > 0]
    summary = {
        'total': sum(data),
        'average': sum(data) / len(dates) if dates else 0,
        'max': max(data) if data else 0,
        'min': min(non_zero_data) if non_zero_data else 0
    }
    
    # Generate chart data
    chart_data = {
        'labels': [d.strftime('%d/%m') for d in dates],
        'datasets': [{
            'label': 'Sản lượng nước sạch theo ngày (m³)',
            'data': data,
            'backgroundColor': 'rgba(75, 192, 192, 0.6)',
            'borderColor': 'rgb(75, 192, 192)',
            'borderWidth': 1,
            'fill': False,
            'tension': 0.3
        }]
    }
    
    # Generate table data with breakdown
    table_data = []
    for i, d in enumerate(dates):
        record = None
        for r in query:
            if r.date == d:
                record = r
                break
        
        # Lấy Jasan thô (J(n))
        jasan_raw = float(record.raw_water_jasan or 0) if record else 0.0

        # H(n): tổng sản lượng giếng trong ngày n (today - yesterday)
        wells_delta = float(_clean_water_production_today(d))

        # (M4+N4+O4)-(M5+N5+O5): tồn kho hôm qua - hôm nay
        prev_day = d - timedelta(days=1)
        inventory_yesterday = float(_get_tank_inventory_yesterday(prev_day))
        inventory_today = float(_get_tank_inventory_today(d))

        print(inventory_yesterday,inventory_today)

        # 2.2 Nước sạch cấp cho KH trong ngày
        total = 0.98 * max(wells_delta - jasan_raw, 0.0) + (inventory_yesterday - inventory_today)

        # Nếu cần, vẫn hiển thị riêng clean_output đã lưu trong DB (nếu có)
        clean_output = float(record.clean_water_output or 0) if record else 0.0

        table_data.append({
            'date': d.strftime('%d/%m/%Y'),
            'clean_water_output': clean_output,
            'raw_water_jasan': jasan_raw,
            'total_water': total,
            #debug only
            # 'wells_delta':wells_delta,
            # 'jasan_raw':jasan_raw, 
            # 'inventory_yesterday':inventory_yesterday,
            # 'inventory_today':inventory_today
        })

    
    return {
        'chart_data': chart_data,
        'summary': summary,
        'table_data': table_data
    }

def generate_wastewater_details(start_date, end_date, plant_ids=None, aggregate=False):
    """Generate wastewater treatment plant details with filtering by plant"""
    # Generate date range
    dates = []
    cur = start_date
    while cur <= end_date:
        dates.append(cur)
        cur += timedelta(days=1)

    if aggregate:
        # Aggregate mode: show total input/output across selected plants
        query = db.session.query(
            WastewaterPlant.date,
            db.func.sum(WastewaterPlant.input_flow_tqt).label('total_input'),
            db.func.sum(WastewaterPlant.output_flow_tqt).label('total_output')
        ).filter(WastewaterPlant.date >= start_date, WastewaterPlant.date <= end_date)
        
        if plant_ids:
            query = query.filter(WastewaterPlant.plant_number.in_(plant_ids))
        
        rows = query.group_by(WastewaterPlant.date).order_by(WastewaterPlant.date).all()
        
        # Create data maps
        input_map = {r.date: float(r.total_input or 0) for r in rows}
        output_map = {r.date: float(r.total_output or 0) for r in rows}
        
        # Generate data series
        input_data = [input_map.get(d, 0.0) for d in dates]
        output_data = [output_map.get(d, 0.0) for d in dates]
        
        labels = [d.strftime('%d/%m') for d in dates]
        datasets = [
            {
                'label': 'Tổng nước thải đầu vào (m³)',
                'data': input_data,
                'borderColor': 'rgb(255, 99, 132)',
                'backgroundColor': 'rgba(255, 99, 132, 0.1)',
                'fill': False,
                'tension': 0.4
            },
            {
                'label': 'Tổng nước thải đầu ra (m³)',
                'data': output_data,
                'borderColor': 'rgb(54, 162, 235)',
                'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                'fill': False,
                'tension': 0.4
            }
        ]
        
        # --- CHANGED: Summary = chỉ lấy đầu vào ---
        valid_inputs = [v for v in input_data if v > 0]
        total_input = sum(input_data)
        summary = {
            'total': total_input,
            'average': (total_input / len(dates)) if dates else 0,
            'max': max(valid_inputs) if valid_inputs else 0,
            'min': min(valid_inputs) if valid_inputs else 0
        }
        # -----------------------------------------

        # Table data
        table_data = [
            {
                'date': d.strftime('%d/%m/%Y'),
                'input_flow': input_data[i],
                'output_flow': output_data[i]
            }
            for i, d in enumerate(dates)
        ]
        
        return {
            'chart_data': {'labels': labels, 'datasets': datasets},
            'summary': summary,
            'table_data': table_data
        }
    
    else:
        # Individual plants mode: show each plant separately
        query = db.session.query(
            WastewaterPlant.date,
            WastewaterPlant.plant_number,
            WastewaterPlant.input_flow_tqt,
            WastewaterPlant.output_flow_tqt
        ).filter(WastewaterPlant.date >= start_date, WastewaterPlant.date <= end_date)
        
        if plant_ids:
            query = query.filter(WastewaterPlant.plant_number.in_(plant_ids))
        
        rows = query.order_by(WastewaterPlant.date, WastewaterPlant.plant_number).all()
        
        # Organize data by plant
        plants_input = {}
        plants_output = {}
        for r in rows:
            plant_key = f"NMNT{r.plant_number}"
            if plant_key not in plants_input:
                plants_input[plant_key] = {}
                plants_output[plant_key] = {}
            plants_input[plant_key][r.date] = float(r.input_flow_tqt or 0)
            plants_output[plant_key][r.date] = float(r.output_flow_tqt or 0)
        
        labels = [d.strftime('%d/%m') for d in dates]
        datasets = []
        
        # Color palette for plants
        colors = ['rgb(255, 99, 132)', 'rgb(54, 162, 235)', 'rgb(75, 192, 192)', 'rgb(255, 206, 86)']
        color_idx = 0
        
        # Add input datasets
        for plant_name in sorted(plants_input.keys()):
            color = colors[color_idx % len(colors)]
            datasets.append({
                'label': f'{plant_name} - Đầu vào (m³)',
                'data': [plants_input[plant_name].get(d, 0) for d in dates],
                'borderColor': color,
                'backgroundColor': color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
                'fill': False,
                'tension': 0.4
            })
            color_idx += 1
        
        # Add output datasets
        color_idx = 0
        for plant_name in sorted(plants_output.keys()):
            color = colors[color_idx % len(colors)]
            datasets.append({
                'label': f'{plant_name} - Đầu ra (m³)',
                'data': [plants_output[plant_name].get(d, 0) for d in dates],
                'borderColor': color,
                'backgroundColor': 'rgba(0,0,0,0)',
                'fill': False,
                'tension': 0.4,
                'borderDash': [5, 5]
            })
            color_idx += 1
        
        # --- CHANGED: Summary = chỉ lấy đầu vào (tổng tất cả NMNT) ---
        input_total_each_day = []
        for d in dates:
            daily_input_sum = sum(plants_input[plant].get(d, 0) for plant in plants_input.keys())
            input_total_each_day.append(daily_input_sum)

        valid_daily_inputs = [v for v in input_total_each_day if v > 0]
        total_input = sum(input_total_each_day)
        summary = {
            'total': total_input,
            'average': (total_input / len(dates)) if dates else 0,
            'max': max(valid_daily_inputs) if valid_daily_inputs else 0,
            'min': min(valid_daily_inputs) if valid_daily_inputs else 0
        }
        # -------------------------------------------------------------

        # Table data with columns for each plant
        table_data = []
        for i, d in enumerate(dates):
            row = {'date': d.strftime('%d/%m/%Y')}
            for plant_name in sorted(plants_input.keys()):
                row[f'{plant_name}_input'] = plants_input[plant_name].get(d, 0)
                row[f'{plant_name}_output'] = plants_output[plant_name].get(d, 0)
            table_data.append(row)
        
        return {
            'chart_data': {'labels': labels, 'datasets': datasets},
            'summary': summary,
            'table_data': table_data
        }



# Lấy số lượng nước tiêu thụ của khách hàng
def generate_customer_details(start_date, end_date, customer_ids=None, aggregate=False):
    """Generate customer consumption details WITH daily-reading customers only (delta = sau - trước)"""

    # --- Dải ngày để fill dữ liệu trống ---
    dates = []
    calc_start = start_date - timedelta(days=1)
    cur = start_date
    while cur <= end_date:
        dates.append(cur)
        cur += timedelta(days=1)

    # Đồng hồ 1
    r1 = func.coalesce(CustomerReading.clean_water_reading, 0)
    lag_r1 = func.lag(r1).over(
        partition_by=CustomerReading.customer_id,
        order_by=CustomerReading.date
    )
    delta1 = case(
        (((r1 - func.coalesce(lag_r1, r1)) < 0), 0),
        else_=(r1 - func.coalesce(lag_r1, r1))
    )

    # Đồng hồ 2 (có thể null với KH chỉ có 1 đồng hồ)
    r2 = func.coalesce(getattr(CustomerReading, "clean_water_reading_2", 0), 0)
    lag_r2 = func.lag(r2).over(
        partition_by=CustomerReading.customer_id,
        order_by=CustomerReading.date
    )
    delta2 = case(
        (((r2 - func.coalesce(lag_r2, r2)) < 0), 0),
        else_=(r2 - func.coalesce(lag_r2, r2))
    )
    companies_NHY = [
        'Cty TNHH Dệt và Nhuộm Hưng Yên',    # Áp hệ số: đồng hồ 1 * 10, đồng hồ 2 * 1
    ]
    companies_LH = [
        'Cty TNHH dệt may Lee Hing Việt Nam'    # Áp hệ số: đồng hồ 1, đồng hồ 2 * 10
    ]

    clean_delta_expr = case(
        (Customer.company_name.in_(companies_NHY), (delta1 * 10) + delta2),
        (Customer.company_name.in_(companies_LH), delta1 + delta2*10),
        else_=delta1
    )

    # Tổng chỉ số NT dùng để trừ: ưu tiên đồng hồ, không có thì dùng tính theo tỉ lệ
    total_waste = func.coalesce(CustomerReading.wastewater_reading,
                                CustomerReading.wastewater_calculated)

    # Chỉ số ngày trước theo cùng quy tắc
    lag_total_waste = func.lag(total_waste).over(
        partition_by=CustomerReading.customer_id,
        order_by=CustomerReading.date
    )

    # Delta ngày = max(curr - prev, 0) ; nếu không có ngày trước thì = 0
    wastewater_delta_expr = case(
        (((total_waste - func.coalesce(lag_total_waste, total_waste)) < 0), 0),
        else_=(total_waste - func.coalesce(lag_total_waste, total_waste))
    )


    # --- Subquery tính delta (chưa lọc theo customer_ids để có thể lấy Top 4) ---
    delta_sq_all = (
        db.session.query(
            CustomerReading.date.label('date'),
            CustomerReading.customer_id.label('customer_id'),
            Customer.company_name.label('company_name'),
            clean_delta_expr.label('clean_delta'),
            wastewater_delta_expr.label('wastewater_delta')
        )
        .join(Customer, Customer.id == CustomerReading.customer_id)
        .filter(
            CustomerReading.date >= calc_start,
            CustomerReading.date <= end_date,
            Customer.is_active.is_(True),
            Customer.daily_reading.is_(True),
        )
        .subquery()
    )

    # --- Tự chọn Top 4 nếu cần (dựa trên tổng clean_delta) ---
    if aggregate and not customer_ids:
        top4_rows = (
            db.session.query(
                delta_sq_all.c.customer_id,
                func.sum(delta_sq_all.c.clean_delta).label('sum_clean_delta')
            )
            .group_by(delta_sq_all.c.customer_id)
            .order_by(func.sum(delta_sq_all.c.clean_delta).desc())
            .limit(4)
            .all()
        )
        customer_ids = [r.customer_id for r in top4_rows] or None

    # --- Subquery delta cuối (có thể lọc theo customer_ids nếu truyền/đã xác định Top4)---
    delta_sq = (
        db.session.query(
            delta_sq_all.c.date,
            delta_sq_all.c.customer_id,
            delta_sq_all.c.company_name,
            delta_sq_all.c.clean_delta,
            delta_sq_all.c.wastewater_delta
        )
        .filter(
            delta_sq_all.c.date >= start_date,
            *( [delta_sq_all.c.customer_id.in_(customer_ids)] if customer_ids else [] ))
        .subquery()
    )

    labels = [d.strftime('%d/%m') for d in dates]

    if aggregate:
        # --- Tổng hợp theo NGÀY trên delta_sq ---
        rows = (
            db.session.query(
                delta_sq.c.date,
                func.sum(delta_sq.c.clean_delta).label('total_clean'),
                func.sum(delta_sq.c.wastewater_delta).label('total_waste')
            )
            .group_by(delta_sq.c.date)
            .order_by(delta_sq.c.date)
        ).all()

        clean_map = {r.date: float(r.total_clean or 0) for r in rows}
        wastewater_map = {r.date: float(r.total_waste or 0) for r in rows}

        clean_data = [clean_map.get(d, 0.0) for d in dates]
        wastewater_data = [wastewater_map.get(d, 0.0) for d in dates]

        datasets = [
            {
                'label': 'Tổng nước sạch tiêu thụ (m³)',
                'data': clean_data,
                'borderColor': 'rgb(54, 162, 235)',
                'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                'fill': False,
                'tension': 0.4
            },
            {
                'label': 'Tổng nước thải phát sinh (m³)',
                'data': wastewater_data,
                'borderColor': 'rgb(255, 206, 86)',
                'backgroundColor': 'rgba(255, 206, 86, 0.1)',
                'fill': False,
                'tension': 0.4
            }
        ]

        summary = {
            'total': sum(clean_data),
            'average': (sum(clean_data) / len(dates)) if dates else 0,
            'max': max(clean_data) if clean_data else 0,
            'min': min([v for v in clean_data if v > 0]) if any(clean_data) else 0
        }

        table_data = [
            {'date': d.strftime('%d/%m/%Y'), 'clean_water': clean_data[i], 'wastewater': wastewater_data[i]}
            for i, d in enumerate(dates)
        ]

        return {
            'chart_data': {'labels': labels, 'datasets': datasets},
            'summary': summary,
            'table_data': table_data
        }

    # --- Chế độ từng khách: tách series theo khách từ delta_sq ---
    rows = (
        db.session.query(
            delta_sq.c.date,
            delta_sq.c.customer_id,
            delta_sq.c.company_name,
            delta_sq.c.clean_delta,
            delta_sq.c.wastewater_delta
        )
        .order_by(delta_sq.c.date, delta_sq.c.company_name)
    ).all()

    customers_clean = {}
    customers_wastewater = {}
    for r in rows:
        k = r.company_name
        customers_clean.setdefault(k, {})[r.date] = float(r.clean_delta or 0)
        customers_wastewater.setdefault(k, {})[r.date] = float(r.wastewater_delta or 0)

    colors = [
        'rgb(54, 162, 235)', 'rgb(255, 99, 132)', 'rgb(75, 192, 192)', 'rgb(255, 206, 86)',
        'rgb(153, 102, 255)', 'rgb(255, 159, 64)', 'rgb(199, 199, 199)', 'rgb(83, 102, 255)',
        'rgb(255, 99, 255)', 'rgb(99, 255, 132)'
    ]
    datasets = []
    # NS theo khách
    for idx, name in enumerate(sorted(customers_clean.keys())):
        color = colors[idx % len(colors)]
        datasets.append({
            'label': f'{name} - Nước sạch (m³)',
            'data': [customers_clean[name].get(d, 0) for d in dates],
            'borderColor': color,
            'backgroundColor': color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
            'fill': False,
            'tension': 0.4
        })
    # NT theo khách (dashed)
    for idx, name in enumerate(sorted(customers_wastewater.keys())):
        color = colors[idx % len(colors)]
        datasets.append({
            'label': f'{name} - Nước thải (m³)',
            'data': [customers_wastewater[name].get(d, 0) for d in dates],
            'borderColor': color,
            'backgroundColor': 'rgba(0,0,0,0)',
            'fill': False,
            'tension': 0.4,
            'borderDash': [5, 5]
        })

    # Summary
    clean_values = []
    all_values = []
    for _, mp in customers_clean.items():
        vals = list(mp.values())
        clean_values.extend(vals)
        all_values.extend(vals)
    for _, mp in customers_wastewater.items():
        all_values.extend(mp.values())

    summary = {
        'total': sum(clean_values),
        'average': (sum(clean_values) / len(dates)) if dates else 0,
        'max': max(clean_values) if clean_values else 0,
        'min': min([v for v in clean_values if v > 0]) if any(clean_values) else 0
    }

    # Bảng dữ liệu theo ngày
    table_data = []
    for d in dates:
        row = {'date': d.strftime('%d/%m/%Y')}
        total_clean = 0.0
        total_waste = 0.0
        for name in sorted(customers_clean.keys()):
            clean_val = customers_clean[name].get(d, 0.0)
            waste_val = customers_wastewater[name].get(d, 0.0)
            short = name[:15] + "..." if len(name) > 15 else name
            row[f'{short}_clean'] = clean_val
            row[f'{short}_waste'] = waste_val
            total_clean += clean_val
            total_waste += waste_val
        # row['total_clean'] = total_clean
        # row['total_wastewater'] = total_waste
        table_data.append(row)

    return {
        'chart_data': {'labels': labels, 'datasets': datasets},
        'summary': summary,
        'table_data': table_data
    }


@bp.route('/api/summary-six-lines')
@login_required
def summary_six_lines():
    # --- Giới hạn quyền ()---
    if current_user.username not in ['tonggiamdoc11', 'admin11']:
        return jsonify({'error': 'forbidden'}), 403

    # --- Nhận khoảng thời gian từ query ---
    start_str = request.args.get('start_date')
    end_str = request.args.get('end_date')
    try:
        if start_str and end_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        else:
            # Mặc định kỳ 25 gần nhất
            today = date.today()
            if today.day >= 25:
                start_date = today.replace(day=25)
            else:
                prev_month = today.replace(day=1) - timedelta(days=1)
                start_date = prev_month.replace(day=25)
            end_date = start_date + timedelta(days=30)
    except Exception:
        return jsonify({'error': 'invalid_date'}), 400

    # --- Lấy dữ liệu ---
    wells = db.session.query(
        WellProduction.date, db.func.sum(WellProduction.production)
    ).filter(WellProduction.date >= start_date, WellProduction.date <= end_date).group_by(WellProduction.date).all()

    clean = db.session.query(
        CleanWaterPlant.date,
        db.func.sum(CleanWaterPlant.clean_water_output),
        db.func.sum(CleanWaterPlant.pac_usage + CleanWaterPlant.naoh_usage + CleanWaterPlant.polymer_usage)
    ).filter(CleanWaterPlant.date >= start_date, CleanWaterPlant.date <= end_date).group_by(CleanWaterPlant.date).all()

    cust = db.session.query(
        CustomerReading.date,
        db.func.sum(CustomerReading.clean_water_reading),
        db.func.sum(db.case(
            (CustomerReading.wastewater_reading.isnot(None), CustomerReading.wastewater_reading),
            else_=CustomerReading.wastewater_calculated
        ))
    ).filter(CustomerReading.date >= start_date, CustomerReading.date <= end_date).group_by(CustomerReading.date).all()

    waste = db.session.query(
        WastewaterPlant.date,
        db.func.sum(WastewaterPlant.output_flow_tqt),
        db.func.sum(WastewaterPlant.sludge_output),
        db.func.sum(WastewaterPlant.chemical_usage)
    ).filter(WastewaterPlant.date >= start_date, WastewaterPlant.date <= end_date).group_by(WastewaterPlant.date).all()

    # --- Tổng hợp ---
    days = sorted({d for s in [wells, clean, cust, waste] for d, *_ in s})
    data = defaultdict(lambda: dict(well=0, clean=0, cust=0, waste=0, chem=0, sludge=0))
    for d, v in wells: data[d]['well'] = v
    for d, v, c in clean: data[d]['clean'] = v; data[d]['chem'] += c
    for d, v1, v2 in cust: data[d]['cust'] = v1; data[d]['waste'] += v2
    for d, v1, v2, v3 in waste: data[d]['waste'] += v1; data[d]['sludge'] += v2; data[d]['chem'] += v3

    labels = [d.strftime('%d/%m') for d in days]
    values = [data[d] for d in days]
    datasets = [
        {'label': 'Giếng khoan', 'data': [x['well'] for x in values], 'borderColor': '#007bff', 'fill': False},
        {'label': 'Nước sạch', 'data': [x['clean'] for x in values], 'borderColor': '#28a745', 'fill': False},
        {'label': 'Nước cấp KH', 'data': [x['cust'] for x in values], 'borderColor': '#ffc107', 'fill': False},
        {'label': 'Nước thải', 'data': [x['waste'] for x in values], 'borderColor': '#dc3545', 'fill': False},
        {'label': 'Hóa chất NMNS', 'data': [x['chem'] for x in values], 'borderColor': '#6610f2', 'borderDash': [5,5], 'fill': False},
        {'label': 'Tổng hợp (NT+HC+BT)', 'data': [x['waste']+x['chem']+x['sludge'] for x in values], 'borderColor': '#20c997', 'fill': False}
    ]

    return jsonify({
        'labels': labels,
        'datasets': datasets,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    })

@bp.route('/api/customer-details', methods=['GET'], endpoint='customer_details_api')
def customer_details_api():
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    if not start or not end:
        return jsonify({'error': 'start_date and end_date are required (YYYY-MM-DD).'}), 400

    try:
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
        if start_date > end_date:
            return jsonify({'error': 'start_date must be <= end_date'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    ids_raw = request.args.get('customer_ids', '')
    aggregate = (request.args.get('aggregate', '0') == '1')

    # Parse customer_ids (tối đa 4)
    customer_ids = [int(x) for x in ids_raw.split(',') if x.strip().isdigit()] if ids_raw else None
    if customer_ids:
        valid_ids = [
            c.id for c in db.session.query(Customer.id)
            .filter(
                Customer.id.in_(customer_ids),
                Customer.is_active == True,
                Customer.daily_reading == True
            ).all()
        ]
        customer_ids = valid_ids[:4] if valid_ids else None

    # Nếu không chọn khách hàng → chọn Top 4 trong nhóm hàng ngày
    if not customer_ids:
        top4_rows = (
            db.session.query(
                Customer.id.label('cid'),
                db.func.sum(
                    CustomerReading.clean_water_reading +
                    db.func.coalesce(CustomerReading.clean_water_reading_2, 0)
                ).label('sum_clean')
            )
            .join(Customer)
            .filter(
                Customer.is_active == True,
                Customer.daily_reading == True, 
                CustomerReading.date >= start_date,
                CustomerReading.date <= end_date,
            )
            .group_by(Customer.id)
            .order_by(db.desc('sum_clean'))
            .limit(4)
            .all()
        )
        customer_ids = [r.cid for r in top4_rows] or None

    # Gọi hàm sinh dữ liệu (đã có điều kiện daily_reading bên trong)
    data = generate_customer_details(
        start_date, end_date,
        customer_ids=customer_ids,
        aggregate=aggregate
    )

    return jsonify(data)

