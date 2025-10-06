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
            # TẠO XLSX THẬT bằng openpyxl (KHÔNG dùng utils để tránh sai định dạng)
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