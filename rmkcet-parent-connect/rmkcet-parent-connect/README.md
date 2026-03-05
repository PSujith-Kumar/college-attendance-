# RMKCET Parent Connect

A web-based system for managing student-parent communication at RMKCET. Counselors can upload student data, manage test marks, and generate progress reports to send to parents via WhatsApp.

## Project Structure

```
rmkcet-parent-connect/
├── backend/                 # Flask backend application
│   ├── app.py              # Main Flask application
│   ├── database.py         # Database operations (SQLite)
│   ├── config.py           # Configuration settings
│   ├── requirements.txt    # Python dependencies
│   ├── migrate_db.py       # Database migration script
│   ├── core/               # Core business logic
│   │   ├── dynamic_parser.py
│   │   ├── excel_detective.py
│   │   ├── intelligent_parser.py
│   │   └── student_matcher.py
│   ├── models/             # Data models
│   │   ├── data_models.py
│   │   └── test_metadata.py
│   ├── utils/              # Utility functions
│   │   ├── email_helper.py
│   │   ├── pdf_generator.py
│   │   ├── template_engine.py
│   │   ├── validators.py
│   │   └── whatsapp_helper.py
│   └── data/               # Database and assets
├── frontend/               # Frontend templates and assets
│   ├── templates/          # HTML templates
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── admin.html
│   │   └── counselor.html
│   └── static/             # Static files
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── app.js
├── .env                    # Environment variables
├── .gitignore
└── start.bat               # Windows launcher script
```

## Features

- **Admin Panel**: Manage users, departments, and system settings
- **Counselor Dashboard**: Upload student data, manage test marks, generate reports
- **Student Management**: Import students from Excel files
- **Marks Management**: Upload and track test marks
- **Report Generation**: Generate progress reports with WhatsApp integration
- **Session Management**: Secure authentication with session tracking

## Installation

### Prerequisites
- Python 3.10+
- pip (Python package manager)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/rmkcet-parent-connect.git
   cd rmkcet-parent-connect
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

5. **Configure environment** (optional)
   - Copy `.env.example` to `.env`
   - Update settings as needed

6. **Run the application**
   - Windows: Double-click `start.bat`
   - Or run: `python backend/app.py`

7. **Access the application**
   - Open http://localhost:5000 in your browser

## Default Login

- **Email**: admin@rmkcet.ac.in
- **Password**: Admin@123

## Environment Variables

Create a `.env` file with:
```
SECRET_KEY=your-secret-key
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## License

This project is for educational purposes at RMKCET.
