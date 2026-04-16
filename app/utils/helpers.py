import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import magic
from flask import current_app
from app import db
from app.models import AuditLog
import json

def allowed_file(filename, allowed_extensions=None):
    """
    Check if file has allowed extension
    
    Args:
        filename (str): Name of the file
        allowed_extensions (set): Set of allowed extensions
        
    Returns:
        bool: True if allowed, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp'}
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, claim_id):
    """
    Save uploaded file with unique name
    
    Args:
        file: File object from request
        claim_id (str): Claim ID for organization
        
    Returns:
        dict: File information including saved path
    """
    try:
        # Create claim directory if it doesn't exist
        upload_folder = current_app.config['UPLOAD_FOLDER']
        claim_dir = os.path.join(upload_folder, str(claim_id))
        os.makedirs(claim_dir, exist_ok=True)
        
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Save file
        file_path = os.path.join(claim_dir, unique_filename)
        file.save(file_path)
        
        # Get file type using magic
        file_type = magic.from_file(file_path, mime=True)
        is_image = file_type.startswith('image/')
        is_pdf = file_type == 'application/pdf'
        
        # Create thumbnail for images
        thumbnail_path = None
        if is_image:
            thumbnail_path = os.path.join(claim_dir, f"thumb_{unique_filename}")
            with Image.open(file_path) as img:
                img.thumbnail((200, 200))
                img.save(thumbnail_path, format=img.format if img.format else 'JPEG')
        
        return {
            'original_name': original_filename,
            'saved_name': unique_filename,
            'file_path': file_path,
            'thumbnail_path': thumbnail_path,
            'file_type': 'image' if is_image else 'pdf' if is_pdf else 'other',
            'mime_type': file_type,
            'upload_time': datetime.now().isoformat(),
            'size': os.path.getsize(file_path)
        }
        
    except Exception as e:
        raise Exception(f"Error saving file: {str(e)}")

def cleanup_file(file_path):
    """
    Safely remove a file
    
    Args:
        file_path (str): Path to file to remove
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        # Log error but don't raise exception during cleanup
        current_app.logger.error(f"Error cleaning up file {file_path}: {str(e)}")

def log_audit_event(user_id, action, details=None, resource_type=None, 
                   resource_id=None, ip_address=None, user_agent=None):
    """
    Log an audit event
    
    Args:
        user_id (int): ID of the user performing the action
        action (str): Action performed
        details (dict): Additional details about the action
        resource_type (str): Type of resource affected
        resource_id (int): ID of resource affected
        ip_address (str): IP address of user
        user_agent (str): User agent string
    """
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow()
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error logging audit event: {str(e)}")
        db.session.rollback()

def generate_synthetic_training_data(num_samples=1000):
    """
    Generate synthetic training data for model training
    """
    import numpy as np
    from datetime import datetime, timedelta
    import random
    
    np.random.seed(42)
    random.seed(42)
    
    data = []
    user_ids = [f"USER_{i:04d}" for i in range(1, 101)]
    claim_types = ['auto', 'health', 'property', 'life']
    locations = ['urban', 'suburban', 'rural']
    policy_types = ['comprehensive', 'basic', 'premium']
    
    start_date = datetime(2020, 1, 1)
    
    for i in range(num_samples):
        user_id = random.choice(user_ids)
        
        # Determine if this is a fraudulent claim (15% fraud rate)
        is_fraud = np.random.random() < 0.15
        
        # Generate claim date (spread over 3 years)
        days_offset = random.randint(0, 3 * 365)
        claim_date = start_date + timedelta(days=days_offset)
        
        # Base claim amount based on type
        base_amounts = {
            'auto': np.random.lognormal(9, 1.2),      # ~₹10,000-100,000
            'health': np.random.lognormal(10, 1.0),    # ~₹20,000-200,000  
            'property': np.random.lognormal(11, 1.3),  # ~₹50,000-500,000
            'life': np.random.lognormal(12, 1.1)       # ~₹100,000-1,000,000
        }
        
        claim_type = random.choice(claim_types)
        base_amount = base_amounts[claim_type]
        
        # Adjust amount for fraudulent claims
        claim_amount = base_amount
        if is_fraud:
            claim_amount *= np.random.uniform(1.5, 5.0)
        
        # Add some random noise
        claim_amount *= np.random.uniform(0.8, 1.2)
        
        claim_data = {
            'user_id': user_id,
            'claim_id': f"CLM_{10000 + i}",
            'claim_amount': round(claim_amount, 2),
            'claim_type': claim_type,
            'incident_location': random.choice(locations),
            'policy_type': random.choice(policy_types),
            'age_of_policy': random.randint(0, 3650),  # 0-10 years
            'submission_date': claim_date.strftime('%Y-%m-%d'),
            'submission_time': f"{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:00",
            'document_verification_score': np.random.beta(2, 5) * 100,  # Most documents are authentic
            'behavioral_anomaly_score': np.random.beta(2, 8) * 100,     # Most behavior is normal
            'hidden_link_score': np.random.beta(1, 9) * 100,           # Most have no hidden links
            'is_fraud': 1 if is_fraud else 0
        }
        
        data.append(claim_data)
    
    return data

def format_currency(amount):
    """
    Format amount as Indian currency
    
    Args:
        amount (float): Amount to format
        
    Returns:
        str: Formatted currency string
    """
    if amount is None:
        return "₹0.00"
    
    if amount >= 10000000:  # 1 crore
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:  # 1 lakh
        return f"₹{amount/100000:.2f} L"
    else:
        return f"₹{amount:,.2f}"

def format_risk_score(score):
    """
    Format risk score with appropriate color coding
    
    Args:
        score (float): Risk score (0-100)
        
    Returns:
        dict: Formatted score with color and text
    """
    if score is None:
        return {"score": "N/A", "color": "secondary", "text": "Not analyzed"}
    
    if score >= 80:
        return {"score": f"{score:.1f}", "color": "danger", "text": "Very High"}
    elif score >= 65:
        return {"score": f"{score:.1f}", "color": "warning", "text": "High"}
    elif score >= 45:
        return {"score": f"{score:.1f}", "color": "info", "text": "Medium"}
    elif score >= 30:
        return {"score": f"{score:.1f}", "color": "primary", "text": "Low"}
    else:
        return {"score": f"{score:.1f}", "color": "success", "text": "Very Low"}
