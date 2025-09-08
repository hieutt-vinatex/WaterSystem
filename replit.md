# Water Management System - Phố Nối

## Overview

This is a comprehensive web-based water management system for Phố Nối industrial zone, designed to manage clean water production, wastewater treatment, and customer consumption tracking. The system provides role-based access control with different permission levels for administrators, leadership, plant managers, accounting staff, and data entry personnel. It features a dashboard with system overview diagrams, data entry interfaces for daily operations, and automated report generation capabilities.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
The system is built using Flask (Python) with SQLAlchemy ORM for database management. This choice provides flexibility for rapid development and easy database schema modifications. Flask-Login handles user authentication and session management, ensuring secure access control across different user roles.

### Database Design
Uses SQLAlchemy with a declarative base model approach, supporting both SQLite for development and PostgreSQL for production via environment variable configuration. The schema includes:
- User management with role-based permissions (Admin, Leadership, Plant Manager, Accounting, Data Entry)
- Customer management with water ratio tracking
- Well production tracking for 6 wells including backup systems
- Clean water and wastewater plant operations
- Reading management for both daily and percentage-based billing

### Authentication & Authorization
Flask-Login provides session-based authentication with role-based access control. Six distinct user roles are implemented:
- Admin: Full system access and user management
- Leadership: Dashboard overview and analytical reports
- Plant Manager: Data entry and KPI monitoring  
- Accounting: Report generation and period locking
- Data Entry: Production data input only
- Customer: Limited access (future implementation)

### Frontend Architecture
Server-side rendered templates using Jinja2 with Bootstrap 5 for responsive design. JavaScript handles dynamic interactions for:
- Interactive system diagrams with clickable zones
- Real-time chart updates using Chart.js
- Tabbed interfaces for data entry across different operational areas
- AJAX form submissions for seamless user experience

### Data Management Strategy
Implements a cyclic reporting period from the 25th of previous month to 25th of current month, matching industrial operational requirements. Automatic data validation ensures production balance between wells, treatment plants, and customer consumption. The system generates sample data for demonstration and testing purposes.

### Report Generation System
Dual-format export capability (Excel and PDF) for four standardized reports:
- Daily clean water production reports
- Monthly clean water plant consumption reports  
- Monthly wastewater treatment reports
- Customer consumption summaries
Uses pandas for Excel generation and ReportLab for PDF creation, maintaining exact formatting compatibility with existing paper-based reports.

## External Dependencies

### Core Framework Dependencies
- **Flask**: Web application framework with SQLAlchemy ORM for database operations
- **Flask-Login**: User session management and authentication
- **Werkzeug**: Password hashing and security utilities

### Frontend Libraries
- **Bootstrap 5**: Responsive UI framework with dark theme support
- **Font Awesome 6**: Icon library for consistent visual elements
- **Chart.js**: Interactive charting for production and consumption analytics

### Report Generation
- **pandas**: Excel file generation and data manipulation
- **ReportLab**: PDF report generation with custom formatting
- **openpyxl**: Excel file handling and formatting (implicit pandas dependency)

### Database Support
- **SQLite**: Default development database (file-based)
- **PostgreSQL**: Production database support via DATABASE_URL environment variable
- **SQLAlchemy**: Database abstraction layer with connection pooling

### Development Tools
- **Werkzeug ProxyFix**: Production deployment behind reverse proxy
- **Python logging**: Comprehensive error tracking and debugging
- **Environment variables**: Configuration management for different deployment environments