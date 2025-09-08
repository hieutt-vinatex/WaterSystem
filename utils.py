from flask import make_response
from models import UserRole, WellProduction, CleanWaterPlant, WastewaterPlant, CustomerReading, Customer, Well
from app import db
from datetime import datetime, date
import io
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def check_permissions(user_role, allowed_roles):
    """Check if user role has permission"""
    if user_role == UserRole.ADMIN:
        return True
    return user_role.value in allowed_roles

def generate_daily_report(start_date, end_date, format_type):
    """Generate daily clean water report"""
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get data
    well_data = db.session.query(
        WellProduction.date,
        Well.code,
        WellProduction.production
    ).join(Well).filter(
        WellProduction.date >= start_date,
        WellProduction.date <= end_date
    ).order_by(WellProduction.date, Well.code).all()
    
    clean_water_data = CleanWaterPlant.query.filter(
        CleanWaterPlant.date >= start_date,
        CleanWaterPlant.date <= end_date
    ).all()
    
    if format_type == 'excel':
        return generate_excel_daily_report(well_data, clean_water_data, start_date, end_date)
    else:
        return generate_pdf_daily_report(well_data, clean_water_data, start_date, end_date)

def generate_monthly_report(report_type, start_date, end_date, format_type):
    """Generate monthly reports"""
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if report_type == 'monthly_clean_water':
        data = CleanWaterPlant.query.filter(
            CleanWaterPlant.date >= start_date,
            CleanWaterPlant.date <= end_date
        ).all()
        
        if format_type == 'excel':
            return generate_excel_monthly_clean_water(data, start_date, end_date)
        else:
            return generate_pdf_monthly_clean_water(data, start_date, end_date)
    
    elif report_type == 'monthly_wastewater_1':
        data = WastewaterPlant.query.filter(
            WastewaterPlant.date >= start_date,
            WastewaterPlant.date <= end_date,
            WastewaterPlant.plant_number == 1
        ).all()
        
        if format_type == 'excel':
            return generate_excel_monthly_wastewater(data, start_date, end_date, 1)
        else:
            return generate_pdf_monthly_wastewater(data, start_date, end_date, 1)
    
    elif report_type == 'monthly_wastewater_2':
        data = WastewaterPlant.query.filter(
            WastewaterPlant.date >= start_date,
            WastewaterPlant.date <= end_date,
            WastewaterPlant.plant_number == 2
        ).all()
        
        if format_type == 'excel':
            return generate_excel_monthly_wastewater(data, start_date, end_date, 2)
        else:
            return generate_pdf_monthly_wastewater(data, start_date, end_date, 2)

def generate_excel_daily_report(well_data, clean_water_data, start_date, end_date):
    """Generate Excel daily report"""
    output = io.BytesIO()
    
    # Create DataFrame for wells
    well_df_data = []
    for item in well_data:
        well_df_data.append({
            'Ngày': item.date.strftime('%d/%m/%Y'),
            'Giếng': item.code,
            'Sản lượng (m³)': item.production or 0
        })
    
    # Create DataFrame for clean water
    clean_df_data = []
    for item in clean_water_data:
        clean_df_data.append({
            'Ngày': item.date.strftime('%d/%m/%Y'),
            'Nước sạch cấp (m³)': item.clean_water_output or 0,
            'Nước thô Jasan (m³)': item.raw_water_jasan or 0,
            'Điện tiêu thụ (kWh)': item.electricity or 0
        })
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if well_df_data:
            well_df = pd.DataFrame(well_df_data)
            well_df.to_excel(writer, sheet_name='Sản lượng giếng', index=False)
        
        if clean_df_data:
            clean_df = pd.DataFrame(clean_df_data)
            clean_df.to_excel(writer, sheet_name='Nhà máy nước sạch', index=False)
    
    output.seek(0)
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=daily_report_{start_date}_{end_date}.xlsx'
    
    return response

def generate_pdf_daily_report(well_data, clean_water_data, start_date, end_date):
    """Generate PDF daily report"""
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title = Paragraph(f"Báo cáo nước sạch hàng ngày<br/>Từ {start_date.strftime('%d/%m/%Y')} đến {end_date.strftime('%d/%m/%Y')}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Well production table
    if well_data:
        well_table_data = [['Ngày', 'Giếng', 'Sản lượng (m³)']]
        for item in well_data:
            well_table_data.append([
                item.date.strftime('%d/%m/%Y'),
                item.code,
                f"{item.production or 0:.2f}"
            ])
        
        well_table = Table(well_table_data)
        well_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(Paragraph("Sản lượng các giếng khoan", styles['Heading2']))
        story.append(well_table)
        story.append(Spacer(1, 20))
    
    # Clean water table
    if clean_water_data:
        clean_table_data = [['Ngày', 'Nước sạch cấp (m³)', 'Nước thô Jasan (m³)', 'Điện tiêu thụ (kWh)']]
        for item in clean_water_data:
            clean_table_data.append([
                item.date.strftime('%d/%m/%Y'),
                f"{item.clean_water_output or 0:.2f}",
                f"{item.raw_water_jasan or 0:.2f}",
                f"{item.electricity or 0:.2f}"
            ])
        
        clean_table = Table(clean_table_data)
        clean_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(Paragraph("Nhà máy xử lý nước sạch", styles['Heading2']))
        story.append(clean_table)
    
    doc.build(story)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=daily_report_{start_date}_{end_date}.pdf'
    
    return response

def generate_excel_monthly_clean_water(data, start_date, end_date):
    """Generate Excel monthly clean water report"""
    output = io.BytesIO()
    
    df_data = []
    for item in data:
        df_data.append({
            'Ngày': item.date.strftime('%d/%m/%Y'),
            'Điện tiêu thụ (kWh)': item.electricity or 0,
            'PAC (kg)': item.pac_usage or 0,
            'Xút (kg)': item.naoh_usage or 0,
            'Polymer (kg)': item.polymer_usage or 0,
            'Nước sạch sản xuất (m³)': item.clean_water_output or 0
        })
    
    df = pd.DataFrame(df_data)
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Tiêu hao điện và hóa chất', index=False)
    
    output.seek(0)
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=monthly_clean_water_{start_date}_{end_date}.xlsx'
    
    return response

def generate_pdf_monthly_clean_water(data, start_date, end_date):
    """Generate PDF monthly clean water report"""
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title = Paragraph(f"Báo cáo tiêu hao điện và hóa chất NMNS<br/>Từ {start_date.strftime('%d/%m/%Y')} đến {end_date.strftime('%d/%m/%Y')}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Data table
    table_data = [['Ngày', 'Điện (kWh)', 'PAC (kg)', 'Xút (kg)', 'Polymer (kg)', 'NS sản xuất (m³)']]
    for item in data:
        table_data.append([
            item.date.strftime('%d/%m/%Y'),
            f"{item.electricity or 0:.2f}",
            f"{item.pac_usage or 0:.2f}",
            f"{item.naoh_usage or 0:.2f}",
            f"{item.polymer_usage or 0:.2f}",
            f"{item.clean_water_output or 0:.2f}"
        ])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    doc.build(story)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=monthly_clean_water_{start_date}_{end_date}.pdf'
    
    return response

def generate_excel_monthly_wastewater(data, start_date, end_date, plant_number):
    """Generate Excel monthly wastewater report"""
    output = io.BytesIO()
    
    df_data = []
    for item in data:
        df_data.append({
            'Ngày': item.date.strftime('%d/%m/%Y'),
            'NT theo ĐH (m³)': item.wastewater_meter or 0,
            'NT đầu vào TQT (m³)': item.input_flow_tqt or 0,
            'NT đầu ra TQT (m³)': item.output_flow_tqt or 0,
            'Bùn thải (m³)': item.sludge_output or 0,
            'Điện tiêu thụ (kWh)': item.electricity or 0,
            'Hóa chất (kg)': item.chemical_usage or 0 if plant_number == 2 else 'N/A'
        })
    
    df = pd.DataFrame(df_data)
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=f'NMNT{plant_number}', index=False)
    
    output.seek(0)
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=monthly_wastewater_{plant_number}_{start_date}_{end_date}.xlsx'
    
    return response

def generate_pdf_monthly_wastewater(data, start_date, end_date, plant_number):
    """Generate PDF monthly wastewater report"""
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title = Paragraph(f"Báo cáo tổng hợp NMNT{plant_number}<br/>Từ {start_date.strftime('%d/%m/%Y')} đến {end_date.strftime('%d/%m/%Y')}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Data table
    if plant_number == 2:
        table_data = [['Ngày', 'NT ĐH (m³)', 'NT vào TQT (m³)', 'NT ra TQT (m³)', 'Bùn (m³)', 'Điện (kWh)', 'Hóa chất (kg)']]
        for item in data:
            table_data.append([
                item.date.strftime('%d/%m/%Y'),
                f"{item.wastewater_meter or 0:.2f}",
                f"{item.input_flow_tqt or 0:.2f}",
                f"{item.output_flow_tqt or 0:.2f}",
                f"{item.sludge_output or 0:.2f}",
                f"{item.electricity or 0:.2f}",
                f"{item.chemical_usage or 0:.2f}"
            ])
    else:
        table_data = [['Ngày', 'NT ĐH (m³)', 'NT vào TQT (m³)', 'NT ra TQT (m³)', 'Bùn (m³)', 'Điện (kWh)']]
        for item in data:
            table_data.append([
                item.date.strftime('%d/%m/%Y'),
                f"{item.wastewater_meter or 0:.2f}",
                f"{item.input_flow_tqt or 0:.2f}",
                f"{item.output_flow_tqt or 0:.2f}",
                f"{item.sludge_output or 0:.2f}",
                f"{item.electricity or 0:.2f}"
            ])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    doc.build(story)
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=monthly_wastewater_{plant_number}_{start_date}_{end_date}.pdf'
    
    return response
