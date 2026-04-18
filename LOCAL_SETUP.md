# 🚀 RiskRadar - Local Setup Guide

This guide will help you set up RiskRadar on your local machine.

## 📋 Prerequisites

- Python 3.10 or higher
- Git
- pip (Python package manager)

## 🔧 Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/pranav-358/RiskRadar_1.git
cd RiskRadar
```

### 2. Create Virtual Environment (Recommended)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database

Run the setup script to create the database and default users:

```bash
python setup_local.py
```

This will:
- Create the SQLite database
- Create all necessary tables
- Add default admin and user accounts
- Configure system settings

### 5. Run the Application

```bash
python run.py
```

The application will start on `http://127.0.0.1:7860`

## 🔐 Default Login Credentials

**Admin Account:**
- Username: `admin`
- Password: `admin123`

**User Account:**
- Username: `user`
- Password: `user123`

## 📁 Project Structure

```
RiskRadar/
├── app/                    # Main application package
│   ├── admin/             # Admin blueprint
│   ├── ai_models/         # AI/ML models
│   ├── main/              # Main blueprint (auth, home)
│   ├── models/            # Database models
│   ├── static/            # Static files (CSS, JS, images)
│   ├── templates/         # HTML templates
│   ├── user/              # User blueprint
│   └── utils/             # Utility functions
├── instance/              # Instance folder (database)
├── migrations/            # Database migrations
├── training_data/         # ML training data
├── requirements.txt       # Python dependencies
├── run.py                # Application entry point
└── setup_local.py        # Local setup script
```

## 🐛 Troubleshooting

### Database Error: "no such table: users"

This means the database hasn't been initialized. Run:
```bash
python setup_local.py
```

### Import Errors

Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Port Already in Use

If port 7860 is already in use, you can change it in `run.py`:
```python
app.run(host='0.0.0.0', port=5000, debug=True)  # Change to any available port
```

### AI Model Warnings

If you see warnings about missing AI models, you can train them:
```bash
python train_models.py
```

This is optional - the app will work with rule-based fallbacks.

## 🔄 Resetting the Database

If you need to start fresh:

1. Delete the database file:
   ```bash
   rm instance/riskradar.db
   ```

2. Run setup again:
   ```bash
   python setup_local.py
   ```

## 📝 Environment Variables (Optional)

Create a `.env` file in the project root for custom configuration:

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/riskradar.db
FLASK_ENV=development
```

## 🚀 Running in Production

For production deployment, use a production WSGI server like Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:7860 run:app
```

## 📞 Support

If you encounter any issues:
1. Check the console output for error messages
2. Ensure all dependencies are installed
3. Verify Python version is 3.10+
4. Check that the database was initialized properly

## 🎯 Next Steps

After successful setup:
1. Login with admin credentials
2. Explore the admin dashboard
3. Create test claims as a user
4. Review the AI analysis features

---

**Happy Coding! 🎉**
