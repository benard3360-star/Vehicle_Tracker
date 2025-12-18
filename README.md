# Vehicle Intelligence System

A modern Django-based vehicle movement intelligence and AI analytics system with role-based access control and comprehensive tracking capabilities.

## 🚗 Features

### Core Functionality
- **Real-time Vehicle Tracking** - Monitor vehicle locations and status
- **Movement History** - Detailed trip history with filtering and analytics
- **AI Assistant** - Chat-based interface for movement insights and queries
- **PDF Reports** - Generate comprehensive movement, fuel, and performance reports
- **Role-based Access Control** - Super Admin, Organization Admin, and Employee roles

### User Management
- **Multi-organization Support** - Separate organizations with dedicated admins
- **Profile Management** - Complete user profiles with document uploads
- **Activity Logging** - Comprehensive audit trails for all user actions
- **Secure Authentication** - Password management and security features

### Modern UI/UX
- **Enterprise SaaS Design** - Clean, professional interface
- **Responsive Layout** - Works on desktop, tablet, and mobile
- **Interactive Dashboard** - Real-time KPIs and quick access modules
- **Modern Sidebar Navigation** - Organized by functionality

## 🛠️ Technology Stack

- **Backend**: Django 5.2.9, Python 3.11
- **Database**: SQLite (development)
- **Frontend**: HTML5, CSS3, JavaScript (ES6)
- **PDF Generation**: ReportLab
- **Icons**: Font Awesome 6.4
- **Fonts**: Inter, Poppins (Google Fonts)

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd vehicle-intelligence-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   cd vehicle_intelligence
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Open http://127.0.0.1:8000 in your browser
   - Login with your superuser credentials

## 🏗️ Project Structure

```
vehicle-intelligence-system/
├── vehicle_intelligence/
│   ├── main_app/
│   │   ├── templates/
│   │   │   ├── profile/
│   │   │   ├── ai_assistant.html
│   │   │   ├── dashboard.html
│   │   │   ├── vehicle_tracking.html
│   │   │   ├── movement_history.html
│   │   │   ├── reports.html
│   │   │   └── base.html
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── vehicle_intelligence/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── db.sqlite3
│   └── manage.py
├── requirements.txt
└── README.md
```

## 👥 User Roles

### Super Admin
- System-wide access and control
- Manage organizations and organization admins
- View all system activities and statistics
- Access to all modules and features

### Organization Admin
- Manage users within their organization
- View organization-specific analytics
- Add/edit/remove organization users
- Access to HR dashboard and user management

### Employee
- Access to vehicle intelligence features
- Personal profile management
- Vehicle tracking and movement history
- AI assistant for movement insights
- Generate personal reports

## 🚀 Key Modules

### 1. Vehicle Tracking (`/vehicle-tracking/`)
- Real-time vehicle location monitoring
- Current status and coordinates
- Daily summary statistics
- Interactive map view (placeholder)

### 2. Movement History (`/movement-history/`)
- Complete trip history with filtering
- Route details and statistics
- Time, distance, and fuel consumption data
- Date range and vehicle filtering

### 3. AI Assistant (`/ai-assistant/`)
- Interactive chat interface
- Natural language queries about vehicle movements
- Smart responses for location, routes, and patterns
- Quick action buttons for common questions

### 4. Reports (`/reports/`)
- **Movement Summary** - Comprehensive movement overview
- **Route Analysis** - Most frequent routes and patterns
- **Fuel Consumption** - Usage and cost analysis
- **Weekly Summary** - Daily breakdown of activities
- **Performance Metrics** - KPIs and efficiency ratings
- **Location History** - Most visited locations

### 5. Profile Management (`/profile/`)
- Complete user profile with personal information
- Document upload and management
- Activity history and audit logs
- Security settings and preferences

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
```

### Database Models
- **CustomUser** - Extended user model with role-based permissions
- **Organization** - Multi-tenant organization support
- **UserProfile** - Extended profile information
- **Document** - File upload and management
- **ActivityLog** - Comprehensive audit logging
- **Notification** - User notification system

## 🎨 UI/UX Design

### Design Principles
- **Clean & Modern** - Minimal design with focus on functionality
- **Enterprise SaaS Standards** - Professional appearance and behavior
- **Green Accent Color** - Used sparingly for primary actions (#16a34a)
- **Responsive Design** - Mobile-first approach with desktop optimization
- **Accessibility** - WCAG compliant with proper contrast and navigation

### Color Palette
- **Primary Green**: #16a34a
- **Text Dark**: #111827
- **Text Medium**: #6b7280
- **Background**: #ffffff
- **Border**: #e5e7eb
- **Success**: #16a34a
- **Warning**: #f59e0b
- **Error**: #dc2626

## 📱 Responsive Breakpoints
- **Mobile**: ≤ 480px
- **Tablet**: 481px - 768px
- **Desktop**: 769px - 1024px
- **Large Desktop**: ≥ 1025px

## 🔒 Security Features

- **Role-based Access Control** - Granular permissions system
- **Activity Logging** - Complete audit trail of user actions
- **Secure Authentication** - Password hashing and session management
- **CSRF Protection** - Built-in Django CSRF middleware
- **Input Validation** - Server-side validation for all forms
- **File Upload Security** - Restricted file types and sizes

## 🚀 Deployment

### Production Setup
1. Set `DEBUG=False` in settings
2. Configure production database (PostgreSQL recommended)
3. Set up static file serving
4. Configure email backend for notifications
5. Set up SSL/HTTPS
6. Configure backup strategy

### Docker Deployment (Optional)
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation in the `/docs` folder

## 🔄 Version History

- **v1.0.0** - Initial release with basic vehicle tracking
- **v1.1.0** - Added AI assistant and modern UI redesign
- **v1.2.0** - Enhanced reporting with PDF generation
- **v1.3.0** - Complete profile management system

---

**Vehicle Intelligence System** - Empowering smart vehicle movement analytics with AI-driven insights.