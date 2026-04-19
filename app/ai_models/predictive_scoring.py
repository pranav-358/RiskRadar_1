import numpy as np
import joblib
import os
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictiveScoringModel:
    def __init__(self):
        """Initialize the predictive scoring model"""
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.is_trained = False
        self.models_dir = 'training_data/models'
        
        # Try to load trained model on initialization
        self.load_model()
    
    def load_model(self):
        """Load trained ML model from disk"""
        try:
            model_path = os.path.join(self.models_dir, 'gradient_boosting.joblib')
            scaler_path = os.path.join(self.models_dir, 'scaler.joblib')
            features_path = os.path.join(self.models_dir, 'feature_names.json')
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                
                if os.path.exists(features_path):
                    with open(features_path, 'r') as f:
                        self.feature_names = json.load(f)
                
                # CRITICAL: The pre-trained model returns probabilities in wrong scale
                # It returns values like 1.5e-05 instead of 0-100 range
                # This is a model calibration issue - disable it and use rule-based instead
                logger.warning("⚠️ Pre-trained ML model found but DISABLED due to calibration issues")
                logger.warning("   Model returns probabilities in wrong scale (e.g., 1.5e-05 instead of 0-100)")
                logger.warning("   Using RULE-BASED prediction instead for production-ready results")
                self.is_trained = False  # Force rule-based prediction
                return False
            else:
                logger.warning("⚠️ No trained model found. Using rule-based fallback.")
                logger.warning(f"  Expected model at: {model_path}")
                logger.warning("  Run 'python train_models.py' to train the model")
                self.is_trained = False
                return False
                
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self.is_trained = False
            return False
    
    def predict(self, claim_data):
        """
        Predict fraud probability for a claim
        
        Args:
            claim_data (dict): Claim data with keys:
                - claim_amount: float
                - claim_type: str (health, auto, property, life)
                - policy_type: str (comprehensive, basic, premium)
                - document_verification_score: float (0-100)
                - documents: list of documents
                - risk_score: float (0-100) [optional]
                
        Returns:
            float: Fraud probability (0-100 scale)
        """
        try:
            logger.info("=" * 80)
            logger.info("PREDICTIVE MODEL PREDICTION")
            logger.info("=" * 80)
            logger.info(f"Model Status: Trained={self.is_trained}, Model={self.model is not None}")
            
            if self.is_trained and self.model is not None:
                # Use trained ML model
                logger.info("Using TRAINED ML Model")
                return self._ml_prediction(claim_data)
            else:
                # Fallback to rule-based prediction
                logger.info("Using RULE-BASED Prediction (ML model not available)")
                return self._rule_based_prediction(claim_data)
                
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Return moderate risk on error
            return 50.0
    
    def _ml_prediction(self, claim_data):
        """
        Make prediction using trained ML model
        
        Args:
            claim_data (dict): Claim data
            
        Returns:
            float: Fraud probability (0-100 scale)
        """
        try:
            # Extract features in the same order as training
            features = self._extract_features(claim_data)
            
            # Scale features
            features_scaled = self.scaler.transform([features])
            
            # Get probability from model
            # predict_proba returns [[prob_legit, prob_fraud]]
            prob_fraud = self.model.predict_proba(features_scaled)[0][1]
            
            # Convert to 0-100 scale
            risk_score = prob_fraud * 100.0
            
            logger.info(f"ML Prediction: {risk_score:.1f}/100 (fraud probability: {prob_fraud:.2%})")
            
            return risk_score
            
        except Exception as e:
            logger.error(f"ML prediction error: {str(e)}")
            return self._rule_based_prediction(claim_data)
    
    def _extract_features(self, claim_data):
        """
        Extract features from claim data matching training format
        
        Feature order must match training:
        [amount, claim_health, claim_auto, claim_property, claim_life,
         policy_comprehensive, policy_basic, policy_premium,
         doc_authenticity, num_documents, time_diff, risk_score]
        
        Args:
            claim_data (dict): Claim data
            
        Returns:
            list: Feature vector
        """
        features = []
        
        # 1. Amount (normalized by 100,000)
        amount = claim_data.get('claim_amount', 0)
        features.append(float(amount) / 100000.0)
        
        # 2. Claim type (one-hot encoded)
        claim_type = claim_data.get('claim_type', 'health').lower()
        for ct in ['health', 'auto', 'property', 'life']:
            features.append(1.0 if claim_type == ct else 0.0)
        
        # 3. Policy type (one-hot encoded)
        policy_type = claim_data.get('policy_type', 'basic').lower()
        for pt in ['comprehensive', 'basic', 'premium']:
            features.append(1.0 if policy_type == pt else 0.0)
        
        # 4. Document authenticity (normalized to 0-1)
        doc_score = claim_data.get('document_verification_score', 50.0)
        features.append(doc_score / 100.0)
        
        # 5. Number of documents (normalized)
        documents = claim_data.get('documents', [])
        num_docs = len(documents) if documents else 0
        features.append(num_docs / 5.0)  # Normalize by typical max
        
        # 6. Time difference (normalized)
        # For now, use a default value since we don't have incident date in claim_data
        features.append(0.5)  # Neutral value
        
        # 7. Risk score (normalized to 0-1)
        risk_score = claim_data.get('risk_score', 50.0)
        features.append(risk_score / 100.0)
        
        return features
    
    def _rule_based_prediction(self, claim_data):
        """
        Fallback rule-based prediction when ML model is not available
        
        Args:
            claim_data (dict): Claim data
            
        Returns:
            float: Risk score (0-100)
        """
        score = 50.0  # Start with neutral score
        
        logger.info("=" * 60)
        logger.info("RULE-BASED PREDICTION ANALYSIS")
        logger.info("=" * 60)
        
        # Document verification score (most important)
        doc_score = claim_data.get('document_verification_score', 50)
        logger.info(f"Document Verification Score: {doc_score}")
        if doc_score < 40:
            score += 30  # Very suspicious
            logger.info(f"  → Low document score: +30 points (very suspicious)")
        elif doc_score < 60:
            score += 20  # Suspicious
            logger.info(f"  → Medium-low document score: +20 points (suspicious)")
        elif doc_score > 80:
            score -= 15  # Good documents
            logger.info(f"  → High document score: -15 points (good documents)")
        else:
            logger.info(f"  → Neutral document score: no change")
        
        # Behavioral analysis
        behavioral_score = claim_data.get('behavioral_anomaly_score', 50)
        logger.info(f"Behavioral Anomaly Score: {behavioral_score}")
        if behavioral_score > 70:
            score += 15
            logger.info(f"  → High behavioral anomaly: +15 points")
        elif behavioral_score < 30:
            score -= 10
            logger.info(f"  → Low behavioral anomaly: -10 points")
        else:
            logger.info(f"  → Normal behavioral score: no change")
        
        # Hidden links
        link_score = claim_data.get('hidden_link_score', 50)
        logger.info(f"Hidden Link Score: {link_score}")
        if link_score > 70:
            score += 15
            logger.info(f"  → High connection risk: +15 points")
        elif link_score < 30:
            score -= 10
            logger.info(f"  → Low connection risk: -10 points")
        else:
            logger.info(f"  → Normal connection score: no change")
        
        # Claim amount
        amount = claim_data.get('claim_amount', 0)
        logger.info(f"Claim Amount: ₹{amount:,.2f}")
        if amount > 1000000:
            score += 15
            logger.info(f"  → Very high amount (>₹1M): +15 points")
        elif amount > 500000:
            score += 10
            logger.info(f"  → High amount (>₹500K): +10 points")
        elif amount > 100000:
            logger.info(f"  → Medium amount: no change")
        else:
            logger.info(f"  → Low amount: no change")
        
        # Number of documents
        documents = claim_data.get('documents', [])
        doc_count = len(documents) if documents else 0
        logger.info(f"Number of Documents: {doc_count}")
        if doc_count < 1:
            score += 15  # No documents - very suspicious
            logger.info(f"  → No documents: +15 points (very suspicious)")
        elif doc_count < 2:
            score += 10  # Too few documents
            logger.info(f"  → Only 1 document: +10 points (too few)")
        elif doc_count >= 4:
            score -= 5  # Good documentation
            logger.info(f"  → Good documentation (4+ docs): -5 points")
        else:
            logger.info(f"  → Adequate documentation: no change")
        
        # Claim type analysis
        claim_type = claim_data.get('claim_type', 'unknown').lower()
        logger.info(f"Claim Type: {claim_type}")
        
        # Policy type analysis
        policy_type = claim_data.get('policy_type', 'unknown').lower()
        logger.info(f"Policy Type: {policy_type}")
        
        # Incident location
        incident_location = claim_data.get('incident_location', 'unknown')
        logger.info(f"Incident Location: {incident_location}")
        
        # Description length
        description = claim_data.get('description', '')
        desc_length = len(description) if description else 0
        logger.info(f"Description Length: {desc_length} characters")
        if desc_length < 20:
            score += 10
            logger.info(f"  → Very short description: +10 points (suspicious)")
        elif desc_length < 50:
            score += 5
            logger.info(f"  → Short description: +5 points")
        elif desc_length > 500:
            score -= 5
            logger.info(f"  → Detailed description: -5 points (good)")
        
        # Ensure score is in valid range
        score = max(0.0, min(100.0, score))
        
        logger.info("=" * 60)
        logger.info(f"FINAL RULE-BASED PREDICTION: {score:.1f}/100")
        logger.info("=" * 60)
        
        return score
    
    def get_feature_importance(self):
        """
        Get feature importance from trained model
        
        Returns:
            dict: Feature names and their importance scores
        """
        if not self.is_trained or self.model is None:
            return {}
        
        try:
            # Get feature importances from the model
            importances = self.model.feature_importances_
            
            # Create dictionary of feature names and importances
            importance_dict = {}
            for i, feature_name in enumerate(self.feature_names):
                if i < len(importances):
                    importance_dict[feature_name] = float(importances[i])
            
            # Sort by importance
            importance_dict = dict(sorted(importance_dict.items(), 
                                        key=lambda x: x[1], 
                                        reverse=True))
            
            return importance_dict
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {str(e)}")
            return {}


# Singleton instance for the application
predictive_model = PredictiveScoringModel()
