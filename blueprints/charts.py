import logging, random
from datetime import datetime, date, timedelta
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from models import Well, WellProduction, CleanWaterPlant, WastewaterPlant, CustomerReading, Customer

bp = Blueprint('charts', __name__)
logger = logging.getLogger(__name__)


@bp.route('/api/kpi-data')
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
        well_data = db.session.query(
            WellProduction.date, db.func.sum(WellProduction.production).label('total_production')
        ).filter(WellProduction.date >= start_date, WellProduction.date <= end_date)\
         .group_by(WellProduction.date).all()
        clean_water_data = CleanWaterPlant.query.filter(
            CleanWaterPlant.date >= start_date, CleanWaterPlant.date <= end_date
        ).all()
        wastewater_data = db.session.query(
            WastewaterPlant.date,
            db.func.sum(WastewaterPlant.input_flow_tqt).label('total_input'),
            db.func.sum(WastewaterPlant.output_flow_tqt).label('total_output')
        ).filter(WastewaterPlant.date >= start_date, WastewaterPlant.date <= end_date)\
         .group_by(WastewaterPlant.date).all()
        customer_data = db.session.query(
            CustomerReading.date,
            db.func.sum(CustomerReading.clean_water_reading).label('total_clean_water'),
            db.func.sum(
                db.case((CustomerReading.wastewater_reading.isnot(None), CustomerReading.wastewater_reading),
                        else_=CustomerReading.wastewater_calculated)
            ).label('total_wastewater')
        ).filter(CustomerReading.date >= start_date, CustomerReading.date <= end_date)\
         .group_by(CustomerReading.date).all()
        return jsonify({
            'well_production': [{'date': str(d.date), 'production': float(d.total_production or 0)} for d in well_data],
            'clean_water': [{'date': str(d.date), 'output': float(d.clean_water_output or 0)} for d in clean_water_data],
            'wastewater': [{'date': str(d.date), 'input': float(d.total_input or 0), 'output': float(d.total_output or 0)} for d in wastewater_data],
            'customer_consumption': [{'date': str(d.date), 'clean_water': float(d.total_clean_water or 0), 'wastewater': float(d.total_wastewater or 0)} for d in customer_data]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/chart-details/<chart_type>')
@login_required
def chart_details(chart_type):
    chart_configs = {
        'wells': {'name':'Sản lượng tổng các giếng khoan theo ngày','icon':'fa-water','description':'Theo dõi sản lượng nước'},
        'clean-water': {'name':'Sản lượng nước sạch từ nhà máy','icon':'fa-tint','description':'Bao gồm nước từ giếng khoan + Jasan'},
        'wastewater': {'name':'Lưu lượng nước thải qua nhà máy xử lý','icon':'fa-recycle','description':'NMNT1/2'},
        'customers': {'name':'Tiêu thụ nước của khách hàng','icon':'fa-users','description':'Nước sạch và nước thải'},
    }
    config = chart_configs.get(chart_type)
    if not config:
        flash('Loại biểu đồ không hợp lệ', 'error')
        return redirect(url_for('dashboard.dashboard'))
    wells_list = []
    if chart_type == 'wells':
        wells_list = Well.query.filter_by(is_active=True).order_by(Well.code).all()
    return render_template('chart_details.html',
                           chart_type=chart_type,
                           chart_type_name=config['name'],
                           chart_icon=config['icon'],
                           chart_description=config['description'],
                           wells=wells_list)

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
            well_ids = [int(x) for x in well_ids_param.split(',') if x.strip().isdigit()] if well_ids_param else None
            data = get_well_production_range(start_dt, end_dt, well_ids)
        elif chart_type == 'clean-water':
            data = generate_clean_water_details(start_dt, end_dt)
        elif chart_type == 'wastewater':
            data = generate_wastewater_details(start_dt, end_dt)
        elif chart_type == 'customers':
            data = generate_customer_details(start_dt, end_dt)
        else:
            return jsonify({'error': 'Invalid chart type'}), 400
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in chart details API: {str(e)}")
        return jsonify({'error': 'Lỗi khi tải dữ liệu chi tiết'}), 500

def get_well_production_range(start_date, end_date, well_ids=None):
    q = db.session.query(
        WellProduction.date, Well.id.label('well_id'), Well.code.label('well_code'),
        Well.capacity.label('capacity'), db.func.sum(WellProduction.production).label('production')
    ).join(Well).filter(WellProduction.date >= start_date, WellProduction.date <= end_date)
    if well_ids: q = q.filter(Well.id.in_(well_ids))
    q = q.group_by(WellProduction.date, Well.id, Well.code, Well.capacity).order_by(WellProduction.date, Well.code)
    rows = q.all()
    dates_set = sorted({r.date for r in rows})
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
        datasets.append({'label': code,'data':[date_dict.get(d,0) for d in dates_set],
                         'borderColor': color,'backgroundColor': color.replace('rgb','rgba').replace(')',',0.15)'),
                         'fill': False,'tension': 0.3})
    for code, cap in sorted(capacities_map.items()):
        color = well_colors.get(code, 'rgb(100,100,100)')
        datasets.append({'label': f'{code} - Công suất','data':[cap for _ in dates_set],
                         'borderColor': color,'backgroundColor':'rgba(0,0,0,0)',
                         'fill': False,'tension': 0.0,'borderDash':[6,6],'pointRadius':0})
    total_each_day = [sum(ds['data'][idx] for ds in datasets if 'Công suất' not in ds['label']) for idx in range(len(labels))]
    summary = {'total': sum(total_each_day), 'average': (sum(total_each_day)/len(total_each_day)) if total_each_day else 0,
               'max': max(total_each_day) if total_each_day else 0,
               'min': min([v for v in total_each_day if v > 0]) if any(total_each_day) else 0}
    table_data=[]
    for idx, d in enumerate(dates_set):
        row={'date': d.strftime('%d/%m/%Y')}; daily_total=0
        for ds in datasets:
            if 'Công suất' in ds['label']: continue
            v = ds['data'][idx]; row[ds['label']] = v; daily_total += v
        row['total'] = daily_total; table_data.append(row)
    return {'chart_data': {'labels': labels,'datasets': datasets}, 'summary': summary, 'table_data': table_data}

def generate_clean_water_details(start_date, end_date):
    dates=[]; cur=start_date
    while cur<=end_date: dates.append(cur); cur+=timedelta(days=1)
    data=[random.uniform(9000,12000) for _ in dates]
    return {'chart_data': {'labels':[d.strftime('%d/%m') for d in dates],
                           'datasets':[{'label':'Nước sạch sản xuất (m³)','data':data,'backgroundColor':'rgba(75, 192, 192, 0.6)','borderColor':'rgb(75, 192, 192)','borderWidth':1}]},
            'summary': {'total': sum(data), 'average': sum(data)/len(dates), 'max': max(data), 'min': min(data)},
            'table_data': [{'date': d.strftime('%d/%m/%Y'), 'clean_water_output': data[i]} for i, d in enumerate(dates)]}

def generate_wastewater_details(start_date, end_date):
    dates=[]; cur=start_date
    while cur<=end_date: dates.append(cur); cur+=timedelta(days=1)
    input_data=[random.uniform(15000,18000) for _ in dates]
    output_data=[random.uniform(14000,17000) for _ in dates]
    return {'chart_data': {'labels': [d.strftime('%d/%m') for d in dates],
                           'datasets': [{'label':'Nước thải đầu vào (m³)','data':input_data,'borderColor':'rgb(255, 99, 132)','backgroundColor':'rgba(255, 99, 132, 0.1)','fill':False,'tension':0.4},
                                        {'label':'Nước thải đầu ra (m³)','data':output_data,'borderColor':'rgb(54, 162, 235)','backgroundColor':'rgba(54, 162, 235, 0.1)','fill':False,'tension':0.4}]},
            'summary': {'total': sum(input_data)+sum(output_data), 'average': (sum(input_data)+sum(output_data))/(2*len(dates)),
                        'max': max(max(input_data), max(output_data)), 'min': min(min(input_data), min(output_data))},
            'table_data': [{'date': d.strftime('%d/%m/%Y'), 'input_flow': input_data[i], 'output_flow': output_data[i]} for i, d in enumerate(dates)]}

def generate_customer_details(start_date, end_date):
    dates=[]; cur=start_date
    while cur<=end_date: dates.append(cur); cur+=timedelta(days=1)
    clean=[random.uniform(8000,11000) for _ in dates]; waste=[random.uniform(7000,10000) for _ in dates]
    return {'chart_data': {'labels':[d.strftime('%d/%m') for d in dates],
                           'datasets':[{'label':'Nước sạch tiêu thụ (m³)','data':clean,'borderColor':'rgb(54, 162, 235)','backgroundColor':'rgba(54, 162, 235, 0.1)','fill':False,'tension':0.4},
                                       {'label':'Nước thải phát sinh (m³)','data':waste,'borderColor':'rgb(255, 206, 86)','backgroundColor':'rgba(255, 206, 86, 0.1)','fill':False,'tension':0.4}]},
            'summary': {'total': sum(clean)+sum(waste), 'average': (sum(clean)+sum(waste))/(2*len(dates)),
                        'max': max(max(clean), max(waste)), 'min': min(min(clean), min(waste))},
            'table_data': [{'date': d.strftime('%d/%m/%Y'), 'clean_water': clean[i], 'wastewater': waste[i]} for i, d in enumerate(dates)]}