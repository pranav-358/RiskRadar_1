# CRITICAL: Set matplotlib backend BEFORE importing pyplot
import os
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib
matplotlib.use('Agg', force=True)

import numpy as np
import pandas as pd
import logging
import joblib
from sklearn.inspection import permutation_importance
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExplainableAI:
    def __init__(self):
        self.feature_importance = {}
        self.model_path = os.path.join(os.path.dirname(__file__), '../../models/explainability_model.joblib')
        logger.info("Explainable AI initialized")
    
    def explain_prediction(self, claim_data, prediction_score, feature_weights):
        """
        Generate explanation for a prediction
        
        Args:
            claim_data (dict): Claim data
            prediction_score (float): Prediction score (0-100)
            feature_weights (dict): Feature importance weights
            
        Returns:
            dict: Explanation results
        """
        try:
            # Generate feature-based explanation
            feature_explanation = self._explain_by_features(claim_data, feature_weights)
            
            # Generate rule-based explanation
            rule_explanation = self._explain_by_rules(claim_data)
            
            # Generate risk factors
            risk_factors = self._identify_risk_factors(claim_data, feature_weights)
            
            # Generate visual explanation
            visual_explanation = self._generate_visual_explanation(feature_weights)
            
            return {
                "prediction_score": prediction_score,
                "feature_explanation": feature_explanation,
                "rule_explanation": rule_explanation,
                "risk_factors": risk_factors,
                "visual_explanation": visual_explanation,
                "summary": self._generate_summary(prediction_score, risk_factors)
            }
            
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            return {
                "prediction_score": prediction_score,
                "error": str(e),
                "summary": "Unable to generate detailed explanation due to technical error"
            }
    
    def _explain_by_features(self, claim_data, feature_weights):
        """
        Explain prediction based on feature importance
        
        Args:
            claim_data (dict): Claim data
            feature_weights (dict): Feature importance weights
            
        Returns:
            list: Feature-based explanations
        """
        explanations = []
        
        # Sort features by importance
        sorted_features = sorted(feature_weights.items(), key=lambda x: x[1], reverse=True)
        
        for feature, weight in sorted_features[:5]:  # Top 5 features
            if feature in claim_data:
                value = claim_data[feature]
                explanation = self._get_feature_explanation(feature, value, weight)
                if explanation:
                    explanations.append(explanation)
        
        return explanations
    
    def _get_feature_explanation(self, feature, value, weight):
        """
        Get explanation for a specific feature
        
        Args:
            feature (str): Feature name
            value: Feature value
            weight (float): Feature importance weight
            
        Returns:
            dict: Feature explanation
        """
        explanations = {
            'claim_amount': {
                'high': lambda v: f"High claim amount (₹{v:,.2f}) significantly increases fraud risk",
                'medium': lambda v: f"Moderate claim amount (₹{v:,.2f}) contributes to risk",
                'low': lambda v: f"Low claim amount (₹{v:,.2f}) reduces fraud risk"
            },
            'claim_frequency': {
                'high': lambda v: f"High claim frequency ({v:.2f}/year) suggests potential abuse",
                'medium': lambda v: f"Elevated claim frequency ({v:.2f}/year) noted",
                'low': lambda v: f"Normal claim frequency ({v:.2f}/year)"
            },
            'time_since_last_claim': {
                'high': lambda v: f"Very recent previous claim ({v} days ago) is suspicious",
                'medium': lambda v: f"Recent claim history ({v} days since last claim)",
                'low': lambda v: f"Normal time between claims ({v} days)"
            },
            'document_verification_score': {
                'high': lambda v: f"Document verification issues (score: {v}/100) increase risk",
                'medium': lambda v: f"Some document concerns (score: {v}/100)",
                'low': lambda v: f"Good document authenticity (score: {v}/100)"
            }
        }
        
        if feature not in explanations:
            return None
        
        # Determine risk level based on value and weight
        if weight > 0.2:  # High importance
            risk_level = 'high'
        elif weight > 0.1:  # Medium importance
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        if risk_level in explanations[feature]:
            return {
                'feature': feature,
                'value': value,
                'importance': weight,
                'explanation': explanations[feature][risk_level](value),
                'risk_level': risk_level
            }
        
        return None
    
    def _explain_by_rules(self, claim_data):
        """
        Explain prediction based on business rules
        
        Args:
            claim_data (dict): Claim data
            
        Returns:
            list: Rule-based explanations
        """
        rules = [
            {
                'condition': lambda x: x.get('claim_amount', 0) > 500000,
                'explanation': "Claim amount exceeds ₹500,000 threshold",
                'risk': 'high'
            },
            {
                'condition': lambda x: x.get('claim_frequency', 0) > 3,
                'explanation': "Claim frequency exceeds 3 claims per year",
                'risk': 'medium'
            },
            {
                'condition': lambda x: x.get('time_since_last_claim', 365) < 30,
                'explanation': "Previous claim was within last 30 days",
                'risk': 'medium'
            },
            {
                'condition': lambda x: x.get('document_verification_score', 100) < 70,
                'explanation': "Document verification score below 70/100",
                'risk': 'high'
            },
            {
                'condition': lambda x: x.get('behavioral_risk_score', 50) > 70,
                'explanation': "Behavioral analysis shows high risk patterns",
                'risk': 'high'
            }
        ]
        
        triggered_rules = []
        for rule in rules:
            if rule['condition'](claim_data):
                triggered_rules.append({
                    'explanation': rule['explanation'],
                    'risk_level': rule['risk']
                })
        
        return triggered_rules
    
    def _identify_risk_factors(self, claim_data, feature_weights):
        """
        Identify specific risk factors in the claim
        
        Args:
            claim_data (dict): Claim data
            feature_weights (dict): Feature importance weights
            
        Returns:
            list: Risk factors
        """
        risk_factors = []
        
        # Check amount-based risks
        if claim_data.get('claim_amount', 0) > 1000000:
            risk_factors.append({
                'factor': 'extremely_high_amount',
                'description': 'Claim amount over ₹1,000,000',
                'severity': 'high'
            })
        
        # Check frequency risks
        if claim_data.get('claim_frequency', 0) > 5:
            risk_factors.append({
                'factor': 'very_high_frequency',
                'description': 'More than 5 claims per year',
                'severity': 'high'
            })
        
        # Check document risks
        if claim_data.get('document_verification_score', 100) < 60:
            risk_factors.append({
                'factor': 'poor_document_quality',
                'description': 'Document verification score below 60',
                'severity': 'high'
            })
        
        # Check behavioral risks
        if claim_data.get('behavioral_risk_score', 50) > 75:
            risk_factors.append({
                'factor': 'suspicious_behavior',
                'description': 'Behavioral analysis indicates high risk',
                'severity': 'medium'
            })
        
        # Check connection risks
        if claim_data.get('connection_risk_score', 50) > 70:
            risk_factors.append({
                'factor': 'suspicious_connections',
                'description': 'Network analysis shows risky connections',
                'severity': 'medium'
            })
        
        return risk_factors
    
    def _generate_visual_explanation(self, feature_weights):
        """
        Generate visual explanation of feature importance
        
        Args:
            feature_weights (dict): Feature importance weights
            
        Returns:
            dict: Base64 encoded image and description
        """
        try:
            # Create feature importance plot
            plt.figure(figsize=(10, 6))
            features = list(feature_weights.keys())[:10]  # Top 10 features
            importance = list(feature_weights.values())[:10]
            
            colors = ['red' if imp > 0.15 else 'orange' if imp > 0.1 else 'blue' for imp in importance]
            
            plt.barh(features, importance, color=colors)
            plt.xlabel('Importance')
            plt.title('Top Feature Importance for Fraud Prediction')
            plt.gca().invert_yaxis()
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            
            # Convert to base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return {
                'type': 'feature_importance_chart',
                'data': f"data:image/png;base64,{image_base64}",
                'description': "Visualization of the most important factors influencing this fraud prediction"
            }
            
        except Exception as e:
            logger.error(f"Error generating visual explanation: {str(e)}")
            return {
                'type': 'error',
                'description': f"Could not generate visual explanation: {str(e)}"
            }
    
    def _generate_summary(self, prediction_score, risk_factors):
        """
        Generate human-readable summary explanation
        
        Args:
            prediction_score (float): Prediction score (0-100)
            risk_factors (list): Identified risk factors
            
        Returns:
            str: Summary explanation
        """
        if prediction_score >= 80:
            severity = "high"
            base_text = "This claim shows strong indicators of potential fraud."
        elif prediction_score >= 60:
            severity = "moderate"
            base_text = "This claim displays several characteristics that raise fraud concerns."
        elif prediction_score >= 40:
            severity = "low"
            base_text = "This claim has some minor indicators that warrant attention."
        else:
            severity = "very_low"
            base_text = "This claim appears to be legitimate based on current analysis."
        
        # Add risk factor details
        if risk_factors:
            high_risk_factors = [rf for rf in risk_factors if rf['severity'] == 'high']
            medium_risk_factors = [rf for rf in risk_factors if rf['severity'] == 'medium']
            
            if high_risk_factors:
                base_text += f" Key risk factors include: {', '.join([rf['description'] for rf in high_risk_factors])}."
            elif medium_risk_factors:
                base_text += f" Notable factors include: {', '.join([rf['description'] for rf in medium_risk_factors])}."
        
        # Add recommendation
        if severity == "high":
            base_text += " Immediate investigation is recommended."
        elif severity == "moderate":
            base_text += " Further review is advised."
        elif severity == "low":
            base_text += " Monitoring is suggested."
        else:
            base_text += " Standard processing can continue."
        
        return base_text
    
    def save_explanation_model(self):
        """Save the explanation model"""
        try:
            joblib.dump(self.feature_importance, self.model_path)
            logger.info("Explanation model saved")
        except Exception as e:
            logger.error(f"Error saving explanation model: {str(e)}")
    
    def load_explanation_model(self):
        """Load explanation model"""
        try:
            if os.path.exists(self.model_path):
                self.feature_importance = joblib.load(self.model_path)
                logger.info("Explanation model loaded")
        except Exception as e:
            logger.error(f"Error loading explanation model: {str(e)}")

# Singleton instance
explainable_ai = ExplainableAI()
