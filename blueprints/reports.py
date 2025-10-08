import io, csv, logging
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, make_response, current_app
from flask_login import login_required, current_user
from app import db
from models import CleanWaterPlant, WaterTankLevel, WaterTank, CustomerReading, Customer
from utils import generate_daily_report, generate_monthly_report, check_permissions
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

bp = Blueprint('reports', __name__)
logger = logging.getLogger(__name__)


@bp.route('/reports')
@login_required
def reports():
    if not check_permissions(current_user.role, ['accounting', 'plant_manager', 'leadership', 'admin']):
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))

    return render_template('reports.html')

def _xlsx_response(wb: Workbook, filename_base: str):
    """
    Serialize openpyxl Workbook to an in-memory XLSX and return send_file response.
    """
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"{filename_base}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

def _build_sample_report_wb(report_type: str, start_dt: date, end_dt: date) -> Workbook:
    """
    TẠM THỜI: Tạo workbook mẫu có dữ liệu tối thiểu để đảm bảo mở được bằng Excel.
    Bạn có thể thay phần fill data bằng truy vấn thực tế.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = 'BaoCao'
    ws.append(['Báo cáo', report_type])
    ws.append(['Từ ngày', start_dt.strftime('%Y-%m-%d')])
    ws.append(['Đến ngày', end_dt.strftime('%Y-%m-%d')])
    ws.append([])

    # Header dữ liệu ví dụ
    ws.append(['Ngày', 'Mô tả', 'Giá trị'])
    cur = start_dt
    v = 1000
    while cur <= end_dt:
        ws.append([cur.strftime('%Y-%m-%d'), 'Dữ liệu mẫu', v])
        v += 37
        cur += timedelta(days=1)
    return wb

def _date_range(start_dt: date, end_dt: date):
    cur = start_dt
    while cur <= end_dt:
        yield cur
        cur += timedelta(days=1)

def _build_clean_water_plant_report_wb(start_dt: date, end_dt: date) -> Workbook:
    """Builds an Excel workbook for 'BÁO CÁO NHÀ MÁY NƯỚC SẠCH (m3)'.

    Mapping requirements:
    - NƯỚC CẤP              -> CleanWaterPlant.clean_water_output (per day)
    - NƯỚC THÔ JASAN        -> CleanWaterPlant.raw_water_jasan (per day)
    - LƯỢNG NƯỚC TẠI CÁC BỂ CHỨA (clean water tanks)
        Columns: BỂ 1200, BỂ 2000, BỂ 4000 -> WaterTankLevel.level for tanks with capacity 1200/2000/4000 (tank_type='clean_water')
    - NƯỚC SẠCH MỘT SỐ DOANH NGHIỆP (customer clean water reading)
        Columns: NHUỘM HY, LEEHING HT, LEEHING TT, JASAN, LỆ TINH
        Data: sum of CustomerReading.clean_water_reading per customer per day (0 if none)
    """
    wb = Workbook()
    ws = wb.active
    ws.title = 'BÁO CÁO'

    # Styles
    header_fill = PatternFill(start_color='FFECD9', end_color='FFECD9', fill_type='solid')
    subheader_fill = PatternFill(start_color='FFF5E6', end_color='FFF5E6', fill_type='solid')
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    right = Alignment(horizontal='right', vertical='center')

    # Title row (merge across columns A to M)
    ws.merge_cells('A1:M1')
    ws['A1'] = 'BÁO CÁO NHÀ MÁY NƯỚC SẠCH (m3)'
    ws['A1'].font = Font(size=14, bold=True)
    ws['A1'].alignment = center

    # Header rows
    # Row 2: group headers
    headers_row2 = [
        'STT', 'NGÀY', 'NƯỚC CẤP',
        'LƯỢNG NƯỚC TẠI CÁC BỂ CHỨA', '', '',
        'NƯỚC SẠCH MỘT SỐ DOANH NGHIỆP', '', '', '', '',
        'NƯỚC THÔ JASAN', 'GHI CHÚ'
    ]
    ws.append(headers_row2)
    # Row 3: sub-headers
    sub_headers_row3 = [
        '', '', '',
        'BỂ 1200', 'BỂ 2000', 'BỂ 4000',
        'NHUỘM HY', 'LEEHING HT', 'LEEHING TT', 'JASAN', 'LỆ TINH',
        '', ''
    ]
    ws.append(sub_headers_row3)

    # Merge group cells
    ws.merge_cells('A2:A3')  # STT
    ws.merge_cells('B2:B3')  # NGÀY
    ws.merge_cells('C2:C3')  # NƯỚC CẤP
    ws.merge_cells('D2:F2')  # BỂ CHỨA
    ws.merge_cells('G2:K2')  # DOANH NGHIỆP
    ws.merge_cells('L2:L3')  # NƯỚC THÔ JASAN
    ws.merge_cells('M2:M3')  # GHI CHÚ

    # Style header rows
    for row_idx in (2, 3):
        for col in range(1, 14):  # A..M (13 columns)
            c = ws.cell(row=row_idx, column=col)
            c.font = Font(bold=True)
            c.alignment = center
            c.fill = header_fill if row_idx == 2 else subheader_fill
            c.border = border

    # Column widths
    widths = [6, 12, 12, 10, 10, 10, 12, 12, 12, 12, 12, 14, 18]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w

    # Data preparation
    dates = list(_date_range(start_dt, end_dt))

    # Clean water plant data
    plant_rows = db.session.query(CleanWaterPlant.date, CleanWaterPlant.clean_water_output, CleanWaterPlant.raw_water_jasan) \
        .filter(CleanWaterPlant.date >= start_dt, CleanWaterPlant.date <= end_dt) \
        .all()
    clean_map = {r[0]: float(r[1] or 0) for r in plant_rows}
    raw_jasan_map = {r[0]: float(r[2] or 0) for r in plant_rows}

    # Tanks: only clean water tanks
    tanks = WaterTank.query.filter(WaterTank.tank_type == 'clean_water').all()
    # Map tank_id to label (by capacity or name)
    def tank_label(t: WaterTank):
        cap = int((t.capacity or 0))
        if cap in (1200, 2000, 4000):
            return f'BỂ {cap}'
        # Fallback: try parse from name
        name = (t.name or '').lower()
        for c in (1200, 2000, 4000):
            if str(c) in name:
                return f'BỂ {c}'
        return t.name or f'TANK {t.id}'

    desired_tank_labels = ['BỂ 1200', 'BỂ 2000', 'BỂ 4000']
    tank_by_label = {}
    for t in tanks:
        lbl = tank_label(t)
        if lbl in desired_tank_labels and lbl not in tank_by_label:
            tank_by_label[lbl] = t.id

    # Fetch levels
    levels = db.session.query(WaterTankLevel.date, WaterTankLevel.tank_id, WaterTankLevel.level) \
        .filter(WaterTankLevel.date >= start_dt, WaterTankLevel.date <= end_dt, WaterTankLevel.tank_id.in_(tank_by_label.values() if tank_by_label else [-1])) \
        .all()
    levels_map = {lbl: {} for lbl in desired_tank_labels}
    for dt_val, tank_id, level in levels:
        # find label
        for lbl, tid in tank_by_label.items():
            if tid == tank_id:
                levels_map[lbl][dt_val] = float(level or 0)
                break

    # Customers mapping
    customer_columns = ['NHUỘM HY', 'LEEHING HT', 'LEEHING TT', 'JASAN', 'LỆ TINH']
    cust_col_map = {k: [] for k in customer_columns}
    all_customers = Customer.query.filter(Customer.is_active.is_(True)).all()
    for c in all_customers:
        name = (c.company_name or '').lower()
        if 'jasan' in name:
            cust_col_map['JASAN'].append(c.id)
        elif 'lệ tinh' in name or 'le tinh' in name:
            cust_col_map['LỆ TINH'].append(c.id)
        elif 'hy' in name:
            # nhuộm hy
            cust_col_map['NHUỘM HY'].append(c.id)
        elif 'leehing' in name and ('tt' in name or ' t.t' in name):
            cust_col_map['LEEHING TT'].append(c.id)
        elif 'leehing' in name:  # default to HT if not specified
            cust_col_map['LEEHING HT'].append(c.id)

    # Customer readings by day (clean water)
    readings = db.session.query(
        CustomerReading.date,
        CustomerReading.customer_id,
        db.func.sum(CustomerReading.clean_water_reading)
    ).filter(
        CustomerReading.date >= start_dt,
        CustomerReading.date <= end_dt
    ).group_by(CustomerReading.date, CustomerReading.customer_id).all()

    # Build per-column map
    cust_series = {k: {} for k in customer_columns}
    for d, cid, total_clean in readings:
        for col, ids in cust_col_map.items():
            if cid in ids:
                cust_series[col][d] = float(total_clean or 0) + float(cust_series[col].get(d, 0))
                break

    # Write data rows
    row_idx = 4
    stt = 1
    for d in dates:
        ws.cell(row=row_idx, column=1, value=stt).alignment = center
        ws.cell(row=row_idx, column=2, value=d.strftime('%d/%m/%Y')).alignment = center

        # NƯỚC CẤP
        ws.cell(row=row_idx, column=3, value=clean_map.get(d, 0)).alignment = right

        # Tanks D,E,F
        ws.cell(row=row_idx, column=4, value=levels_map['BỂ 1200'].get(d, 0)).alignment = right
        ws.cell(row=row_idx, column=5, value=levels_map['BỂ 2000'].get(d, 0)).alignment = right
        ws.cell(row=row_idx, column=6, value=levels_map['BỂ 4000'].get(d, 0)).alignment = right

        # Customers G..K
        for i, col_name in enumerate(['NHUỘM HY', 'LEEHING HT', 'LEEHING TT', 'JASAN', 'LỆ TINH'], start=7):
            ws.cell(row=row_idx, column=i, value=cust_series[col_name].get(d, 0)).alignment = right

        # NƯỚC THÔ JASAN (L)
        ws.cell(row=row_idx, column=12, value=raw_jasan_map.get(d, 0)).alignment = right

        # GHI CHÚ (M) empty for now
        ws.cell(row=row_idx, column=13, value='')

        # Borders for the row
        for col in range(1, 14):
            ws.cell(row=row_idx, column=col).border = border
        row_idx += 1
        stt += 1

    # Apply number formatting with thousand separators
    for r in ws.iter_rows(min_row=4, min_col=3, max_col=13, max_row=row_idx-1):
        for c in r:
            c.number_format = '#,##0'

    # Freeze panes below headers
    ws.freeze_panes = 'A4'

    return wb

@bp.route('/generate-report/<report_type>')
@login_required
def generate_report(report_type):
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        format_type = request.args.get('format', 'excel')  # excel or pdf

        # Parse ngày hợp lệ
        if start_date and end_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_dt = date.today()
            start_dt = end_dt - timedelta(days=30)

        if format_type == 'excel':
            # Excel: nhánh theo report_type
            if report_type == 'clean_water_plant':
                wb = _build_clean_water_plant_report_wb(start_dt, end_dt)
            else:
                wb = _build_sample_report_wb(report_type, start_dt, end_dt)
            filename = f"{report_type}_{date.today().strftime('%Y%m%d')}"
            return _xlsx_response(wb, filename)

        # Các định dạng khác (ví dụ pdf) vẫn dùng utils nếu bạn đã có sẵn
        if report_type == 'daily_clean_water':
            return generate_daily_report(start_date, end_date, format_type)
        else:
            return generate_monthly_report(report_type, start_date, end_date, format_type)

    except Exception as e:
        bp.logger.exception("Error generating report")
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('reports'))
    

@bp.route('/reports/export', methods=['GET'])
@login_required
def export_reports():
    # TODO: thay data bằng dữ liệu thực tế của bạn
    headers = ['Ngày', 'Giếng', 'Sản lượng (m³)']
    rows = [
        ['2025-10-01', 'W1', 1234],
        ['2025-10-01', 'W2', 1456],
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = 'BaoCao'
    ws.append(headers)
    for r in rows:
        ws.append(r)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)  # QUAN TRỌNG

    filename = f"bao_cao_{date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,  # thay cho attachment_filename
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@bp.route('/reports/export-csv', methods=['GET'])
@login_required
def export_reports_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Ngày', 'Giếng', 'Sản lượng (m³)'])
    writer.writerow(['2025-10-01', 'W1', 1234])

    data = output.getvalue()
    resp = make_response(data.encode('utf-8-sig'))  # BOM để Excel mở đúng UTF-8
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = 'attachment; filename=bao_cao.csv'
    return resp