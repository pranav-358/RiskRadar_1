import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
import magic
from datetime import datetime

def allowed_file(filename, allowed_extensions):
    """
    Check if file has allowed extension
    
    Args:
        filename (str): Name of the file
        allowed_extensions (set): Set of allowed extensions
        
    Returns:
        bool: True if allowed, False otherwise
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, upload_folder, claim_id):
    """
    Save uploaded file with unique name
    
    Args:
        file: File object from request
        upload_folder (str): Path to upload folder
        claim_id (str): Claim ID for organization
        
    Returns:
        dict: File information including saved path
    """
    try:
        # Create claim directory if it doesn't exist
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
        pass
