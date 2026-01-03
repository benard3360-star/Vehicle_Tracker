# Vehicle Intelligence System

A modern Django-based vehicle movement intelligence and AI analytics system with role-based access control and comprehensive tracking capabilities.

## 🚗 Features

### Core Functionality
- **Real-time Vehicle Tracking** - Monitor vehicle locations and status
- **Movement History** - Detailed trip history with filtering and analytics
- **AI Assistant** - Chat-based interface for movement insights and queries
- **PDF Reports** - Generate comprehensive movement, fuel, and performance reports
- **Role-based Access Control** - Super Admin, Organization Admin, and Employee roles
- **Inventory Management** - Complete vehicle and parts inventory with stock tracking
- **Sales Management** - Vehicle sales tracking and customer management
- **Manufacturing** - Production line monitoring and order management
- **Purchasing** - Supplier management and purchase order tracking
- **Data Processing** - Advanced Excel data import and feature engineering
- **Export Capabilities** - CSV and PDF export for all major modules

### User Management
- **Multi-organization Support** - Separate organizations with dedicated admins
- **Enhanced Organization Creation** - Structured forms with validation and categorization
- **Profile Management** - Complete user profiles with document uploads
- **Activity Logging** - Comprehensive audit trails for all user actions
- **Secure Authentication** - Password management and security features
- **User Role Management** - Granular permissions and access control
- **Password Reset System** - Temporary password generation and forced changes

### Modern UI/UX
- **Enterprise SaaS Design** - Clean, professional interface
- **Responsive Layout** - Works on desktop, tablet, and mobile
- **Interactive Dashboard** - Real-time KPIs and quick access modules
- **Modern Sidebar Navigation** - Organized by functionality
- **Modal Forms** - Dynamic forms with conditional field display
- **Progress Indicators** - Visual progress bars and status badges
- **Dropdown Menus** - Interactive export and action menus
- **Form Validation** - Real-time validation with helpful error messages
- **Settings Management** - Comprehensive configuration panels

## 🛠️ Technology Stack

- **Backend**: Django 5.2.9, Python 3.11
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Frontend**: HTML5, CSS3, JavaScript (ES6)
- **PDF Generation**: ReportLab
- **Data Processing**: Pandas, NumPy for Excel data import
- **Icons**: Font Awesome 6.4
- **Fonts**: Inter, Poppins (Google Fonts)
- **Version Control**: Git with comprehensive .gitignore
- **Export Formats**: CSV, PDF, Excel

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
│   │   │   │   ├── profile.html
│   │   │   │   └── edit_profile.html
│   │   │   ├── ai_assistant.html
│   │   │   ├── dashboard.html (with AI assistant)
│   │   │   ├── analytics.html (with AI assistant)
│   │   │   ├── vehicle_alert.html (with AI assistant)
│   │   │   ├── vehicle_tracking.html
│   │   │   ├── movement_history.html
│   │   │   ├── reports.html
│   │   │   ├── inventory.html
│   │   │   ├── inventory_settings.html
│   │   │   ├── sales.html
│   │   │   ├── manufacturing.html
│   │   │   ├── purchasing.html
│   │   │   ├── super_admin_dashboard.html
│   │   │   ├── super_admin_organizations.html
│   │   │   ├── super_admin_users.html
│   │   │   ├── org_admin_dashboard.html
│   │   │   ├── hr_dashboard.html
│   │   │   └── base.html
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── ai_assistant.py (AI backend)
│   │   ├── ai_views.py (AI API endpoints)
│   │   ├── urls.py
│   │   └── admin.py
│   ├── vehicle_intelligence/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── data_preprocessing.py
│   ├── db.sqlite3
│   └── manage.py
├── .gitignore
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

## 🤖 AI Assistant Features

### Advanced Intelligence Capabilities
- **OpenAI Integration Ready** - Seamless GPT API integration with fallback algorithms
- **Context-Aware Responses** - Analyzes real database metrics for accurate insights
- **Smart Data Interpretation** - Reads current page data to provide specific analysis
- **Predictive Forecasting** - Growth predictions and capacity planning recommendations
- **Custom Report Generation** - AI-powered detailed reports with executive summaries
- **Performance Optimization** - Fleet redistribution and operational efficiency suggestions

### Page-Specific Intelligence
- **Analytics AI** - Fleet performance analysis, trend forecasting, revenue optimization
- **Vehicle Alert AI** - Individual vehicle analysis, maintenance predictions, cost tracking
- **Dashboard AI** - System overview, user management insights, role-based guidance

### Technical Features
- **Real-time API Communication** - Live chat with backend AI processing
- **Typing Indicators** - Visual feedback during AI response generation
- **Mobile Responsive** - Optimized chat interface for all device sizes
- **Graceful Fallbacks** - Intelligent local responses when API unavailable
- **Source Attribution** - Clear indication of OpenAI vs fallback responses

## 🔬 Advanced Feature Engineering

### Automated Data Enrichment
- **40+ Calculated Features** - Automatically generated from raw parking data
- **Real-time Processing** - Features updated as new data arrives
- **Performance Optimized** - Efficient batch processing with database indexing
- **Analytics Ready** - Features designed for advanced visualizations and ML

### Feature Categories

#### 🕒 Temporal Features
- **Time Analysis**: Hour, day of week, month, quarter, season
- **Business Intelligence**: Weekend detection, business hours, peak hours
- **Pattern Recognition**: Night entries, seasonal trends

#### ⏱️ Duration Features  
- **Smart Categories**: Short (≤30min), Medium (30min-2h), Long (2h-8h), Extended (>8h)
- **Efficiency Scoring**: 0-100 efficiency rating based on optimal duration
- **Overstay Detection**: Automatic policy violation identification

#### 🚗 Vehicle Behavior Features
- **Usage Classification**: Frequent, Regular, Occasional, Rare visitors
- **Revenue Tiers**: High, Medium, Low, Minimal revenue contributors
- **Multi-site Analysis**: Cross-location behavior tracking
- **Visit Patterns**: Daily, Weekly, Monthly, Rare frequency analysis

#### 🏢 Organization Intelligence
- **Size Categories**: Large, Medium, Small, Micro organizations
- **Performance Tiers**: Excellent, Good, Average, Poor performers
- **Capacity Analysis**: Vehicle count and revenue correlation

#### 🧠 Behavioral Analytics
- **Anomaly Detection**: Duration and payment pattern anomalies
- **Loyalty Metrics**: Days since last visit, return patterns
- **Predictive Indicators**: Visit frequency classification

#### 💰 Financial Intelligence
- **Revenue Efficiency**: Revenue per minute calculations
- **Payment Analysis**: Digital vs traditional payment patterns
- **Profitability Scoring**: Payment efficiency ratings

### Usage Instructions

```bash
# Run feature engineering on existing data
python manage.py run_feature_engineering

# Dry run to see what would be processed
python manage.py run_feature_engineering --dry-run

# Process with custom chunk size
python manage.py run_feature_engineering --chunk-size 500
```

## 🚀 Key Modules

### 1. Vehicle Tracking (`/vehicle-tracking/`)
- Real-time vehicle location monitoring with **Leaflet.js mapping**
- **Interactive map** with organization markers and distance calculations
- Current status and coordinates with **red marker styling**
- Daily summary statistics
- **Free mapping solution** using OpenStreetMap

### 2. Movement History (`/movement-history/`)
- Complete trip history with filtering
- Route details and statistics
- Time, distance, and fuel consumption data
- Date range and vehicle filtering

### 3. AI Assistant (Integrated across all pages)
- **Advanced AI Integration** - OpenAI GPT-powered responses with intelligent fallback algorithms
- **Context-Aware Analysis** - Real-time data interpretation from current page metrics
- **Smart Chat Interface** - Interactive chat with typing indicators and contextual suggestions
- **Detailed Report Generation** - AI-powered comprehensive reports with insights and recommendations
- **Predictive Analytics** - Forecasting, trend analysis, and optimization suggestions
- **Multi-Page Integration** - Available on Dashboard, Analytics, and Vehicle Alert pages

### 4. Reports (`/reports/`)
- **Movement Summary** - Comprehensive movement overview
- **Route Analysis** - Most frequent routes and patterns
- **Fuel Consumption** - Usage and cost analysis
- **Weekly Summary** - Daily breakdown of activities
- **Performance Metrics** - KPIs and efficiency ratings
- **Location History** - Most visited locations

### 5. **Enhanced Analytics Dashboard** (`/analytics/`)
- **Advanced Filtering System**:
  - Organization filter (for super admins)
  - **Vehicle Brand filter** (populated from actual dataset)
  - **Vehicle Type filter** (populated from actual dataset)
  - **Reset Filters button** for quick return to default view
- **Real-time Visualizations**:
  - **Parking Duration Analysis** - Bar chart by organization
  - **Hourly Vehicle Entries** - Line chart showing entry patterns
  - **Vehicles per Organization** - **Interactive pie chart** with legend
  - **Revenue per Organization** - Bar chart with **logarithmic scale** and hover details
  - **Vehicle Visit Patterns** - Visit frequency analysis
  - **Average Stay by Vehicle Type** - Duration comparison
- **Comprehensive PDF Export**:
  - **One-click download** of complete analytics report
  - **Executive summary** with key metrics
  - **Driver performance** analysis
  - **Route analysis** with frequency data
  - **Cost analysis** and recommendations
  - **Automated insights** based on fleet performance
  - **Filtered reports** respecting all applied filters
- **Data Accuracy**: Uses **ParkingRecord table** for precise vehicle counts
- **Performance Optimized**: Database-level filtering with Django ORM

### 6. Profile Management (`/profile/`)
- Complete user profile with personal information
- Document upload and management
- Activity history and audit logs
- Security settings and preferences

### 7. Inventory Management (`/inventory/`)
- Vehicle inventory with VIN tracking and status management
- Parts inventory with stock levels and categories
- Low stock alerts and automatic status updates
- Add new items with dynamic forms (vehicle/part specific fields)
- Export inventory reports in CSV and PDF formats
- Configurable settings for stock management

### 8. Sales Management (`/sales/`)
- Vehicle sales tracking with customer information
- Sales performance metrics and revenue tracking
- Customer management with purchase history
- Sales status tracking (completed, pending, cancelled)

### 9. Manufacturing (`/manufacturing/`)
- Production line monitoring with real-time progress
- Production order management and tracking
- Efficiency metrics and completion rates
- Multi-line production with status indicators

### 10. Purchasing (`/purchasing/`)
- Purchase order management and tracking
- Supplier relationship management
- Order status tracking and delivery monitoring
- Budget tracking and cost analysis

### 11. Super Admin Management (`/super-admin-dashboard/`)
- System-wide organization management
- Enhanced organization creation with structured forms
- User management across all organizations
- System activity monitoring and audit logs
- Organization admin assignment and management

### 12. HR Dashboard (`/hr-dashboard/`)
- Employee management and analytics
- Department and role distribution tracking
- Profile completion monitoring
- Document verification management
- Export capabilities for HR reports

### 13. Data Processing (`/data-preprocessing/`)
- Excel file import and processing
- **Advanced Feature Engineering** - Enriches data with 40+ calculated features
- **Temporal Features** - Hour, day, season, peak hours, business hours analysis
- **Duration Features** - Categories, efficiency scores, overstay detection
- **Vehicle Features** - Usage patterns, revenue tiers, multi-site behavior
- **Organization Features** - Size categories, performance tiers
- **Behavioral Features** - Anomaly detection, visit frequency patterns
- **Financial Features** - Revenue efficiency, payment method analysis
- Vehicle and movement data creation
- Organization mapping and creation
- Data validation and cleaning

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
OPENAI_API_KEY=your-openai-api-key-here  # Optional: For AI assistant
```

### AI Assistant Setup
To enable OpenAI-powered responses:
1. Get an API key from OpenAI
2. Add `OPENAI_API_KEY=your-key-here` to your `.env` file
3. The system automatically switches to AI mode when key is detected
4. Fallback algorithms provide intelligent responses without API key

### Database Models
- **CustomUser** - Extended user model with role-based permissions
- **Organization** - Multi-tenant organization support with enhanced fields
- **UserProfile** - Extended profile information with audit logging
- **Document** - File upload and management with expiration tracking
- **ActivityLog** - Comprehensive audit logging with IP and user agent tracking
- **Notification** - User notification system with read status
- **InventoryItem** - Vehicle and parts inventory management with status tracking
- **ProfileAuditLog** - Profile change tracking and history
- **UserPermission** - Granular module-level permissions

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

## 🚀 Advanced Features

### Data Processing & Import
- **Excel Data Import** - Process multiple Excel files with vehicle movement data
- **Feature Engineering** - Advanced data transformation and enhancement
- **Data Validation** - Comprehensive validation and error handling
- **Batch Processing** - Handle large datasets efficiently

### Export & Reporting
- **Multi-format Export** - CSV, PDF, and Excel export capabilities
- **Professional PDF Reports** - Formatted reports with tables and charts
- **Inventory Reports** - Detailed vehicle and parts inventory reports
- **HR Reports** - Employee and organization analytics

### UI/UX Enhancements
- **Dynamic Forms** - Conditional field display based on selections
- **Modal Interfaces** - Clean popup forms for data entry
- **Progress Tracking** - Visual progress bars for production and tasks
- **Status Management** - Color-coded status badges and indicators
- **Interactive Dropdowns** - Context-sensitive action menus

### System Administration
- **Enhanced Organization Creation** - Structured forms with validation
- **User Role Management** - Granular permission control
- **Activity Monitoring** - Comprehensive system audit trails
- **Settings Management** - Configurable system preferences

## 🔒 Security Features

- **Role-based Access Control** - Granular permissions system with module-level access
- **Activity Logging** - Complete audit trail with IP addresses and user agents
- **Secure Authentication** - Password hashing, session management, and forced password changes
- **CSRF Protection** - Built-in Django CSRF middleware
- **Input Validation** - Server-side validation for all forms with error handling
- **File Upload Security** - Restricted file types, sizes, and secure storage
- **Profile Audit Logging** - Track all profile changes with before/after values
- **Temporary Password System** - Secure password reset with forced changes
- **Organization Isolation** - Complete data separation between organizations

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
- **v1.4.0** - Added business modules (Inventory, Sales, Manufacturing, Purchasing)
- **v1.4.1** - Enhanced inventory with add items, export (CSV/PDF), and settings
- **v1.5.0** - Enhanced organization management with structured forms and validation
- **v1.5.1** - Added comprehensive data processing and Excel import capabilities
- **v1.6.0** - **Enhanced Analytics Dashboard** with advanced filtering, interactive visualizations, and comprehensive PDF export
- **v1.6.1** - Added **Leaflet.js mapping** with free OpenStreetMap integration and interactive organization markers
- **v1.6.2** - Implemented **multi-dimensional filtering** (Organization, Vehicle Brand, Vehicle Type) with reset functionality
- **v1.7.0** - **Advanced AI Assistant Integration** with OpenAI GPT support, context-aware analysis, predictive insights, and intelligent report generation across Dashboard, Analytics, and Vehicle Alert pages
- **v1.8.0** - **Advanced Feature Engineering System** with 40+ calculated features including temporal, behavioral, financial, and anomaly detection capabilities for enhanced analytics

---

**Vehicle Intelligence System** - Empowering smart vehicle movement analytics with AI-driven insights.