from flask import render_template, redirect, url_for, request, flash
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import User
from app.forms import LoginForm, RegistrationForm
from app.main import main_bp

@main_bp.route('/')
def index():
    """Home page"""
    if current_user.is_authenticated:
        if current_user.role == 'user':
            return redirect(url_for('user.dashboard'))
        else:
            return redirect(url_for('admin.dashboard'))
    return render_template('index.html')

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('index.html')

@main_bp.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')

@main_bp.route('/health')
def health():
    """Health check endpoint - shows system status"""
    try:
        from app.models import User
        user_count = User.query.count()
        admin_count = User.query.filter_by(role='admin').count()
        
        return {
            'status': 'healthy',
            'database': 'connected',
            'users': user_count,
            'admins': admin_count,
            'message': 'RiskRadar is running!'
        }, 200
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }, 500

@main_bp.route('/logout')
@login_required
def logout():
    """Logout route"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(username=form.username.data).first()
            
            if user is None:
                flash(f'User "{form.username.data}" not found. Please check your username.', 'danger')
                return render_template('login.html', form=form)
            
            if not user.check_password(form.password.data):
                flash('Invalid password. Please try again.', 'danger')
                return render_template('login.html', form=form)
            
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'warning')
                return render_template('login.html', form=form)
            
            # Update last login timestamp
            try:
                user.last_login = datetime.utcnow()
                db.session.commit()
            except Exception as e:
                # Don't fail login if timestamp update fails
                db.session.rollback()
                print(f"Warning: Could not update last_login: {e}")
            
            # Log the user in
            login_user(user, remember=form.remember_me.data)
            
            # Role-based redirect
            if user.role == 'user':
                flash(f'Welcome back, {user.first_name}!', 'success')
                return redirect(url_for('user.dashboard'))
            else:  # officer or admin
                flash(f'Welcome back, {user.first_name}!', 'success')
                return redirect(url_for('admin.dashboard'))
                
        except Exception as e:
            flash(f'Login error: {str(e)}', 'danger')
            print(f"Login error: {e}")
            return render_template('login.html', form=form)
    
    # Show form validation errors
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return render_template('login.html', form=form)

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            aadhar_number=form.aadhar_number.data,
            role='user'
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        
        try:
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('main.login'))
        except IntegrityError:
            db.session.rollback()
            # Check which field caused the error
            if User.query.filter_by(username=form.username.data).first():
                flash('Username already exists.', 'danger')
            elif User.query.filter_by(email=form.email.data).first():
                flash('Email already exists.', 'danger')
            else:
                flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register.html', form=form)
