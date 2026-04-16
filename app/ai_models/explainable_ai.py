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
            feature_weights (dict): Feature importance weights (can be empty)
            
        Returns:
            dict: Explanation results
        """
        try:
            # If no feature weights provided, generate default weights based on analysis results
            if not feature_weights or len(feature_weights) == 0:
                feature_weights = self._generate_default_feature_weights(claim_data)
            
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
            # Return a basic explanation even if there's an error
            return {
                "prediction_score": prediction_score,
                "error": str(e),
                "risk_factors": self._identify_risk_factors(claim_data, {}),
                "summary": self._generate_summary(prediction_score, self._identify_risk_factors(claim_data, {}))
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
    
    def _generate_default_feature_weights(self, claim_data):
        """
        Generate default feature weights based on available data
        
        Args:
            claim_data (dict): Claim data
            
        Returns:
            dict: Default feature importance weights
        """
        weights = {}
        
        # Assign weights based on what data is available
        if 'document_verification_score' in claim_data:
            weights['document_verification_score'] = 0.25
        
        if 'behavioral_anomaly_score' in claim_data:
            weights['behavioral_anomaly_score'] = 0.20
        
        if 'hidden_link_score' in claim_data:
            weights['hidden_link_score'] = 0.20
        
        if 'claim_amount' in claim_data:
            weights['claim_amount'] = 0.15
        
        if 'number_of_previous_claims' in claim_data:
            weights['number_of_previous_claims'] = 0.10
        
        if 'age_of_policy' in claim_data:
            weights['age_of_policy'] = 0.10
        
        return weights
    
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
        # Handle None values
        if value is None:
            return None
        
        explanations = {
            'claim_amount': {
                'high': lambda v: f"High claim amount (₹{v:,.2f}) significantly increases fraud risk",
                'medium': lambda v: f"Moderate claim amount (₹{v:,.2f}) contributes to risk",
                'low': lambda v: f"Low claim amount (₹{v:,.2f}) reduces fraud risk"
            },
            'document_verification_score': {
                'high': lambda v: f"Document verification issues (score: {v:.1f}/100) increase risk",
                'medium': lambda v: f"Some document concerns (score: {v:.1f}/100)",
                'low': lambda v: f"Good document authenticity (score: {v:.1f}/100)"
            },
            'behavioral_anomaly_score': {
                'high': lambda v: f"Behavioral analysis shows high risk patterns (score: {v:.1f}/100)",
                'medium': lambda v: f"Some behavioral anomalies detected (score: {v:.1f}/100)",
                'low': lambda v: f"Normal behavioral patterns (score: {v:.1f}/100)"
            },
            'hidden_link_score': {
                'high': lambda v: f"Suspicious network connections detected (score: {v:.1f}/100)",
                'medium': lambda v: f"Some network connections noted (score: {v:.1f}/100)",
                'low': lambda v: f"No suspicious connections (score: {v:.1f}/100)"
            },
            'number_of_previous_claims': {
                'high': lambda v: f"High number of previous claims ({int(v)}) suggests potential abuse",
                'medium': lambda v: f"Elevated claim frequency ({int(v)} previous claims)",
                'low': lambda v: f"Normal claim history ({int(v)} previous claims)"
            },
            'age_of_policy': {
                'high': lambda v: f"Very new policy ({int(v)} days old) is suspicious",
                'medium': lambda v: f"Recent policy ({int(v)} days old)",
                'low': lambda v: f"Established policy ({int(v)} days old)"
            }
        }
        
        if feature not in explanations:
            # Generic explanation for unknown features
            return {
                'feature': feature,
                'value': value,
                'importance': weight,
                'explanation': f"{feature.replace('_', ' ').title()}: {value}",
                'risk_level': 'medium' if weight > 0.15 else 'low'
            }
        
        # Determine risk level based on value and weight
        try:
            # Convert value to float for comparison
            numeric_value = float(value) if not isinstance(value, (int, float)) else value
            
            # Determine risk level based on feature type and value
            if feature == 'claim_amount':
                if numeric_value > 500000:
                    risk_level = 'high'
                elif numeric_value > 100000:
                    risk_level = 'medium'
                else:
                    risk_level = 'low'
            elif feature in ['document_verification_score']:
                if numeric_value < 60:
                    risk_level = 'high'
                elif numeric_value < 80:
                    risk_level = 'medium'
                else:
                    risk_level = 'low'
            elif feature in ['behavioral_anomaly_score', 'hidden_link_score']:
                if numeric_value > 70:
                    risk_level = 'high'
                elif numeric_value > 50:
                    risk_level = 'medium'
                else:
                    risk_level = 'low'
            elif feature == 'number_of_previous_claims':
                if numeric_value > 5:
                    risk_level = 'high'
                elif numeric_value > 2:
                    risk_level = 'medium'
                else:
                    risk_level = 'low'
            elif feature == 'age_of_policy':
                if numeric_value < 30:
                    risk_level = 'high'
                elif numeric_value < 90:
                    risk_level = 'medium'
                else:
                    risk_level = 'low'
            else:
                risk_level = 'medium' if weight > 0.15 else 'low'
            
            if risk_level in explanations[feature]:
                return {
                    'feature': feature,
                    'value': value,
                    'importance': weight,
                    'explanation': explanations[feature][risk_level](numeric_value),
                    'risk_level': risk_level
                }
        except (ValueError, TypeError):
            pass
        
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
        claim_amount = claim_data.get('claim_amount', 0)
        if claim_amount > 1000000:
            risk_factors.append({
                'factor': 'extremely_high_amount',
                'description': f'Claim amount over ₹10,00,000 (₹{claim_amount:,.0f})',
                'severity': 'high'
            })
        elif claim_amount > 500000:
            risk_factors.append({
                'factor': 'high_amount',
                'description': f'Claim amount over ₹5,00,000 (₹{claim_amount:,.0f})',
                'severity': 'medium'
            })
        
        # Check document verification risks
        doc_score = claim_data.get('document_verification_score', 100)
        if doc_score < 60:
            risk_factors.append({
                'factor': 'poor_document_quality',
                'description': f'Document verification score below 60 ({doc_score:.1f}/100)',
                'severity': 'high'
            })
        elif doc_score < 80:
            risk_factors.append({
                'factor': 'moderate_document_concerns',
                'description': f'Document verification score below 80 ({doc_score:.1f}/100)',
                'severity': 'medium'
            })
        
        # Check behavioral risks
        behavioral_score = claim_data.get('behavioral_anomaly_score', 50)
        if behavioral_score > 75:
            risk_factors.append({
                'factor': 'suspicious_behavior',
                'description': f'Behavioral analysis indicates high risk ({behavioral_score:.1f}/100)',
                'severity': 'high'
            })
        elif behavioral_score > 60:
            risk_factors.append({
                'factor': 'elevated_behavioral_risk',
                'description': f'Behavioral analysis shows some concerns ({behavioral_score:.1f}/100)',
                'severity': 'medium'
            })
        
        # Check connection risks
        connection_score = claim_data.get('hidden_link_score', 50)
        if connection_score > 70:
            risk_factors.append({
                'factor': 'suspicious_connections',
                'description': f'Network analysis shows risky connections ({connection_score:.1f}/100)',
                'severity': 'high'
            })
        elif connection_score > 55:
            risk_factors.append({
                'factor': 'network_concerns',
                'description': f'Some network connections detected ({connection_score:.1f}/100)',
                'severity': 'medium'
            })
        
        # Check claim frequency
        num_claims = claim_data.get('number_of_previous_claims', 0)
        if num_claims > 5:
            risk_factors.append({
                'factor': 'very_high_frequency',
                'description': f'More than 5 previous claims ({num_claims} claims)',
                'severity': 'high'
            })
        elif num_claims > 3:
            risk_factors.append({
                'factor': 'elevated_frequency',
                'description': f'Multiple previous claims ({num_claims} claims)',
                'severity': 'medium'
            })
        
        # Check policy age
        policy_age = claim_data.get('age_of_policy', 365)
        if policy_age < 30:
            risk_factors.append({
                'factor': 'very_new_policy',
                'description': f'Policy is very new ({policy_age} days old)',
                'severity': 'high'
            })
        elif policy_age < 90:
            risk_factors.append({
                'factor': 'new_policy',
                'description': f'Policy is relatively new ({policy_age} days old)',
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
