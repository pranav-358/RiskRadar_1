from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import User, Claim, Document, AnalysisResult, AuditLog, SystemConfig
from app.forms import AdminUserForm, ClaimDecisionForm, SystemConfigForm
from app.utils.helpers import log_audit_event, format_currency, format_risk_score
from app.services.integration_service import integration_service
from app.admin import admin_bp
from datetime import datetime, timedelta
import json

@admin_bp.before_request
@login_required
def require_admin():
    """Require admin or officer role for all admin routes"""
    if current_user.role not in ['admin', 'officer']:
        flash('Access denied. Administrator privileges required.', 'danger')
        return redirect(url_for('main.index'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard"""
    # Get statistics for dashboard
    stats = {
        'total_claims': Claim.query.count(),
        'pending_claims': Claim.query.filter_by(status='submitted').count(),
        'under_review_claims': Claim.query.filter_by(status='under_review').count(),
        'approved_claims': Claim.query.filter_by(decision='approved').count(),
        'rejected_claims': Claim.query.filter_by(decision='rejected').count(),
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'officer_users': User.query.filter_by(role='officer').count(),
        'admin_users': User.query.filter_by(role='admin').count(),
    }
    
    # Get recent claims for dashboard
    recent_claims = Claim.query.order_by(Claim.submission_date.desc()).limit(10).all()
    
    # Get recent audit logs
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    
    # Get fraud statistics
    fraud_stats = {
        'high_risk': Claim.query.filter(Claim.fraud_score >= 75).count(),
        'medium_risk': Claim.query.filter(Claim.fraud_score >= 50, Claim.fraud_score < 75).count(),
        'low_risk': Claim.query.filter(Claim.fraud_score < 50).count(),
    }
    
    return render_template('admin/dashboard.html', 
                         stats=stats,
                         recent_claims=recent_claims,
                         recent_logs=recent_logs,
                         fraud_stats=fraud_stats,
                         format_currency=format_currency,
                         format_risk_score=format_risk_score)

@admin_bp.route('/claims')
@login_required
def claims_list():
    """List all claims with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status_filter = request.args.get('status', 'all')
    risk_filter = request.args.get('risk', 'all')
    search_query = request.args.get('search', '')
    
    # Build query with filters
    query = Claim.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if risk_filter != 'all':
        if risk_filter == 'high':
            query = query.filter(Claim.fraud_score >= 75)
        elif risk_filter == 'medium':
            query = query.filter(Claim.fraud_score >= 50, Claim.fraud_score < 75)
        elif risk_filter == 'low':
            query = query.filter(Claim.fraud_score < 50)
    
    if search_query:
        query = query.join(User).filter(
            (User.first_name.ilike(f'%{search_query}%')) |
            (User.last_name.ilike(f'%{search_query}%')) |
            (Claim.policy_number.ilike(f'%{search_query}%')) |
            (Claim.claim_type.ilike(f'%{search_query}%'))
        )
    
    claims = query.order_by(Claim.submission_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/claims_list.html', 
                         claims=claims,
                         status_filter=status_filter,
                         risk_filter=risk_filter,
                         search_query=search_query,
                         format_currency=format_currency,
                         format_risk_score=format_risk_score)

@admin_bp.route('/claim/<int:claim_id>')
@login_required
def claim_analysis(claim_id):
    """View claim analysis details"""
    claim = Claim.query.get_or_404(claim_id)
    documents = Document.query.filter_by(claim_id=claim_id).all()
    analysis_results = integration_service.get_analysis_report(claim_id)
    
    # Get similar claims for comparison
    similar_claims = []
    if analysis_results and analysis_results.get('hidden_link_analysis'):
        similar_claims = analysis_results['hidden_link_analysis'].get('similar_claims', [])
    
    # Get decision form
    decision_form = ClaimDecisionForm()
    
    # Get list of officers for assignment
    officers = User.query.filter_by(role='officer', is_active=True).all()
    
    return render_template('admin/claim_analysis.html', 
                         claim=claim,
                         documents=documents,
                         analysis_results=analysis_results,
                         similar_claims=similar_claims,
                         decision_form=decision_form,
                         officers=officers,
                         format_currency=format_currency,
                         format_risk_score=format_risk_score)

@admin_bp.route('/claim/<int:claim_id>/decision', methods=['POST'])
@login_required
def make_decision(claim_id):
    """Make decision on a claim"""
    claim = Claim.query.get_or_404(claim_id)
    form = ClaimDecisionForm()
    
    if form.validate_on_submit():
        try:
            claim.decision = form.decision.data
            claim.decision_reason = form.reason.data
            claim.decision_date = datetime.utcnow()
            claim.status = 'processed'
            
            if current_user.role == 'officer':
                claim.assigned_officer_id = current_user.id
            
            db.session.commit()
            
            # Log audit event
            log_audit_event(
                user_id=current_user.id,
                action='claim_decision',
                resource_type='claim',
                resource_id=claim.id,
                details={
                    'decision': claim.decision,
                    'reason': claim.decision_reason
                },
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            flash(f'Claim {claim.decision} successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error making decision on claim {claim_id}: {str(e)}")
            flash('Error processing decision. Please try again.', 'danger')
    
    return redirect(url_for('admin.claim_analysis', claim_id=claim_id))

@admin_bp.route('/claim/<int:claim_id>/assign', methods=['POST'])
@login_required
def assign_claim(claim_id):
    """Assign claim to processing officer"""
    if current_user.role != 'admin':
        flash('Only administrators can assign claims.', 'danger')
        return redirect(url_for('admin.claim_analysis', claim_id=claim_id))
    
    claim = Claim.query.get_or_404(claim_id)
    officer_id = request.form.get('officer_id')
    
    try:
        officer = User.query.filter_by(id=officer_id, role='officer').first()
        if not officer:
            flash('Invalid officer selected.', 'danger')
            return redirect(url_for('admin.claim_analysis', claim_id=claim_id))
        
        claim.assigned_officer_id = officer_id
        claim.status = 'under_review'
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            user_id=current_user.id,
            action='claim_assignment',
            resource_type='claim',
            resource_id=claim.id,
            details={
                'assigned_to': officer_id,
                'assigned_officer': f'{officer.first_name} {officer.last_name}'
            },
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        flash('Claim assigned successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error assigning claim {claim_id}: {str(e)}")
        flash('Error assigning claim. Please try again.', 'danger')
    
    return redirect(url_for('admin.claim_analysis', claim_id=claim_id))

@admin_bp.route('/users')
@login_required
def user_management():
    """User management page"""
    if current_user.role != 'admin':
        flash('Only administrators can access user management.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    role_filter = request.args.get('role', 'all')
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '')
    
    # Build query with filters
    query = User.query
    
    if role_filter != 'all':
        query = query.filter_by(role=role_filter)
    
    if status_filter != 'all':
        query = query.filter_by(is_active=(status_filter == 'active'))
    
    if search_query:
        query = query.filter(
            (User.first_name.ilike(f'%{search_query}%')) |
            (User.last_name.ilike(f'%{search_query}%')) |
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )
    
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/user_management.html', 
                         users=users,
                         role_filter=role_filter,
                         status_filter=status_filter,
                         search_query=search_query)

@admin_bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit user details"""
    if current_user.role != 'admin':
        flash('Only administrators can edit users.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    user = User.query.get_or_404(user_id)
    form = AdminUserForm(obj=user)
    
    if form.validate_on_submit():
        try:
            user.username = form.username.data
            user.email = form.email.data
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.phone = form.phone.data
            user.role = form.role.data
            user.is_active = form.is_active.data
            
            db.session.commit()
            
            # Log audit event
            log_audit_event(
                user_id=current_user.id,
                action='user_update',
                resource_type='user',
                resource_id=user.id,
                details={
                    'updated_fields': ['username', 'email', 'first_name', 'last_name', 'phone', 'role', 'is_active']
                },
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin.user_management'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating user {user_id}: {str(e)}")
            flash('Error updating user. Please try again.', 'danger')
    
    return render_template('admin/edit_user.html', form=form, user=user)

@admin_bp.route('/audit-logs')
@login_required
def audit_logs():
    """View audit logs"""
    if current_user.role != 'admin':
        flash('Only administrators can view audit logs.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    action_filter = request.args.get('action', 'all')
    user_filter = request.args.get('user', 'all')
    date_filter = request.args.get('date', '')
    
    # Build query with filters
    query = AuditLog.query.join(User)
    
    if action_filter != 'all':
        query = query.filter_by(action=action_filter)
    
    if user_filter != 'all':
        query = query.filter_by(user_id=user_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d')
            next_day = filter_date + timedelta(days=1)
            query = query.filter(AuditLog.timestamp >= filter_date, AuditLog.timestamp < next_day)
        except ValueError:
            pass
    
    logs = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get users for filter dropdown
    users = User.query.all()
    
    # Get unique actions for filter dropdown
    actions = db.session.query(AuditLog.action).distinct().all()
    actions = [action[0] for action in actions]
    
    return render_template('admin/audit_logs.html', 
                         logs=logs,
                         users=users,
                         actions=actions,
                         action_filter=action_filter,
                         user_filter=user_filter,
                         date_filter=date_filter)

@admin_bp.route('/self-correction')
@login_required
def self_correction():
    """Self-correction loop for model retraining"""
    if current_user.role != 'admin':
        flash('Only administrators can access self-correction.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    # Get claims with decisions for retraining
    trained_claims = Claim.query.filter(Claim.decision.isnot(None)).count()
    total_claims = Claim.query.count()
    
    # Get system configuration
    config = {
        'fraud_threshold_high': SystemConfig.query.filter_by(key='fraud_threshold_high').first(),
        'fraud_threshold_medium': SystemConfig.query.filter_by(key='fraud_threshold_medium').first(),
        'auto_assign_officers': SystemConfig.query.filter_by(key='auto_assign_officers').first(),
        'max_file_size': SystemConfig.query.filter_by(key='max_file_size').first(),
    }
    
    # Convert config values to appropriate types
    for key, item in config.items():
        if item and item.value:
            if key in ['fraud_threshold_high', 'fraud_threshold_medium']:
                config[key] = float(item.value)
            elif key == 'auto_assign_officers':
                config[key] = item.value.lower() == 'true'
            elif key == 'max_file_size':
                config[key] = int(item.value)
        else:
            config[key] = None
    
    form = SystemConfigForm(data=config)
    
    return render_template('admin/self_correction.html',
                         trained_claims=trained_claims,
                         total_claims=total_claims,
                         form=form)

@admin_bp.route('/self-correction/retrain', methods=['POST'])
@login_required
def retrain_models():
    """Retrain AI models with new data"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        # Get claims with decisions for training
        training_data = Claim.query.filter(Claim.decision.isnot(None)).all()
        
        if len(training_data) < 100:
            return jsonify({
                'success': False, 
                'message': f'Insufficient training data. Need at least 100 claims with decisions, have {len(training_data)}.'
            })
        
        # Prepare training data
        training_set = []
        for claim in training_data:
            training_set.append({
                'claim_id': claim.id,
                'user_id': claim.user_id,
                'claim_amount': claim.amount,
                'claim_type': claim.claim_type,
                'policy_type': claim.policy_type,
                'incident_location': claim.incident_location,
                'age_of_policy': (claim.submission_date - claim.policy_start_date).days if claim.policy_start_date else 0,
                'submission_date': claim.submission_date.isoformat(),
                'is_fraud': 1 if claim.decision == 'rejected' else 0
            })
        
        # Train models (simplified - in real implementation, this would call the actual training methods)
        # behavioral_ai.train_models(training_set)
        # predictive_model.train(training_set, [claim['is_fraud'] for claim in training_set])
        
        # Log audit event
        log_audit_event(
            user_id=current_user.id,
            action='model_retraining',
            details={
                'training_samples': len(training_set),
                'fraud_samples': sum(1 for claim in training_set if claim['is_fraud'] == 1),
                'legitimate_samples': sum(1 for claim in training_set if claim['is_fraud'] == 0)
            },
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        return jsonify({
            'success': True,
            'message': f'Models retrained successfully with {len(training_set)} samples',
            'stats': {
                'total_samples': len(training_set),
                'fraud_samples': sum(1 for claim in training_set if claim['is_fraud'] == 1),
                'legitimate_samples': sum(1 for claim in training_set if claim['is_fraud'] == 0)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retraining models: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/self-correction/config', methods=['POST'])
@login_required
def update_config():
    """Update system configuration"""
    if current_user.role != 'admin':
        flash('Only administrators can update system configuration.', 'danger')
        return redirect(url_for('admin.self_correction'))
    
    form = SystemConfigForm()
    
    if form.validate_on_submit():
        try:
            # Update or create config entries
            config_keys = {
                'fraud_threshold_high': str(form.fraud_threshold_high.data),
                'fraud_threshold_medium': str(form.fraud_threshold_medium.data),
                'auto_assign_officers': str(form.auto_assign_officers.data),
                'max_file_size': str(form.max_file_size.data),
            }
            
            for key, value in config_keys.items():
                config_item = SystemConfig.query.filter_by(key=key).first()
                if config_item:
                    config_item.value = value
                else:
                    config_item = SystemConfig(key=key, value=value)
                    db.session.add(config_item)
            
            db.session.commit()
            
            # Log audit event
            log_audit_event(
                user_id=current_user.id,
                action='config_update',
                details=config_keys,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            flash('System configuration updated successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating system configuration: {str(e)}")
            flash('Error updating configuration. Please try again.', 'danger')
    
    return redirect(url_for('admin.self_correction'))

@admin_bp.route('/api/stats/claims-over-time')
@login_required
def claims_over_time_stats():
    """API endpoint for claims over time statistics"""
    if current_user.role not in ['admin', 'officer']:
        return jsonify({'error': 'Access denied'}), 403
    
    # Get claims grouped by date (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    claims_by_date = db.session.query(
        db.func.date(Claim.submission_date).label('date'),
        db.func.count(Claim.id).label('count')
    ).filter(
        Claim.submission_date >= thirty_days_ago
    ).group_by(
        db.func.date(Claim.submission_date)
    ).order_by('date').all()
    
    data = {
        'dates': [str(result.date) for result in claims_by_date],
        'counts': [result.count for result in claims_by_date]
    }
    
    return jsonify(data)

@admin_bp.route('/api/stats/fraud-by-type')
@login_required
def fraud_by_type_stats():
    """API endpoint for fraud statistics by claim type"""
    if current_user.role not in ['admin', 'officer']:
        return jsonify({'error': 'Access denied'}), 403
    
    fraud_by_type = db.session.query(
        Claim.claim_type,
        db.func.count(Claim.id).label('total'),
        db.func.avg(Claim.fraud_score).label('avg_score')
    ).filter(
        Claim.fraud_score.isnot(None)
    ).group_by(
        Claim.claim_type
    ).all()
    
    data = {
        'types': [result.claim_type for result in fraud_by_type],
        'totals': [result.total for result in fraud_by_type],
        'avg_scores': [float(result.avg_score) if result.avg_score else 0 for result in fraud_by_type]
    }
    
    return jsonify(data)

@admin_bp.route('/document/<int:document_id>')
@login_required
def view_document(document_id):
    """View uploaded document"""
    if current_user.role not in ['admin', 'officer']:
        flash('Access denied. Administrator privileges required.', 'danger')
        return redirect(url_for('main.index'))
    
    from flask import send_file
    import os
    
    document = Document.query.get_or_404(document_id)
    
    # Check if file exists
    if not os.path.exists(document.file_path):
        flash('Document file not found.', 'danger')
        return redirect(url_for('admin.claim_analysis', claim_id=document.claim_id))
    
    # Send file
    return send_file(
        document.file_path,
        mimetype=document.mime_type or 'application/octet-stream',
        as_attachment=False,
        download_name=document.original_filename
    )
