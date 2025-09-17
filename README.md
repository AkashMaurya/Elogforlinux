# 🏥 AGU E-Logbook System (Elogforlinux)

[![Django](https://img.shields.io/badge/Django-5.2.5-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)](https://elog.agu.edu.bh)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [User Roles & Workflows](#user-roles--workflows)
- [Installation](#installation)
- [Configuration](#configuration)
- [Apps Documentation](#apps-documentation)
- [API Endpoints](#api-endpoints)
- [Deployment](#deployment)
- [Pros & Cons](#pros--cons)
- [Contributing](#contributing)
- [Support](#support)

## 🎯 Overview

The **AGU E-Logbook System** is a comprehensive digital platform designed for the Arabian Gulf University (AGU) medical education program. It facilitates electronic logging, tracking, and management of medical students' clinical activities, rotations, and assessments.

### 🌟 Key Highlights

- **Multi-Role System**: Admin, Doctor, Student, Staff access levels
- **SSO Integration**: Microsoft Azure AD authentication
- **Real-time Tracking**: Live attendance and activity monitoring
- **Comprehensive Reporting**: PDF/Excel export capabilities
- **Mobile Responsive**: Works seamlessly on all devices
- **Secure**: SSL encryption and role-based access control

## ✨ Features

### 🔐 Authentication & Authorization
- Microsoft SSO integration with Azure AD
- Role-based access control (RBAC)
- Secure session management
- Password reset functionality

### 📊 Dashboard & Analytics
- Role-specific dashboards
- Real-time statistics and charts
- Activity tracking and monitoring
- Performance analytics

### 📝 Logging & Documentation
- Electronic logbook entries
- Activity type management
- Core diagnosis procedures
- Attendance tracking

### 📄 Reporting & Export
- PDF report generation
- Excel export functionality
- Department-wise reports
- Student progress reports
- Tutor supervision reports

### 👥 User Management
- Bulk user import/export
- Department assignments
- Group management
- Profile management

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (Templates)   │◄──►│   (Django)      │◄──►│   (SQLite/      │
│   - HTML/CSS    │    │   - Views       │    │    PostgreSQL)  │
│   - JavaScript  │    │   - Models      │    │                 │
│   - Bootstrap   │    │   - Forms       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Static Files  │    │   Media Files   │    │   External      │
│   - CSS/JS      │    │   - Uploads     │    │   Services      │
│   - Images      │    │   - Documents   │    │   - Azure AD    │
│   - Fonts       │    │   - Reports     │    │   - Email       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 👥 User Roles & Workflows

### 🔧 Admin Workflow
1. **System Management**
   - User creation and management
   - Department and group setup
   - Activity type configuration
   - System settings and restrictions

2. **Reporting & Analytics**
   - Generate comprehensive reports
   - Monitor system usage
   - Export data for analysis
   - Manage notifications

3. **Content Management**
   - Blog post creation and management
   - Category management
   - File uploads and media management

### 👨‍⚕️ Doctor Workflow
1. **Student Supervision**
   - Review student logbook entries
   - Approve/reject activities
   - Provide feedback and comments
   - Set review deadlines

2. **Attendance Management**
   - Take student attendance
   - Track training site assignments
   - Monitor student progress
   - Generate attendance reports

3. **Assessment & Evaluation**
   - Evaluate student performance
   - Grade clinical activities
   - Provide constructive feedback
   - Track competency development

### 🎓 Student Workflow
1. **Logbook Management**
   - Create daily activity entries
   - Log clinical procedures
   - Record patient encounters
   - Submit for supervisor review

2. **Progress Tracking**
   - View completed activities
   - Monitor approval status
   - Track attendance records
   - Access feedback from supervisors

3. **Resource Access**
   - Download forms and documents
   - Access educational materials
   - View announcements and updates
   - Generate progress reports

### 👩‍💼 Staff Workflow
1. **Administrative Support**
   - Emergency attendance management
   - Student record maintenance
   - Document processing
   - Communication facilitation

2. **Coordination**
   - Schedule management
   - Resource allocation
   - Inter-department communication
   - Event organization

## 🚀 Installation

### Prerequisites
- Python 3.12+
- Django 5.2.5
- PostgreSQL (for production) or SQLite (for development)
- Node.js (for frontend dependencies)

### Quick Start

1. **Clone the Repository**
```bash
git clone https://github.com/AkashMaurya/Elogforlinux.git
cd Elogforlinux/elogbookagu
```

2. **Create Virtual Environment**
```bash
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Database Setup**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

6. **Run Development Server**
```bash
python manage.py runserver
```

Visit `http://localhost:8000` to access the application.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=False
DATABASE_URL=postgresql://user:password@localhost/dbname
ALLOWED_HOSTS=elog.agu.edu.bh,www.elog.agu.edu.bh

# Microsoft SSO Configuration
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_TENANT_ID=your-tenant-id

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-app-password
```

### SSL Configuration

For production deployment, ensure SSL certificates are properly configured:

```bash
# Certificate files should be placed in:
# - cert.crt (SSL certificate)
# - cert.key (Private key)
```

## 📱 Apps Documentation

### 🏠 Core Apps

#### 1. **accounts** - User Management
- **Purpose**: Handle user authentication, profiles, and role management
- **Models**: CustomUser, Doctor, Student, Staff
- **Features**:
  - Microsoft SSO integration
  - Role-based permissions
  - Profile management
  - Soft delete functionality

#### 2. **admin_section** - Administrative Interface
- **Purpose**: Comprehensive admin dashboard and management tools
- **Models**: Department, Year, Group, ActivityType, Blog, BlogCategory
- **Features**:
  - User management (CRUD operations)
  - Bulk import/export functionality
  - Department and group management
  - Activity type configuration
  - Blog and content management
  - Comprehensive reporting system

#### 3. **doctor_section** - Doctor Portal
- **Purpose**: Doctor-specific functionality for student supervision
- **Models**: StudentLogFormModel, Notification
- **Features**:
  - Student logbook review and approval
  - Attendance tracking
  - Performance evaluation
  - Deadline management
  - Notification system

#### 4. **student_section** - Student Portal
- **Purpose**: Student interface for logbook management
- **Models**: StudentLogFormModel, CoreDiagnosisProcedureSession
- **Features**:
  - Daily activity logging
  - Progress tracking
  - Document uploads
  - Supervisor communication
  - Report generation

#### 5. **staff_section** - Staff Portal
- **Purpose**: Administrative staff functionality
- **Models**: EmergencyAttendance
- **Features**:
  - Emergency attendance management
  - Administrative support tools
  - Communication facilitation
  - Record maintenance

#### 6. **publicpage** - Public Interface
- **Purpose**: Public-facing pages and authentication
- **Features**:
  - Landing page
  - Blog display
  - Resource access
  - Authentication forms

#### 7. **defaultuser** - Default User Handling
- **Purpose**: Handle users without specific roles
- **Features**:
  - Pending account management
  - Role assignment workflow
  - Access control

### 🔧 Utility Apps

#### 8. **utils** - Shared Utilities
- **Purpose**: Common functionality across apps
- **Features**:
  - PDF generation utilities
  - Email helpers
  - Common decorators
  - Shared functions

## 🌐 API Endpoints

### Authentication Endpoints
```
POST /accounts/login/          # User login
POST /accounts/logout/         # User logout
POST /accounts/password/reset/ # Password reset
```

### Admin Endpoints
```
GET  /admin_section/                    # Admin dashboard
POST /admin_section/add_user/           # Create new user
GET  /admin_section/department_report/  # Department reports
POST /admin_section/bulk_import/        # Bulk user import
```

### Doctor Endpoints
```
GET  /doctor_section/                   # Doctor dashboard
POST /doctor_section/take_attendance/   # Record attendance
GET  /doctor_section/review_logs/       # Review student logs
POST /doctor_section/approve_activity/  # Approve student activity
```

### Student Endpoints
```
GET  /student_section/              # Student dashboard
POST /student_section/add_log/      # Create log entry
GET  /student_section/my_records/   # View personal records
POST /student_section/upload_file/  # Upload documents
```

## 🚀 Deployment

### Production Deployment (Ubuntu/Linux)

1. **Server Setup**
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx postgresql
```

2. **Application Deployment**
```bash
# Clone and setup application
git clone https://github.com/AkashMaurya/Elogforlinux.git
cd Elogforlinux/elogbookagu
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

3. **Database Configuration**
```bash
sudo -u postgres createdb elogbook_db
sudo -u postgres createuser elogbook_user
```

4. **Gunicorn Setup**
```bash
pip install gunicorn
gunicorn --bind 0.0.0.0:8000 elogbookagu.wsgi:application
```

5. **Nginx Configuration**
```nginx
server {
    listen 80;
    server_name elog.agu.edu.bh;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static/ {
        alias /path/to/staticfiles/;
    }
}
```

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "elogbookagu.wsgi:application"]
```

## ⚖️ Pros & Cons

### ✅ Pros

#### **Technical Advantages**
- **Scalable Architecture**: Django's MVT pattern ensures maintainable code
- **Security**: Built-in CSRF protection, SQL injection prevention
- **Database Flexibility**: Supports multiple database backends
- **Rich Ecosystem**: Extensive third-party packages and community support
- **RESTful Design**: Clean API structure for future integrations

#### **Functional Benefits**
- **Comprehensive Solution**: All-in-one platform for medical education
- **User-Friendly Interface**: Intuitive design for all user types
- **Real-time Updates**: Live notifications and status updates
- **Mobile Responsive**: Works seamlessly on all devices
- **Offline Capability**: Some features work without internet connection

#### **Administrative Advantages**
- **Centralized Management**: Single platform for all operations
- **Automated Workflows**: Reduces manual administrative tasks
- **Detailed Analytics**: Comprehensive reporting and insights
- **Audit Trail**: Complete activity logging for compliance
- **Backup & Recovery**: Robust data protection mechanisms

### ❌ Cons

#### **Technical Limitations**
- **Server Dependencies**: Requires dedicated server infrastructure
- **Database Complexity**: Large datasets may require optimization
- **Learning Curve**: Administrators need training for full utilization
- **Customization Limits**: Some features may require development expertise
- **Performance Scaling**: May need optimization for very large user bases

#### **Operational Challenges**
- **Internet Dependency**: Most features require stable internet connection
- **Maintenance Requirements**: Regular updates and security patches needed
- **Training Needs**: Users need orientation for optimal usage
- **Data Migration**: Moving from existing systems can be complex
- **Integration Complexity**: Connecting with other institutional systems

#### **Resource Requirements**
- **Hardware Costs**: Requires server infrastructure and maintenance
- **Technical Expertise**: Needs IT support for deployment and maintenance
- **Ongoing Costs**: Hosting, SSL certificates, and maintenance expenses
- **Backup Storage**: Additional storage requirements for data backup
- **Security Monitoring**: Continuous security monitoring and updates needed

## 🤝 Contributing

We welcome contributions to improve the AGU E-Logbook System!

### Development Setup
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for all functions and classes
- Write unit tests for new features
- Update documentation for any changes

## 📞 Support

### Technical Support
- **Email**: support@agu.edu.bh
- **Documentation**: [Wiki](https://github.com/AkashMaurya/Elogforlinux/wiki)
- **Issues**: [GitHub Issues](https://github.com/AkashMaurya/Elogforlinux/issues)

### System Information
- **Live URL**: https://elog.agu.edu.bh
- **Version**: 2.0.0
- **Last Updated**: December 2024
- **Maintained by**: AGU IT Department

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Arabian Gulf University** for project sponsorship
- **Django Community** for the excellent framework
- **Microsoft** for Azure AD integration support
- **All Contributors** who helped build this system

---

**Made with ❤️ for Arabian Gulf University Medical Education Program**

*Halleluiyah Ready for production!* 🎉
