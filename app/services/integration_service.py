import logging
from datetime import datetime
import numpy as np
import json
from app.ai_models import (
    document_verifier,
    behavioral_ai,
    hidden_link_ai,
    predictive_model,
    explainable_ai,
    ocr_processor
)
from app import db
from app.models import Claim, Document, AnalysisResult


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrationService:
    def __init__(self):
        self.ai_modules = {
            'document_verification': document_verifier,
            'behavioral_analysis': behavioral_ai,
            'hidden_link_analysis': hidden_link_ai,
            'predictive_scoring': predictive_model,
            'explainable_ai': explainable_ai
        }
        logger.info("Integration Service initialized")
        self._log_model_status()
    
    def _log_model_status(self):
        """Log the status of all AI models"""
        logger.info("=" * 80)
        logger.info("AI MODELS STATUS CHECK")
        logger.info("=" * 80)
        
        # Check predictive model
        logger.info(f"Predictive Model:")
        logger.info(f"  - Is Trained: {predictive_model.is_trained}")
        logger.info(f"  - Model Loaded: {predictive_model.model is not None}")
        logger.info(f"  - Scaler Loaded: {predictive_model.scaler is not None}")
        logger.info(f"  - Feature Names: {len(predictive_model.feature_names)}")
        
        # Check behavioral AI
        logger.info(f"Behavioral AI:")
        logger.info(f"  - Models Initialized: {len(behavioral_ai.models) > 0}")
        logger.info(f"  - Preprocessor: {behavioral_ai.preprocessor is not None}")
        
        # Check hidden link AI
        logger.info(f"Hidden Link AI:")
        logger.info(f"  - Graph Nodes: {len(hidden_link_ai.graph.nodes)}")
        logger.info(f"  - Graph Edges: {len(hidden_link_ai.graph.edges)}")
        logger.info(f"  - Known Fraudulent Entities: {len(hidden_link_ai.known_fraudulent_entities)}")
        
        # Check document verifier
        logger.info(f"Document Verifier:")
        logger.info(f"  - Fraud Patterns Loaded: {len(document_verifier.fraud_patterns) > 0}")
        
        # Check OCR processor
        logger.info(f"OCR Processor:")
        logger.info(f"  - EasyOCR Reader: {ocr_processor.reader is not None}")
        logger.info(f"  - Tesseract Available: {ocr_processor.tesseract_available}")
        
        logger.info("=" * 80)
    
    def process_claim(self, claim_id):
        """
        Process a claim through all AI modules
        
        Args:
            claim_id (str): ID of the claim to process
            
        Returns:
            dict: Comprehensive analysis results
        """
        try:
            logger.info("=" * 80)
            logger.info(f"PROCESSING CLAIM {claim_id}")
            logger.info("=" * 80)
            
            # Retrieve claim from database
            claim = Claim.query.get(claim_id)
            if not claim:
                raise ValueError(f"Claim {claim_id} not found")
            
            logger.info(f"Claim Details:")
            logger.info(f"  - User ID: {claim.user_id}")
            logger.info(f"  - Amount: ₹{claim.amount:,.2f}")
            logger.info(f"  - Type: {claim.claim_type}")
            logger.info(f"  - Policy Type: {claim.policy_type}")
            
            # Retrieve claim documents
            documents = Document.query.filter_by(claim_id=claim_id).all()
            logger.info(f"  - Documents: {len(documents)}")
            
            # Prepare claim data for processing
            claim_data = self._prepare_claim_data(claim, documents)
            
            # Process through each AI module
            results = {}
            
            # 1. Document Verification
            logger.info("\n[1/5] Running Document Verification...")
            doc_results = self._process_documents(documents, claim_data)
            results['document_verification'] = doc_results
            logger.info(f"  ✓ Document Authenticity Score: {doc_results['overall_authenticity_score']:.1f}/100")
            
            # 2. Behavioral Analysis
            logger.info("\n[2/5] Running Behavioral Analysis...")
            user_history = self._get_user_claim_history(claim.user_id, claim_id)
            logger.info(f"  - User History: {len(user_history)} previous claims")
            behavioral_results = behavioral_ai.analyze_behavior(claim_data, user_history)
            results['behavioral_analysis'] = behavioral_results
            logger.info(f"  ✓ Behavioral Risk Score: {behavioral_results['behavioral_risk_score']:.1f}/100")
            
            # 3. Hidden Link Analysis
            logger.info("\n[3/5] Running Hidden Link Analysis...")
            existing_claims = self._get_all_claims_for_network_analysis()
            logger.info(f"  - Existing Claims in Network: {len(existing_claims)}")
            connection_results = hidden_link_ai.analyze_connections(claim_data, existing_claims)
            results['hidden_link_analysis'] = connection_results
            logger.info(f"  ✓ Connection Risk Score: {connection_results['connection_risk_score']:.1f}/100")
            
            # 4. Predictive Scoring (integrate all previous results)
            logger.info("\n[4/5] Running Predictive Scoring...")
            predictive_data = self._prepare_predictive_data(claim_data, results)
            logger.info(f"  - Predictive Data Keys: {list(predictive_data.keys())}")
            fraud_probability = predictive_model.predict(predictive_data)
            results['predictive_scoring'] = {
                'fraud_probability': fraud_probability,
                'risk_category': self._categorize_risk(fraud_probability)
            }
            logger.info(f"  ✓ Fraud Probability: {fraud_probability:.1f}/100")
            logger.info(f"  ✓ Risk Category: {results['predictive_scoring']['risk_category']}")
            
            # 5. Explainable AI
            logger.info("\n[5/5] Running Explainable AI...")
            explanation = explainable_ai.explain_prediction(
                predictive_data, 
                fraud_probability,
                predictive_model.get_feature_importance()
            )
            results['explainable_ai'] = explanation
            logger.info(f"  ✓ Explanation Generated")
            
            # Save results to database
            self._save_analysis_results(claim_id, results)
            
            # Update claim status
            claim.status = 'analyzed'
            claim.analysis_date = datetime.utcnow()
            claim.fraud_score = fraud_probability
            db.session.commit()
            
            logger.info("\n" + "=" * 80)
            logger.info(f"CLAIM {claim_id} ANALYSIS COMPLETE")
            logger.info(f"Final Risk Score: {fraud_probability:.1f}/100")
            logger.info("=" * 80)
            
            return {
                'success': True,
                'claim_id': claim_id,
                'results': results,
                'overall_risk_score': fraud_probability
            }
            
        except Exception as e:
            logger.error(f"Error processing claim {claim_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'claim_id': claim_id
            }
    
    def _prepare_claim_data(self, claim, documents):
        """
        Prepare claim data for AI processing
        
        Args:
            claim: Claim object
            documents: List of Document objects
            
        Returns:
            dict: Processed claim data
        """
        claim_data = {
            'claim_id': claim.id,
            'user_id': claim.user_id,
            'claim_amount': claim.amount,
            'claim_type': claim.claim_type,
            'policy_number': claim.policy_number,
            'incident_date': claim.incident_date.isoformat() if claim.incident_date else None,
            'submission_date': claim.submission_date.isoformat() if claim.submission_date else None,
            'description': claim.description,
            'incident_location': claim.incident_location,
            'policy_type': claim.policy_type,
            'age_of_policy': (claim.submission_date - claim.policy_start_date).days if hasattr(claim, 'policy_start_date') and claim.policy_start_date else 0
        }
        
        # Add claimant information
        claimant = claim.claimant if hasattr(claim, 'claimant') else None
        if claimant:
            claim_data['claimant'] = {
                'name': f"{claimant.first_name or ''} {claimant.last_name or ''}".strip() or claimant.username,
                'email': claimant.email,
                'phone': claimant.phone if hasattr(claimant, 'phone') else None,
                'aadhar_number': claimant.aadhar_number if hasattr(claimant, 'aadhar_number') else None,
                'address': {
                    'street': claimant.address_street if hasattr(claimant, 'address_street') else None,
                    'city': claimant.address_city if hasattr(claimant, 'address_city') else None,
                    'state': claimant.address_state if hasattr(claimant, 'address_state') else None,
                    'zip_code': claimant.address_zip if hasattr(claimant, 'address_zip') else None
                } if hasattr(claimant, 'address_street') and claimant.address_street else None
            }
        else:
            logger.warning(f"No claimant information available for claim {claim.id}")
        
        # Add document information
        claim_data['documents'] = [
            {
                'id': doc.id,
                'type': doc.document_type,
                'path': doc.file_path,
                'original_name': doc.original_filename
            }
            for doc in documents
        ]
        
        return claim_data
    
    def _process_documents(self, documents, claim_data):
        """
        Process all documents through document verification AI
        
        Args:
            documents: List of Document objects
            claim_data: Claim data for consistency checking
            
        Returns:
            dict: Document verification results
        """
        results = {
            'documents': [],
            'overall_authenticity_score': 75.0,  # Default to neutral-good score if no docs
            'any_tampered': False
        }
        
        doc_scores = []
        for doc in documents:
            try:
                doc_result = document_verifier.analyze_document(
                    doc.file_path,
                    doc.document_type,
                    claim_data
                )
                
                # Update document record with analysis results
                doc.authenticity_score = doc_result['authenticity_score']
                doc.is_tampered = doc_result['is_tampered']
                doc.analysis_results = json.dumps(doc_result)
                doc.analysis_date = datetime.utcnow()
                
                results['documents'].append({
                    'document_id': doc.id,
                    'original_name': doc.original_filename,
                    'type': doc.document_type,
                    'results': doc_result
                })
                
                doc_scores.append(doc_result['authenticity_score'])
                if doc_result['is_tampered']:
                    results['any_tampered'] = True
                    
            except Exception as e:
                logger.error(f"Error processing document {doc.id}: {str(e)}")
                results['documents'].append({
                    'document_id': doc.id,
                    'error': str(e)
                })
        
        # Calculate overall document score
        if doc_scores:
            results['overall_authenticity_score'] = sum(doc_scores) / len(doc_scores)
        else:
            # No documents - set to neutral score
            logger.warning("No documents provided for analysis - using default score")
            results['overall_authenticity_score'] = 75.0
        
        return results
    
    def _get_user_claim_history(self, user_id, current_claim_id):
        """
        Get user's previous claim history for behavioral analysis
        
        Args:
            user_id: User ID
            current_claim_id: Current claim ID to exclude
            
        Returns:
            list: User's claim history
        """
        previous_claims = Claim.query.filter(
            Claim.user_id == user_id,
            Claim.id != current_claim_id,
            Claim.status.in_(['submitted', 'analyzed', 'processed'])
        ).order_by(Claim.submission_date.desc()).limit(10).all()
        
        return [
            {
                'claim_id': claim.id,
                'claim_amount': claim.amount,
                'claim_type': claim.claim_type,
                'submission_date': claim.submission_date.isoformat(),
                'status': claim.status,
                'fraud_score': claim.fraud_score
            }
            for claim in previous_claims
        ]
    
    def _get_all_claims_for_network_analysis(self):
        """
        Get all claims for network analysis (limited to recent claims for performance)
        
        Returns:
            list: Recent claims data
        """
        recent_claims = Claim.query.filter(
            Claim.status.in_(['submitted', 'analyzed', 'processed'])
        ).order_by(Claim.submission_date.desc()).limit(1000).all()
        
        return [
            {
                'claim_id': claim.id,
                'user_id': claim.user_id,
                'claim_amount': claim.amount,
                'claim_type': claim.claim_type,
                'submission_date': claim.submission_date.isoformat(),
                'incident_location': claim.incident_location,
                'policy_number': claim.policy_number
            }
            for claim in recent_claims
        ]
    
    def _prepare_predictive_data(self, claim_data, analysis_results):
        """
        Prepare data for predictive scoring by integrating all analysis results
        
        Args:
            claim_data: Original claim data
            analysis_results: Results from all AI modules
            
        Returns:
            dict: Integrated data for predictive model
        """
        predictive_data = claim_data.copy()
        
        # Add document verification results
        doc_results = analysis_results['document_verification']
        predictive_data['document_verification_score'] = doc_results['overall_authenticity_score']
        predictive_data['document_tampered'] = doc_results['any_tampered']
        
        # Add behavioral analysis results
        behavioral_results = analysis_results['behavioral_analysis']
        predictive_data['behavioral_anomaly_score'] = behavioral_results['behavioral_risk_score']
        
        # Add hidden link analysis results
        link_results = analysis_results['hidden_link_analysis']
        predictive_data['hidden_link_score'] = link_results['connection_risk_score']
        
        # Add derived features
        if 'user_history' in predictive_data:
            history = predictive_data['user_history']
            if history:
                predictive_data['number_of_previous_claims'] = len(history)
                predictive_data['avg_previous_claim_amount'] = (
                    sum(claim['claim_amount'] for claim in history) / len(history) 
                    if history else 0
                )
        
        return predictive_data
    
    def _categorize_risk(self, score):
        """
        Categorize risk based on score
        
        Args:
            score (float): Risk score (0-100)
            
        Returns:
            str: Risk category
        """
        if score >= 80:
            return 'very_high'
        elif score >= 65:
            return 'high'
        elif score >= 45:
            return 'medium'
        elif score >= 30:
            return 'low'
        else:
            return 'very_low'
    
    def _save_analysis_results(self, claim_id, results):
        """
        Save analysis results to database
        
        Args:
            claim_id: Claim ID
            results: Analysis results from all modules
        """
        try:
            # Check if analysis result already exists
            analysis = AnalysisResult.query.filter_by(claim_id=claim_id).first()
            if not analysis:
                analysis = AnalysisResult(claim_id=claim_id)
                db.session.add(analysis)
            
            # Update analysis results
            analysis.document_verification_results = json.dumps(results['document_verification'])
            analysis.behavioral_analysis_results = json.dumps(results['behavioral_analysis'])
            analysis.hidden_link_results = json.dumps(results['hidden_link_analysis'])
            analysis.predictive_scoring_results = json.dumps(results['predictive_scoring'])
            analysis.explainable_ai_results = json.dumps(results['explainable_ai'])
            analysis.overall_score = results['predictive_scoring']['fraud_probability']
            analysis.analysis_date = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error saving analysis results for claim {claim_id}: {str(e)}")
            db.session.rollback()
    
    def batch_process_claims(self, claim_ids):
        """
        Process multiple claims in batch
        
        Args:
            claim_ids (list): List of claim IDs to process
            
        Returns:
            dict: Batch processing results
        """
        results = {
            'processed': 0,
            'succeeded': 0,
            'failed': 0,
            'details': []
        }
        
        for claim_id in claim_ids:
            try:
                result = self.process_claim(claim_id)
                if result['success']:
                    results['succeeded'] += 1
                    results['details'].append({
                        'claim_id': claim_id,
                        'status': 'success',
                        'risk_score': result['overall_risk_score']
                    })
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'claim_id': claim_id,
                        'status': 'failed',
                        'error': result['error']
                    })
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'claim_id': claim_id,
                    'status': 'error',
                    'error': str(e)
                })
            
            results['processed'] += 1
        
        return results
    
    def get_analysis_report(self, claim_id):
        """
        Get comprehensive analysis report for a claim
        
        Args:
            claim_id: Claim ID
            
        Returns:
            dict: Analysis report
        """
        analysis = AnalysisResult.query.filter_by(claim_id=claim_id).first()
        if not analysis:
            return None
        
        return {
            'document_verification': json.loads(analysis.document_verification_results),
            'behavioral_analysis': json.loads(analysis.behavioral_analysis_results),
            'hidden_link_analysis': json.loads(analysis.hidden_link_results),
            'predictive_scoring': json.loads(analysis.predictive_scoring_results),
            'explainable_ai': json.loads(analysis.explainable_ai_results),
            'overall_score': analysis.overall_score,
            'analysis_date': analysis.analysis_date.isoformat() if analysis.analysis_date else None
        }

# Singleton instance
integration_service = IntegrationService()
