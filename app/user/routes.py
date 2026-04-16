from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Claim, Document, AuditLog
from app.forms import ClaimForm, DocumentUploadForm
from app.utils.helpers import save_uploaded_file, log_audit_event, format_currency, format_risk_score
from app.services.integration_service import integration_service
from app.user import user_bp
from datetime import datetime
import os

@user_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    # Get user's claims statistics
    claims = Claim.query.filter_by(user_id=current_user.id).order_by(Claim.submission_date.desc()).limit(5).all()
    
    stats = {
        'total_claims': Claim.query.filter_by(user_id=current_user.id).count(),
        'approved_claims': Claim.query.filter_by(user_id=current_user.id, decision='approved').count(),
        'pending_claims': Claim.query.filter_by(user_id=current_user.id, status='submitted').count(),
        'under_review_claims': Claim.query.filter_by(user_id=current_user.id, status='under_review').count()
    }
    
    return render_template('user/dashboard.html', 
                         claims=claims, 
                         stats=stats,
                         format_currency=format_currency,
                         format_risk_score=format_risk_score)

@user_bp.route('/claims')
@login_required
def view_claims():
    """View all claims"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    claims = Claim.query.filter_by(user_id=current_user.id)\
                       .order_by(Claim.submission_date.desc())\
                       .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('user/view_claims.html', 
                         claims=claims,
                         format_currency=format_currency,
                         format_risk_score=format_risk_score)

@user_bp.route('/claim/<int:claim_id>')
@login_required
def claim_details(claim_id):
    """View claim details"""
    claim = Claim.query.filter_by(id=claim_id, user_id=current_user.id).first_or_404()
    documents = Document.query.filter_by(claim_id=claim_id).all()
    
    # Get analysis results if available
    analysis_results = None
    if claim.analysis_results:
        analysis_results = integration_service.get_analysis_report(claim_id)
    
    return render_template('user/claim_details.html', 
                         claim=claim, 
                         documents=documents,
                         analysis_results=analysis_results,
                         format_currency=format_currency,
                         format_risk_score=format_risk_score)

@user_bp.route('/claim/new', methods=['GET', 'POST'])
@login_required
def new_claim():
    """Submit new claim"""
    form = ClaimForm()
    
    # Debug logging
    if request.method == 'POST':
        current_app.logger.info("=== CLAIM SUBMISSION DEBUG ===")
        current_app.logger.info(f"Form submitted: {form.is_submitted()}")
        current_app.logger.info(f"Form data: {request.form}")
        current_app.logger.info(f"Form errors: {form.errors}")
        current_app.logger.info(f"Form validate: {form.validate()}")
    
    if form.validate_on_submit():
        try:
            current_app.logger.info("Form validation passed, creating claim...")
            
            # Create new claim
            claim = Claim(
                user_id=current_user.id,
                policy_number=form.policy_number.data,
                policy_type=form.policy_type.data,
                claim_type=form.claim_type.data,
                amount=form.amount.data,
                incident_date=form.incident_date.data,
                incident_location=form.incident_location.data,
                description=form.description.data,
                submission_date=datetime.utcnow(),
                status='submitted'
            )
            
            db.session.add(claim)
            db.session.flush()  # Get the claim ID without committing
            
            current_app.logger.info(f"Claim created with ID: {claim.id}")
            
            # Handle file uploads
            files = request.files.getlist('file')
            if files and files[0].filename:  # Check if files were uploaded
                for file in files:
                    if file and file.filename:
                        file_info = save_uploaded_file(file, claim.id)
                        
                        document = Document(
                            claim_id=claim.id,
                            document_type=form.document_type.data if form.document_type.data else 'other',
                            original_filename=file_info['original_name'],
                            file_path=file_info['file_path'],
                            file_size=file_info['size'],
                            mime_type=file_info['mime_type'],
                            upload_date=datetime.utcnow()
                        )
                        
                        db.session.add(document)
                        current_app.logger.info(f"Document added: {file_info['original_name']}")
            
            db.session.commit()
            current_app.logger.info("Claim committed to database successfully")
            
            # Trigger AI analysis in background
            try:
                current_app.logger.info(f"Triggering AI analysis for claim {claim.id}")
                analysis_result = integration_service.process_claim(claim.id)
                if analysis_result['success']:
                    current_app.logger.info(f"AI analysis completed. Risk score: {analysis_result['overall_risk_score']}")
                else:
                    current_app.logger.error(f"AI analysis failed: {analysis_result.get('error')}")
            except Exception as e:
                current_app.logger.error(f"Error triggering AI analysis: {str(e)}")
                # Don't fail the claim submission if analysis fails
            
            # Log audit event
            log_audit_event(
                user_id=current_user.id,
                action='claim_submission',
                resource_type='claim',
                resource_id=claim.id,
                details={
                    'claim_type': claim.claim_type,
                    'amount': float(claim.amount),
                    'documents_count': len(files) if files else 0
                },
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            flash('Claim submitted successfully! It will be processed shortly.', 'success')
            return redirect(url_for('user.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting claim: {str(e)}")
            import traceback
            current_app.logger.error(traceback.format_exc())
            flash(f'Error submitting claim: {str(e)}', 'danger')
    else:
        if request.method == 'POST':
            current_app.logger.error(f"Form validation failed: {form.errors}")
            flash('Please correct the errors in the form.', 'danger')
    
    return render_template('user/new_claim.html', form=form)

@user_bp.route('/profile')
@login_required
def profile():
    """User profile"""
    # Get user's claim statistics
    stats = {
        'total_claims': Claim.query.filter_by(user_id=current_user.id).count(),
        'approved_claims': Claim.query.filter_by(user_id=current_user.id, decision='approved').count(),
        'pending_claims': Claim.query.filter_by(user_id=current_user.id, status='submitted').count(),
        'under_review_claims': Claim.query.filter_by(user_id=current_user.id, status='under_review').count()
    }
    
    return render_template('user/profile.html', user=current_user, stats=stats)

@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    from app.forms import UserProfileForm
    
    form = UserProfileForm(obj=current_user)
    form.user_id = current_user.id  # For email validation
    
    if form.validate_on_submit():
        try:
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.email = form.email.data
            current_user.phone = form.phone.data
            
            db.session.commit()
            
            log_audit_event(
                user_id=current_user.id,
                action='profile_update',
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('user.profile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating profile: {str(e)}")
            flash('Error updating profile. Please try again.', 'danger')
    
    return render_template('user/edit_profile.html', form=form)

@user_bp.route('/documents/<int:document_id>')
@login_required
def view_document(document_id):
    """View document"""
    document = Document.query.join(Claim).filter(
        Document.id == document_id,
        Claim.user_id == current_user.id
    ).first_or_404()
    
    # In a real application, you would serve the file securely
    # For now, we'll just show document info
    return render_template('user/view_document.html', document=document)
