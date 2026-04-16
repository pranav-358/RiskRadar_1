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
                
                self.is_trained = True
                logger.info("✓ Trained ML model loaded successfully")
                logger.info(f"  Model: Gradient Boosting Classifier")
                logger.info(f"  Features: {len(self.feature_names)}")
                return True
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
            if self.is_trained and self.model is not None:
                # Use trained ML model
                return self._ml_prediction(claim_data)
            else:
                # Fallback to rule-based prediction
                logger.warning("Using rule-based prediction (model not trained)")
                return self._rule_based_prediction(claim_data)
                
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
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
        
        # Document verification score (most important)
        doc_score = claim_data.get('document_verification_score', 50)
        if doc_score < 40:
            score += 30  # Very suspicious
        elif doc_score < 60:
            score += 20  # Suspicious
        elif doc_score > 80:
            score -= 15  # Good documents
        
        # Behavioral analysis
        behavioral_score = claim_data.get('behavioral_anomaly_score', 50)
        if behavioral_score > 70:
            score += 15
        elif behavioral_score < 30:
            score -= 10
        
        # Hidden links
        link_score = claim_data.get('hidden_link_score', 50)
        if link_score > 70:
            score += 15
        elif link_score < 30:
            score -= 10
        
        # Claim amount
        amount = claim_data.get('claim_amount', 0)
        if amount > 500000:
            score += 10
        elif amount > 1000000:
            score += 15
        
        # Number of documents
        documents = claim_data.get('documents', [])
        if len(documents) < 2:
            score += 10  # Too few documents
        elif len(documents) >= 4:
            score -= 5  # Good documentation
        
        # Ensure score is in valid range
        score = max(0.0, min(100.0, score))
        
        logger.info(f"Rule-based prediction: {score:.1f}/100")
        
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
