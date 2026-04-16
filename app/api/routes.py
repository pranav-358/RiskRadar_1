from flask import jsonify, request, current_app
from flask_login import current_user, login_required
from app import db
from app.models import Claim, User, Document, AnalysisResult
from app.services.integration_service import integration_service
from app.utils.helpers import log_audit_event
from app.api import api_bp
from datetime import datetime, timedelta
import json

@api_bp.before_request
@login_required
def require_auth():
    """Require authentication for all API endpoints"""
    pass

@api_bp.route('/claims/<int:claim_id>/analyze', methods=['POST'])
def analyze_claim(claim_id):
    """API endpoint to analyze a specific claim"""
    try:
        if current_user.role not in ['admin', 'officer']:
            return jsonify({'error': 'Access denied. Officer or admin privileges required.'}), 403
        
        result = integration_service.process_claim(claim_id)
        
        if result['success']:
            # Log audit event
            log_audit_event(
                user_id=current_user.id,
                action='claim_analysis',
                resource_type='claim',
                resource_id=claim_id,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            return jsonify({
                'success': True,
                'message': 'Claim analysis completed',
                'risk_score': result['overall_risk_score'],
                'analysis_id': claim_id
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Analysis failed')
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error analyzing claim {claim_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@api_bp.route('/claims/batch-analyze', methods=['POST'])
def batch_analyze_claims():
    """API endpoint to analyze multiple claims in batch"""
    try:
        if current_user.role != 'admin':
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        claim_ids = request.json.get('claim_ids', [])
        
        if not claim_ids:
            return jsonify({'error': 'No claim IDs provided'}), 400
        
        result = integration_service.batch_process_claims(claim_ids)
        
        # Log audit event
        log_audit_event(
            user_id=current_user.id,
            action='batch_analysis',
            details={
                'total_claims': len(claim_ids),
                'processed': result['processed'],
                'succeeded': result['succeeded'],
                'failed': result['failed']
            },
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in batch analysis: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@api_bp.route('/claims/<int:claim_id>', methods=['GET'])
def get_claim_details(claim_id):
    """API endpoint to get claim details"""
    try:
        claim = Claim.query.get_or_404(claim_id)
        
        # Check permissions
        if current_user.role == 'user' and claim.user_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        claim_data = {
            'id': claim.id,
            'user_id': claim.user_id,
            'policy_number': claim.policy_number,
            'policy_type': claim.policy_type,
            'claim_type': claim.claim_type,
            'amount': claim.amount,
            'incident_date': claim.incident_date.isoformat() if claim.incident_date else None,
            'submission_date': claim.submission_date.isoformat() if claim.submission_date else None,
            'incident_location': claim.incident_location,
            'description': claim.description,
            'status': claim.status,
            'fraud_score': claim.fraud_score,
            'assigned_officer_id': claim.assigned_officer_id,
            'analysis_date': claim.analysis_date.isoformat() if claim.analysis_date else None,
            'decision': claim.decision,
            'decision_reason': claim.decision_reason,
            'decision_date': claim.decision_date.isoformat() if claim.decision_date else None
        }
        
        return jsonify(claim_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching claim {claim_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/claims/<int:claim_id>/documents', methods=['GET'])
def get_claim_documents(claim_id):
    """API endpoint to get claim documents"""
    try:
        claim = Claim.query.get_or_404(claim_id)
        
        # Check permissions
        if current_user.role == 'user' and claim.user_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        documents = Document.query.filter_by(claim_id=claim_id).all()
        documents_data = [{
            'id': doc.id,
            'document_type': doc.document_type,
            'original_filename': doc.original_filename,
            'file_size': doc.file_size,
            'mime_type': doc.mime_type,
            'upload_date': doc.upload_date.isoformat() if doc.upload_date else None,
            'authenticity_score': doc.authenticity_score,
            'is_tampered': doc.is_tampered,
            'analysis_date': doc.analysis_date.isoformat() if doc.analysis_date else None
        } for doc in documents]
        
        return jsonify(documents_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching documents for claim {claim_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/claims/<int:claim_id>/analysis', methods=['GET'])
def get_claim_analysis(claim_id):
    """API endpoint to get claim analysis results"""
    try:
        claim = Claim.query.get_or_404(claim_id)
        
        # Check permissions
        if current_user.role == 'user' and claim.user_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        analysis = integration_service.get_analysis_report(claim_id)
        
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        return jsonify(analysis)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching analysis for claim {claim_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/users/stats', methods=['GET'])
def get_user_stats():
    """API endpoint to get user statistics"""
    try:
        if current_user.role not in ['admin', 'officer']:
            return jsonify({'error': 'Access denied'}), 403
        
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        user_roles = db.session.query(
            User.role, 
            db.func.count(User.id)
        ).group_by(User.role).all()
        
        # User registration over time (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        registrations_by_date = db.session.query(
            db.func.date(User.created_at).label('date'),
            db.func.count(User.id).label('count')
        ).filter(
            User.created_at >= thirty_days_ago
        ).group_by(
            db.func.date(User.created_at)
        ).order_by('date').all()
        
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'roles': {role: count for role, count in user_roles},
            'registrations_over_time': {
                'dates': [str(result.date) for result in registrations_by_date],
                'counts': [result.count for result in registrations_by_date]
            }
        }
        
        return jsonify(stats)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching user stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/system/stats', methods=['GET'])
def get_system_stats():
    """API endpoint to get system statistics"""
    try:
        if current_user.role not in ['admin', 'officer']:
            return jsonify({'error': 'Access denied'}), 403
        
        # Claim statistics
        total_claims = Claim.query.count()
        claims_by_status = db.session.query(
            Claim.status, 
            db.func.count(Claim.id)
        ).group_by(Claim.status).all()
        
        claims_by_type = db.session.query(
            Claim.claim_type, 
            db.func.count(Claim.id)
        ).group_by(Claim.claim_type).all()
        
        # Fraud statistics
        fraud_stats = {
            'high_risk': Claim.query.filter(Claim.fraud_score >= 75).count(),
            'medium_risk': Claim.query.filter(Claim.fraud_score >= 50, Claim.fraud_score < 75).count(),
            'low_risk': Claim.query.filter(Claim.fraud_score < 50).count(),
            'average_risk_score': db.session.query(db.func.avg(Claim.fraud_score)).scalar() or 0
        }
        
        # Document statistics
        total_documents = Document.query.count()
        documents_by_type = db.session.query(
            Document.document_type, 
            db.func.count(Document.id)
        ).group_by(Document.document_type).all()
        
        stats = {
            'claims': {
                'total': total_claims,
                'by_status': {status: count for status, count in claims_by_status},
                'by_type': {claim_type: count for claim_type, count in claims_by_type}
            },
            'fraud': fraud_stats,
            'documents': {
                'total': total_documents,
                'by_type': {doc_type: count for doc_type, count in documents_by_type}
            }
        }
        
        return jsonify(stats)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching system stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/ai/models/status', methods=['GET'])
def get_ai_models_status():
    """API endpoint to get AI models status"""
    try:
        if current_user.role != 'admin':
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        # This would check the status of all AI models
        # For now, we'll return a mock response
        models_status = {
            'document_verification': {
                'status': 'active',
                'version': '1.0.0',
                'last_trained': '2024-01-15T10:30:00Z'
            },
            'behavioral_analysis': {
                'status': 'active', 
                'version': '1.0.0',
                'last_trained': '2024-01-15T10:30:00Z'
            },
            'hidden_link_analysis': {
                'status': 'active',
                'version': '1.0.0',
                'last_trained': '2024-01-15T10:30:00Z'
            },
            'predictive_scoring': {
                'status': 'active',
                'version': '1.0.0',
                'last_trained': '2024-01-15T10:30:00Z'
            }
        }
        
        return jsonify(models_status)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching AI models status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """API endpoint for health check"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check if models are loaded (simplified)
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'ai_models': 'loaded',
            'version': '1.0.0'
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'disconnected',
            'error': str(e)
        }), 500
