from app import db
from models import *
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timedelta
import random

def generate_sample_data():
    """Generate sample data for the system"""
    
    # Check if data already exists
    if User.query.first():
        return
    
    print("Generating sample data...")
    
    # Create users
    users_data = [
        {'username': 'admin', 'password': 'admin123', 'email': 'admin@phonoi.com', 'role': UserRole.ADMIN, 'full_name': 'Quản trị hệ thống'},
        {'username': 'leadership', 'password': 'leader123', 'email': 'leader@phonoi.com', 'role': UserRole.LEADERSHIP, 'full_name': 'Ban lãnh đạo'},
        {'username': 'plant_manager', 'password': 'manager123', 'email': 'manager@phonoi.com', 'role': UserRole.PLANT_MANAGER, 'full_name': 'Quản lý nhà máy'},
        {'username': 'accounting', 'password': 'accounting123', 'email': 'accounting@phonoi.com', 'role': UserRole.ACCOUNTING, 'full_name': 'Kế toán'},
        {'username': 'data_entry', 'password': 'entry123', 'email': 'entry@phonoi.com', 'role': UserRole.DATA_ENTRY, 'full_name': 'Nhân viên nhập liệu'},
    ]
    
    for user_data in users_data:
        user = User(
            username=user_data['username'],
            password_hash=generate_password_hash(user_data['password']),
            email=user_data['email'],
            role=user_data['role'],
            full_name=user_data['full_name']
        )
        db.session.add(user)
    
    # Create wells
    wells_data = [
        {'code': 'GK1', 'name': 'Giếng khoan số 1', 'capacity': 2000, 'is_active': True, 'is_backup': False},
        {'code': 'GK2', 'name': 'Giếng khoan số 2', 'capacity': 2000, 'is_active': True, 'is_backup': False},
        {'code': 'GK3', 'name': 'Giếng khoan số 3', 'capacity': 2000, 'is_active': True, 'is_backup': False},
        {'code': 'GK5', 'name': 'Giếng khoan số 5', 'capacity': 2000, 'is_active': True, 'is_backup': False},
        {'code': 'GK5-TT', 'name': 'Giếng khoan số 5 TT', 'capacity': 2000, 'is_active': True, 'is_backup': False},
        {'code': 'GK6', 'name': 'Giếng khoan số 6 (dự phòng)', 'capacity': 2000, 'is_active': False, 'is_backup': True},
    ]
    
    for well_data in wells_data:
        well = Well(**well_data)
        db.session.add(well)
    
    # Create water tanks
    tanks_data = [
        {'name': 'Bể chứa 1200', 'capacity': 1200, 'tank_type': 'clean_water'},
        {'name': 'Bể chứa 2000', 'capacity': 2000, 'tank_type': 'clean_water'},
        {'name': 'Bể chứa 4000', 'capacity': 4000, 'tank_type': 'clean_water'},
    ]
    
    for tank_data in tanks_data:
        tank = WaterTank(**tank_data)
        db.session.add(tank)
    
    # Create 50 customers
    customers_data = [
        {'company_name': 'Công ty Jasan', 'contact_person': 'Nguyễn Văn A', 'phone': '0123456789', 'email': 'contact@jasan.com', 'water_ratio': 0.85, 'daily_reading': True},
        {'company_name': 'Công ty Nhuộm HY', 'contact_person': 'Trần Thị B', 'phone': '0123456790', 'email': 'contact@hy.com', 'water_ratio': 0.9, 'daily_reading': True},
        {'company_name': 'Công ty Leehing', 'contact_person': 'Lê Văn C', 'phone': '0123456791', 'email': 'contact@leehing.com', 'water_ratio': 0.8, 'daily_reading': True},
        {'company_name': 'Công ty Lệ Tinh', 'contact_person': 'Phạm Thị D', 'phone': '0123456792', 'email': 'contact@letinh.com', 'water_ratio': 0.75, 'daily_reading': True},
        {'company_name': 'Dệt nhuộm HSM', 'contact_person': 'Hoàng Văn E', 'phone': '0123456793', 'email': 'contact@hsm.com', 'water_ratio': 0.88, 'daily_reading': False},
    ]
    
    # Generate 45 more customers
    for i in range(45):
        customers_data.append({
            'company_name': f'Công ty số {i+6}',
            'contact_person': f'Người liên hệ {i+6}',
            'phone': f'012345{6800+i}',
            'email': f'contact{i+6}@company.com',
            'water_ratio': round(random.uniform(0.6, 0.9), 2),
            'daily_reading': False
        })
    
    for customer_data in customers_data:
        customer = Customer(**customer_data)
        db.session.add(customer)
    
    db.session.commit()
    
    # Generate production data from early 2024
    start_date = date(2024, 1, 1)
    end_date = date.today()
    
    wells = Well.query.filter_by(is_active=True).all()
    customers = Customer.query.all()
    tanks = WaterTank.query.all()
    
    current_date = start_date
    while current_date <= end_date:
        # Generate well production data
        for well in wells:
            if not well.is_backup:  # GK6 is backup, rarely used
                production = random.uniform(1500, 2000)
                well_production = WellProduction(
                    well_id=well.id,
                    date=current_date,
                    production=production,
                    created_by=1  # admin user
                )
                db.session.add(well_production)
        
        # Generate clean water plant data
        total_well_production = sum([random.uniform(1500, 2000) for _ in wells if not well.is_backup])
        clean_water_output = total_well_production * 0.98  # 98% efficiency
        
        clean_water_plant = CleanWaterPlant(
            date=current_date,
            electricity=random.uniform(8000, 12000),
            pac_usage=random.uniform(50, 80),
            naoh_usage=random.uniform(30, 50),
            polymer_usage=random.uniform(10, 20),
            clean_water_output=clean_water_output,
            raw_water_jasan=random.uniform(800, 1000),
            created_by=1
        )
        db.session.add(clean_water_plant)
        
        # Generate wastewater plant data
        for plant_num in [1, 2]:
            capacity = 12000 if plant_num == 1 else 8000
            input_flow = random.uniform(capacity * 0.6, capacity * 0.9)
            output_flow = input_flow * 0.95  # 95% treatment efficiency
            
            wastewater_plant = WastewaterPlant(
                plant_number=plant_num,
                date=current_date,
                wastewater_meter=input_flow,
                input_flow_tqt=input_flow,
                output_flow_tqt=output_flow,
                sludge_output=random.uniform(10, 30),
                electricity=random.uniform(5000, 8000),
                chemical_usage=random.uniform(20, 40) if plant_num == 2 else 0,
                created_by=1
            )
            db.session.add(wastewater_plant)
        
        # Generate customer readings (monthly on 25th or daily for large customers)
        for customer in customers:
            should_generate = False
            
            if customer.daily_reading:
                should_generate = True
            elif current_date.day == 25:  # Monthly reading on 25th
                should_generate = True
            
            if should_generate:
                clean_water_reading = random.uniform(100, 500) if customer.daily_reading else random.uniform(2000, 8000)
                
                # Calculate wastewater
                if customer.daily_reading and random.random() > 0.5:  # Some large customers have direct wastewater reading
                    wastewater_reading = clean_water_reading * customer.water_ratio
                    wastewater_calculated = None
                else:
                    wastewater_reading = None
                    wastewater_calculated = clean_water_reading * customer.water_ratio
                
                customer_reading = CustomerReading(
                    customer_id=customer.id,
                    date=current_date,
                    clean_water_reading=clean_water_reading,
                    wastewater_reading=wastewater_reading,
                    wastewater_calculated=wastewater_calculated,
                    created_by=1
                )
                db.session.add(customer_reading)
        
        # Generate tank levels
        for tank in tanks:
            level = random.uniform(tank.capacity * 0.3, tank.capacity * 0.9)
            tank_level = WaterTankLevel(
                tank_id=tank.id,
                date=current_date,
                level=level,
                created_by=1
            )
            db.session.add(tank_level)
        
        current_date += timedelta(days=1)
        
        # Commit every 30 days to avoid memory issues
        if current_date.day == 1:
            db.session.commit()
            print(f"Generated data up to {current_date}")
    
    db.session.commit()
    print("Sample data generation completed!")
    
    # Write user accounts to info.txt
    write_user_accounts()

def write_user_accounts():
    """Write user account information to info.txt"""
    with open('info.txt', 'w', encoding='utf-8') as f:
        f.write("THÔNG TIN TÀI KHOẢN HỆ THỐNG QUẢN LÝ NƯỚC PHỐ NỐI\n")
        f.write("=" * 60 + "\n\n")
        
        accounts = [
            {
                'role': 'Quản trị hệ thống',
                'username': 'admin',
                'password': 'admin123',
                'permissions': 'Toàn quyền hệ thống, quản lý người dùng, cấu hình'
            },
            {
                'role': 'Ban lãnh đạo',
                'username': 'leadership',
                'password': 'leader123',
                'permissions': 'Xem dashboard tổng quan, báo cáo phân tích'
            },
            {
                'role': 'Quản lý nhà máy',
                'username': 'plant_manager',
                'password': 'manager123',
                'permissions': 'Nhập liệu, xem KPI, quản lý vận hành'
            },
            {
                'role': 'Kế toán',
                'username': 'accounting',
                'password': 'accounting123',
                'permissions': 'Tạo báo cáo, xuất Excel/PDF, khóa kỳ'
            },
            {
                'role': 'Nhân viên nhập liệu',
                'username': 'data_entry',
                'password': 'entry123',
                'permissions': 'Nhập dữ liệu sản xuất, chỉ số khách hàng'
            }
        ]
        
        for account in accounts:
            f.write(f"Vai trò: {account['role']}\n")
            f.write(f"Tên đăng nhập: {account['username']}\n")
            f.write(f"Mật khẩu: {account['password']}\n")
            f.write(f"Quyền hạn: {account['permissions']}\n")
            f.write("-" * 50 + "\n\n")
        
        f.write("THÔNG TIN HỆ THỐNG:\n")
        f.write("- Địa chỉ truy cập: http://localhost:5000\n")
        f.write("- Hệ thống có 50 khách hàng mẫu\n")
        f.write("- Dữ liệu sản xuất từ 01/01/2024 đến hiện tại\n")
        f.write("- Chu kỳ chốt số: từ ngày 25 tháng trước đến 25 tháng sau\n")
        f.write("- Hỗ trợ xuất báo cáo Excel và PDF\n")
