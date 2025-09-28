from app import db
from flask_login import UserMixin
from datetime import datetime, date
from sqlalchemy import Enum
import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    LEADERSHIP = "leadership"
    PLANT_MANAGER = "plant_manager"
    ACCOUNTING = "accounting"
    DATA_ENTRY = "data_entry"
    CUSTOMER = "customer"

class User(UserMixin, db.Model):
    # người dùng
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(Enum(UserRole), nullable=False, default=UserRole.DATA_ENTRY)
    full_name = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Customer(db.Model):
    # khách hàng
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    notes = db.Column(db.Text)
    water_ratio = db.Column(db.Float, default=0.8)  # Wastewater to clean water ratio
    daily_reading = db.Column(db.Boolean, default=False)  # True for large customers
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Well(db.Model):
    # giếng khoan
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # GK1, GK2, etc.
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Float)  # m3/day
    is_active = db.Column(db.Boolean, default=True)
    is_backup = db.Column(db.Boolean, default=False)  # GK6 is backup

class WaterTank(db.Model):
    # bể chứa nước
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Float)  # m3
    tank_type = db.Column(db.String(50))  # clean_water, raw_water

class WellProduction(db.Model):
    # SL giếng khoan
    id = db.Column(db.Integer, primary_key=True)
    well_id = db.Column(db.Integer, db.ForeignKey('well.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    production = db.Column(db.Float)  # m3
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class CleanWaterPlant(db.Model):
    # nhà máy nước sạch
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    electricity = db.Column(db.Float)  # kWh
    pac_usage = db.Column(db.Float)  # kg
    naoh_usage = db.Column(db.Float)  # kg (Xút)
    polymer_usage = db.Column(db.Float)  # kg
    clean_water_output = db.Column(db.Float)  # m3
    raw_water_jasan = db.Column(db.Float)  # m3
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class WaterTankLevel(db.Model):
    # mực nước bể chứa
    id = db.Column(db.Integer, primary_key=True)
    tank_id = db.Column(db.Integer, db.ForeignKey('water_tank.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    level = db.Column(db.Float)  # m3
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class WastewaterPlant(db.Model):
    # nhà máy xử lý nước thải
    id = db.Column(db.Integer, primary_key=True)
    plant_number = db.Column(db.Integer, nullable=False)  # 1 or 2
    date = db.Column(db.Date, nullable=False)
    wastewater_meter = db.Column(db.Float)  # m3
    input_flow_tqt = db.Column(db.Float)  # m3
    output_flow_tqt = db.Column(db.Float)  # m3
    sludge_output = db.Column(db.Float)  # m3
    electricity = db.Column(db.Float)  # kWh
    chemical_usage = db.Column(db.Float)  # kg (for plant 2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class CustomerReading(db.Model):
    # chỉ số khách hàng
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    clean_water_reading = db.Column(db.Float)  # m3
    wastewater_reading = db.Column(db.Float)  # m3 (for large customers)
    wastewater_calculated = db.Column(db.Float)  # m3 (calculated from ratio)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class ReportPeriod(db.Model):
    # kỳ báo cáo
    id = db.Column(db.Integer, primary_key=True)
    period_start = db.Column(db.Date, nullable=False)  # 25th of month
    period_end = db.Column(db.Date, nullable=False)    # 25th of next month
    is_locked = db.Column(db.Boolean, default=False)
    locked_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    locked_at = db.Column(db.DateTime)

# Define relationships
Well.production = db.relationship('WellProduction', backref='well', lazy=True)
Customer.readings = db.relationship('CustomerReading', backref='customer', lazy=True)
WaterTank.levels = db.relationship('WaterTankLevel', backref='tank', lazy=True)
User.well_productions = db.relationship('WellProduction', backref='creator', lazy=True)
User.clean_water_entries = db.relationship('CleanWaterPlant', backref='creator', lazy=True)
User.wastewater_entries = db.relationship('WastewaterPlant', backref='creator', lazy=True)
User.customer_readings = db.relationship('CustomerReading', backref='creator', lazy=True)
User.tank_levels = db.relationship('WaterTankLevel', backref='creator', lazy=True)
