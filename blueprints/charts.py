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
        # Optional date param to view historical KPI
        date_str = request.args.get('date')
        today = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
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
            # Total = clean_water_output + raw_water_jasan for consistency with details page
            'clean_water': [
                {
                    'date': str(d.date),
                    'output': float((d.clean_water_output or 0)) + float((d.raw_water_jasan or 0))
                }
                for d in clean_water_data
            ],
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
    plants_list = []
    customers_list = []
    if chart_type == 'wells':
        wells_list = Well.query.filter_by(is_active=True).order_by(Well.code).all()
    elif chart_type == 'wastewater':
        # Get unique plant numbers from database
        plants_query = db.session.query(WastewaterPlant.plant_number).distinct().order_by(WastewaterPlant.plant_number).all()
        plants_list = [{'number': p.plant_number, 'name': f'NMNT{p.plant_number}'} for p in plants_query]
    elif chart_type == 'customers':
        # Get top 4 customers by total consumption in last 30 days
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        top_customers_query = db.session.query(
            Customer.id,
            Customer.company_name,
            db.func.sum(CustomerReading.clean_water_reading).label('total_clean_water')
        ).join(CustomerReading).filter(
            Customer.is_active == True,
            CustomerReading.date >= start_date,
            CustomerReading.date <= end_date
        ).group_by(Customer.id, Customer.company_name)\
         .order_by(db.func.sum(CustomerReading.clean_water_reading).desc())\
         .limit(4).all()
        
        customers_list = [{'id': c.id, 'name': c.company_name, 'total_consumption': float(c.total_clean_water or 0)} for c in top_customers_query]
    
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
        # 1) Tổng sản lượng theo ngày
        q = db.session.query(
            WellProduction.date,
            db.func.sum(WellProduction.production).label('total_production')
        ).filter(WellProduction.date >= start_date, WellProduction.date <= end_date)
        if well_ids:
            q = q.filter(WellProduction.well_id.in_(well_ids))
        rows = q.group_by(WellProduction.date).order_by(WellProduction.date).all()
        prod_map = {r.date: float(r.total_production or 0) for r in rows}
        total_series = [prod_map.get(d, 0.0) for d in dates]

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
            'average': (sum(total_each_day) / len(total_each_day)) if total_each_day else 0,
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
        datasets.append({
            'label': code,
            'data': [date_dict.get(d, 0) for d in dates_set],
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
        'average': (sum(total_each_day)/len(total_each_day)) if total_each_day else 0,
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
    
    # Query clean water plant data from database
    query = CleanWaterPlant.query.filter(
        CleanWaterPlant.date >= start_date,
        CleanWaterPlant.date <= end_date
    ).order_by(CleanWaterPlant.date).all()
    
    # Create data map from query results - sum of clean_water_output + raw_water_jasan
    data_map = {}
    for record in query:
        clean_output = float(record.clean_water_output or 0)
        raw_jasan = float(record.raw_water_jasan or 0)
        total_water = clean_output + raw_jasan
        data_map[record.date] = total_water
    
    # Generate data series for all dates in range
    data = [data_map.get(d, 0.0) for d in dates]
    
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
            'label': 'Tổng nước sạch (Sản xuất + Jasan) (m³)',
            'data': data,
            'backgroundColor': 'rgba(75, 192, 192, 0.6)',
            'borderColor': 'rgb(75, 192, 192)',
            'borderWidth': 1,
            'fill': True,
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
        
        if record:
            clean_output = float(record.clean_water_output or 0)
            raw_jasan = float(record.raw_water_jasan or 0)
            total = clean_output + raw_jasan
        else:
            clean_output = 0
            raw_jasan = 0
            total = 0
            
        table_data.append({
            'date': d.strftime('%d/%m/%Y'),
            'clean_water_output': clean_output,
            'raw_water_jasan': raw_jasan,
            'total_water': total
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
        
        # Summary statistics
        all_values = input_data + output_data
        summary = {
            'total': sum(all_values),
            'average': sum(all_values) / (2 * len(dates)) if dates else 0,
            'max': max(all_values) if all_values else 0,
            'min': min([v for v in all_values if v > 0]) if any(all_values) else 0
        }
        
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
            # Make output lines dashed to distinguish from input
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
        
        # Calculate summary from all non-dashed datasets (input + output)
        all_values = []
        for ds in datasets:
            all_values.extend(ds['data'])
        
        summary = {
            'total': sum(all_values),
            'average': sum(all_values) / len(all_values) if all_values else 0,
            'max': max(all_values) if all_values else 0,
            'min': min([v for v in all_values if v > 0]) if any(all_values) else 0
        }
        
        # Table data with columns for each plant
        table_data = []
        for i, d in enumerate(dates):
            row = {'date': d.strftime('%d/%m/%Y')}
            total_input = 0
            total_output = 0
            
            for plant_name in sorted(plants_input.keys()):
                input_val = plants_input[plant_name].get(d, 0)
                output_val = plants_output[plant_name].get(d, 0)
                row[f'{plant_name}_input'] = input_val
                row[f'{plant_name}_output'] = output_val
                total_input += input_val
                total_output += output_val
            
            row['total_input'] = total_input
            row['total_output'] = total_output
            table_data.append(row)
        
        return {
            'chart_data': {'labels': labels, 'datasets': datasets},
            'summary': summary,
            'table_data': table_data
        }

def generate_customer_details(start_date, end_date, customer_ids=None, aggregate=False):
    """Generate customer consumption details with filtering by customer"""
    # Generate date range
    dates = []
    cur = start_date
    while cur <= end_date:
        dates.append(cur)
        cur += timedelta(days=1)

    if aggregate:
        # Aggregate mode: show total consumption across selected customers
        query = db.session.query(
            CustomerReading.date,
            db.func.sum(CustomerReading.clean_water_reading).label('total_clean_water'),
            db.func.sum(
                db.case((CustomerReading.wastewater_reading.isnot(None), CustomerReading.wastewater_reading),
                        else_=CustomerReading.wastewater_calculated)
            ).label('total_wastewater')
        ).join(Customer).filter(
            CustomerReading.date >= start_date, 
            CustomerReading.date <= end_date,
            Customer.is_active == True
        )
        
        if customer_ids:
            query = query.filter(Customer.id.in_(customer_ids))
        
        rows = query.group_by(CustomerReading.date).order_by(CustomerReading.date).all()
        
        # Create data maps
        clean_map = {r.date: float(r.total_clean_water or 0) for r in rows}
        wastewater_map = {r.date: float(r.total_wastewater or 0) for r in rows}
        
        # Generate data series
        clean_data = [clean_map.get(d, 0.0) for d in dates]
        wastewater_data = [wastewater_map.get(d, 0.0) for d in dates]
        
        labels = [d.strftime('%d/%m') for d in dates]
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
        
        # Summary statistics
        all_values = clean_data + wastewater_data
        summary = {
            'total': sum(all_values),
            'average': sum(all_values) / (2 * len(dates)) if dates else 0,
            'max': max(all_values) if all_values else 0,
            'min': min([v for v in all_values if v > 0]) if any(all_values) else 0
        }
        
        # Table data
        table_data = [
            {
                'date': d.strftime('%d/%m/%Y'),
                'clean_water': clean_data[i],
                'wastewater': wastewater_data[i]
            }
            for i, d in enumerate(dates)
        ]
        
        return {
            'chart_data': {'labels': labels, 'datasets': datasets},
            'summary': summary,
            'table_data': table_data
        }
    
    else:
        # Individual customers mode: show each customer separately
        query = db.session.query(
            CustomerReading.date,
            Customer.id,
            Customer.company_name,
            CustomerReading.clean_water_reading,
            db.case((CustomerReading.wastewater_reading.isnot(None), CustomerReading.wastewater_reading),
                    else_=CustomerReading.wastewater_calculated).label('wastewater_total')
        ).join(Customer).filter(
            CustomerReading.date >= start_date, 
            CustomerReading.date <= end_date,
            Customer.is_active == True
        )
        
        if customer_ids:
            query = query.filter(Customer.id.in_(customer_ids))
        
        rows = query.order_by(CustomerReading.date, Customer.company_name).all()
        
        # Organize data by customer
        customers_clean = {}
        customers_wastewater = {}
        for r in rows:
            customer_key = r.company_name
            if customer_key not in customers_clean:
                customers_clean[customer_key] = {}
                customers_wastewater[customer_key] = {}
            customers_clean[customer_key][r.date] = float(r.clean_water_reading or 0)
            customers_wastewater[customer_key][r.date] = float(r.wastewater_total or 0)
        
        labels = [d.strftime('%d/%m') for d in dates]
        datasets = []
        
        # Color palette for customers
        colors = ['rgb(54, 162, 235)', 'rgb(255, 99, 132)', 'rgb(75, 192, 192)', 'rgb(255, 206, 86)', 
                  'rgb(153, 102, 255)', 'rgb(255, 159, 64)', 'rgb(199, 199, 199)', 'rgb(83, 102, 255)',
                  'rgb(255, 99, 255)', 'rgb(99, 255, 132)']
        color_idx = 0
        
        # Add clean water datasets for each customer
        for customer_name in sorted(customers_clean.keys()):
            color = colors[color_idx % len(colors)]
            datasets.append({
                'label': f'{customer_name} - Nước sạch (m³)',
                'data': [customers_clean[customer_name].get(d, 0) for d in dates],
                'borderColor': color,
                'backgroundColor': color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
                'fill': False,
                'tension': 0.4
            })
            color_idx += 1
        
        # Add wastewater datasets for each customer with dashed lines
        color_idx = 0
        for customer_name in sorted(customers_wastewater.keys()):
            color = colors[color_idx % len(colors)]
            datasets.append({
                'label': f'{customer_name} - Nước thải (m³)',
                'data': [customers_wastewater[customer_name].get(d, 0) for d in dates],
                'borderColor': color,
                'backgroundColor': 'rgba(0,0,0,0)',
                'fill': False,
                'tension': 0.4,
                'borderDash': [5, 5]
            })
            color_idx += 1
        
        # Calculate summary from all datasets
        all_values = []
        for ds in datasets:
            all_values.extend(ds['data'])
        
        summary = {
            'total': sum(all_values),
            'average': sum(all_values) / len(all_values) if all_values else 0,
            'max': max(all_values) if all_values else 0,
            'min': min([v for v in all_values if v > 0]) if any(all_values) else 0
        }
        
        # Table data with columns for each customer
        table_data = []
        for i, d in enumerate(dates):
            row = {'date': d.strftime('%d/%m/%Y')}
            total_clean = 0
            total_wastewater = 0
            
            for customer_name in sorted(customers_clean.keys()):
                clean_val = customers_clean[customer_name].get(d, 0)
                wastewater_val = customers_wastewater[customer_name].get(d, 0)
                # Shorten customer name for table headers
                short_name = customer_name[:15] + "..." if len(customer_name) > 15 else customer_name
                row[f'{short_name}_clean'] = clean_val
                row[f'{short_name}_waste'] = wastewater_val
                total_clean += clean_val
                total_wastewater += wastewater_val
            
            row['total_clean'] = total_clean
            row['total_wastewater'] = total_wastewater
            table_data.append(row)
        
        return {
            'chart_data': {'labels': labels, 'datasets': datasets},
            'summary': summary,
            'table_data': table_data
        }