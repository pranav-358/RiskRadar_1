# Add this import at the very top of the file
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.neighbors import LocalOutlierFactor
import joblib
import logging
from datetime import datetime, timedelta
import json
from collections import defaultdict
import math

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BehavioralAI:
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.preprocessor = None
        self.claim_history = defaultdict(list)
        self.user_profiles = {}
        self.model_path = os.path.join(os.path.dirname(__file__), '../../models/behavioral_model.joblib')
        self.scaler_path = os.path.join(os.path.dirname(__file__), '../../models/behavioral_scaler.joblib')
        
        # Create models directory if it doesn't exist
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # Initialize models
        self._initialize_models()
        logger.info("Behavioral AI initialized")
    
    def _initialize_models(self):
        """Initialize the machine learning models for behavioral analysis"""
        # Isolation Forest for anomaly detection
        self.models['isolation_forest'] = IsolationForest(
            n_estimators=100,
            contamination=0.1,  # Expected proportion of outliers
            random_state=42
        )
        
        # Local Outlier Factor for density-based outlier detection
        self.models['lof'] = LocalOutlierFactor(
            n_neighbors=20,
            contamination=0.1
        )
        
        # DBSCAN for clustering-based anomaly detection
        self.models['dbscan'] = DBSCAN(eps=0.5, min_samples=5)
        
        # Define preprocessing for different feature types
        numeric_features = ['claim_amount', 'age_of_policy', 'time_since_last_claim', 
                          'number_of_previous_claims', 'claim_frequency']
        categorical_features = ['claim_type', 'incident_location', 'policy_type']
        
        numeric_transformer = Pipeline(steps=[
            ('scaler', StandardScaler())
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('onehot', OneHotEncoder(handle_unknown='ignore'))
        ])
        
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, numeric_features),
                ('cat', categorical_transformer, categorical_features)
            ])
    
    def analyze_behavior(self, claim_data, user_history=None):
        """
        Analyze claim behavior for anomalies
        
        Args:
            claim_data (dict): Current claim data
            user_history (list): User's previous claims history
            
        Returns:
            dict: Behavioral analysis results with anomaly scores and findings
        """
        try:
            # Prepare features for analysis
            features = self._prepare_features(claim_data, user_history)
            
            # Calculate multiple anomaly scores
            anomaly_scores = self._calculate_anomaly_scores(features)
            
            # Check for specific behavioral patterns
            pattern_analysis = self._check_behavioral_patterns(claim_data, user_history)
            
            # Calculate overall behavioral risk score
            risk_score = self._calculate_risk_score(anomaly_scores, pattern_analysis)
            
            # Compile findings
            findings = self._compile_findings(anomaly_scores, pattern_analysis, risk_score)
            
            return {
                "behavioral_risk_score": risk_score,
                "anomaly_scores": anomaly_scores,
                "pattern_analysis": pattern_analysis,
                "findings": findings,
                "is_anomalous": risk_score > 70,  # Threshold for behavioral anomaly
                "features_used": features
            }
            
        except Exception as e:
            logger.error(f"Error in behavioral analysis: {str(e)}")
            return {
                "behavioral_risk_score": 50,
                "anomaly_scores": {},
                "pattern_analysis": {},
                "findings": [f"Analysis error: {str(e)}"],
                "is_anomalous": False,
                "error": str(e)
            }
    
    def _prepare_features(self, claim_data, user_history):
        """
        Prepare features for behavioral analysis
        
        Args:
            claim_data (dict): Current claim data
            user_history (list): User's claim history
            
        Returns:
            dict: Processed features for ML models
        """
        features = claim_data.copy()
        
        # Calculate derived features from user history
        if user_history and len(user_history) > 0:
            history_df = pd.DataFrame(user_history)
            
            # Calculate claim frequency (claims per year)
            if 'submission_date' in history_df.columns and 'submission_date' in claim_data:
                try:
                    # Convert to datetime objects
                    history_dates = pd.to_datetime(history_df['submission_date'])
                    current_date = pd.to_datetime(claim_data['submission_date'])
                    
                    # Calculate time span in years
                    if len(history_dates) > 0:
                        first_claim = history_dates.min()
                        time_span_years = (current_date - first_claim).days / 365.25
                        
                        if time_span_years > 0:
                            features['claim_frequency'] = len(history_dates) / time_span_years
                        else:
                            features['claim_frequency'] = len(history_dates)  # All claims in same year
                    else:
                        features['claim_frequency'] = 0
                except:
                    features['claim_frequency'] = len(history_dates)
            
            # Calculate average claim amount
            if 'claim_amount' in history_df.columns:
                features['avg_previous_claim_amount'] = history_df['claim_amount'].mean()
                features['claim_amount_ratio'] = (
                    claim_data['claim_amount'] / features['avg_previous_claim_amount'] 
                    if features['avg_previous_claim_amount'] > 0 else 10  # High ratio if no previous claims
                )
            
            # Calculate time since last claim
            if 'submission_date' in history_df.columns and 'submission_date' in claim_data:
                try:
                    last_claim_date = pd.to_datetime(history_df['submission_date']).max()
                    current_date = pd.to_datetime(claim_data['submission_date'])
                    time_since_last = (current_date - last_claim_date).days
                    features['time_since_last_claim'] = time_since_last
                except:
                    features['time_since_last_claim'] = 0
        else:
            # First claim for this user
            features['claim_frequency'] = 0
            features['time_since_last_claim'] = 0
            features['claim_amount_ratio'] = 10  # High ratio for first claim
        
        # Ensure all required features are present
        default_features = {
            'claim_amount': 0,
            'age_of_policy': 0,
            'number_of_previous_claims': 0,
            'claim_frequency': 0,
            'time_since_last_claim': 365,  # Default to 1 year
            'claim_type': 'unknown',
            'incident_location': 'unknown',
            'policy_type': 'unknown'
        }
        
        for feature, default_value in default_features.items():
            if feature not in features:
                features[feature] = default_value
        
        return features
    
    def _calculate_anomaly_scores(self, features):
        """
        Calculate multiple anomaly scores using different algorithms
        
        Args:
            features (dict): Processed features
            
        Returns:
            dict: Anomaly scores from different models
        """
        try:
            # Convert features to DataFrame for processing
            feature_df = pd.DataFrame([features])
            
            # Select and prepare features for ML
            ml_features = feature_df[['claim_amount', 'age_of_policy', 'time_since_last_claim', 
                                    'number_of_previous_claims', 'claim_frequency', 
                                    'claim_type', 'incident_location', 'policy_type']]
            
            # Preprocess features
            processed_features = self.preprocessor.fit_transform(ml_features)
            
            # Calculate Isolation Forest score
            iso_score = self.models['isolation_forest'].fit_predict(processed_features)
            # Convert to 0-100 scale where higher = more anomalous
            iso_score_normalized = 50 + (iso_score[0] * 50) if iso_score[0] == -1 else 50
            
            # Calculate LOF score (already returns negative values for outliers)
            lof_score = self.models['lof'].fit_predict(processed_features)
            lof_score_normalized = 50 + (lof_score[0] * 50) if lof_score[0] == -1 else 50
            
            # For DBSCAN, we'll use the cluster labels (-1 indicates outlier)
            dbscan_labels = self.models['dbscan'].fit_predict(processed_features)
            dbscan_score = 100 if dbscan_labels[0] == -1 else 0
            
            # Calculate statistical outliers
            statistical_scores = self._calculate_statistical_anomalies(features)
            
            return {
                'isolation_forest_score': max(0, min(100, iso_score_normalized)),
                'lof_score': max(0, min(100, lof_score_normalized)),
                'dbscan_score': dbscan_score,
                'statistical_anomalies': statistical_scores,
                'composite_score': (iso_score_normalized + lof_score_normalized + dbscan_score) / 3
            }
            
        except Exception as e:
            logger.error(f"Error calculating anomaly scores: {str(e)}")
            return {
                'isolation_forest_score': 50,
                'lof_score': 50,
                'dbscan_score': 0,
                'statistical_anomalies': {},
                'composite_score': 50,
                'error': str(e)
            }
    
    def _calculate_statistical_anomalies(self, features):
        """
        Calculate statistical anomalies based on business rules
        
        Args:
            features (dict): Processed features
            
        Returns:
            dict: Statistical anomaly scores
        """
        anomalies = {}
        
        # Claim amount anomalies
        if features['claim_amount'] > 1000000:  # ₹1 million
            anomalies['high_claim_amount'] = {
                'score': 90,
                'message': f"Extremely high claim amount: ₹{features['claim_amount']:,.2f}"
            }
        elif features['claim_amount'] > 500000:  # ₹500,000
            anomalies['high_claim_amount'] = {
                'score': 70,
                'message': f"Very high claim amount: ₹{features['claim_amount']:,.2f}"
            }
        
        # Claim frequency anomalies
        if features['claim_frequency'] > 5:  # More than 5 claims per year
            anomalies['high_claim_frequency'] = {
                'score': 85,
                'message': f"Unusually high claim frequency: {features['claim_frequency']:.2f} claims/year"
            }
        elif features['claim_frequency'] > 2:  # More than 2 claims per year
            anomalies['high_claim_frequency'] = {
                'score': 65,
                'message': f"High claim frequency: {features['claim_frequency']:.2f} claims/year"
            }
        
        # Recent claim anomalies
        if features['time_since_last_claim'] < 7:  # Claim within 7 days of previous
            anomalies['recent_claim'] = {
                'score': 80,
                'message': f"Very recent previous claim: {features['time_since_last_claim']} days ago"
            }
        elif features['time_since_last_claim'] < 30:  # Claim within 30 days of previous
            anomalies['recent_claim'] = {
                'score': 60,
                'message': f"Recent previous claim: {features['time_since_last_claim']} days ago"
            }
        
        # Policy age anomalies (very new policies)
        if features['age_of_policy'] < 30:  # Policy less than 30 days old
            anomalies['new_policy'] = {
                'score': 75,
                'message': f"Very new policy: {features['age_of_policy']} days old"
            }
        
        # Claim amount ratio anomalies (compared to historical average)
        if 'claim_amount_ratio' in features:
            if features['claim_amount_ratio'] > 5:  # 5x average claim amount
                anomalies['amount_deviation'] = {
                    'score': 85,
                    'message': f"Claim amount is {features['claim_amount_ratio']:.1f}x historical average"
                }
            elif features['claim_amount_ratio'] > 2:  # 2x average claim amount
                anomalies['amount_deviation'] = {
                    'score': 65,
                    'message': f"Claim amount is {features['claim_amount_ratio']:.1f}x historical average"
                }
        
        return anomalies
    
    def _check_behavioral_patterns(self, claim_data, user_history):
        """
        Check for specific behavioral patterns indicative of fraud
        
        Args:
            claim_data (dict): Current claim data
            user_history (list): User's claim history
            
        Returns:
            dict: Pattern analysis results
        """
        patterns = {}
        
        # Weekend claims pattern (potential for staged incidents)
        try:
            claim_date = pd.to_datetime(claim_data.get('submission_date', datetime.now()))
            if claim_date.weekday() >= 5:  # Saturday or Sunday
                patterns['weekend_claim'] = {
                    'score': 40,
                    'message': "Claim submitted on weekend"
                }
        except:
            pass
        
        # Late-night submission pattern
        try:
            submission_time = pd.to_datetime(claim_data.get('submission_time', '12:00:00')).time()
            if submission_time.hour < 6 or submission_time.hour > 22:  # Between 10 PM and 6 AM
                patterns['late_night_submission'] = {
                    'score': 45,
                    'message': f"Claim submitted during unusual hours: {submission_time}"
                }
        except:
            pass
        
        # Rapid succession claims pattern
        if user_history and len(user_history) >= 2:
            recent_claims = sorted(user_history, key=lambda x: x.get('submission_date', ''), reverse=True)[:3]
            
            if len(recent_claims) >= 2:
                try:
                    dates = [pd.to_datetime(claim.get('submission_date')) for claim in recent_claims]
                    time_diffs = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
                    
                    if all(diff < 30 for diff in time_diffs):  # All within 30 days
                        patterns['rapid_succession'] = {
                            'score': 75,
                            'message': f"Multiple claims in rapid succession: {len(recent_claims)} claims within {max(time_diffs)} days"
                        }
                except:
                    pass
        
        # Location pattern changes
        if user_history:
            locations = [claim.get('incident_location', 'unknown') for claim in user_history]
            current_location = claim_data.get('incident_location', 'unknown')
            
            if locations and current_location not in locations:
                patterns['new_location'] = {
                    'score': 35,
                    'message': f"First claim in new location: {current_location}"
                }
        
        # Claim type pattern changes
        if user_history:
            claim_types = [claim.get('claim_type', 'unknown') for claim in user_history]
            current_type = claim_data.get('claim_type', 'unknown')
            
            if claim_types and current_type not in claim_types:
                patterns['new_claim_type'] = {
                    'score': 40,
                    'message': f"First claim of type: {current_type}"
                }
        
        return patterns
    
    def _calculate_risk_score(self, anomaly_scores, pattern_analysis):
        """
        Calculate overall behavioral risk score (0-100)
        
        Args:
            anomaly_scores (dict): Scores from ML models
            pattern_analysis (dict): Pattern analysis results
            
        Returns:
            float: Composite risk score
        """
        # Start with composite ML score (weight: 60%)
        base_score = anomaly_scores.get('composite_score', 50) * 0.6
        
        # Add statistical anomalies (weight: 30%)
        stat_score = 0
        stat_count = 0
        for anomaly in anomaly_scores.get('statistical_anomalies', {}).values():
            stat_score += anomaly['score']
            stat_count += 1
        
        if stat_count > 0:
            base_score += (stat_score / stat_count) * 0.3
        else:
            base_score += 50 * 0.3  # Neutral score if no statistical anomalies
        
        # Add pattern analysis (weight: 10%)
        pattern_score = 0
        pattern_count = 0
        for pattern in pattern_analysis.values():
            pattern_score += pattern['score']
            pattern_count += 1
        
        if pattern_count > 0:
            base_score += (pattern_score / pattern_count) * 0.1
        else:
            base_score += 50 * 0.1  # Neutral score if no patterns
        
        # Ensure score is within bounds and round
        return round(max(0, min(100, base_score)), 2)
    
    def _compile_findings(self, anomaly_scores, pattern_analysis, risk_score):
        """
        Compile human-readable findings from analysis
        
        Args:
            anomaly_scores (dict): Anomaly scores from ML models
            pattern_analysis (dict): Pattern analysis results
            risk_score (float): Overall risk score
            
        Returns:
            list: Human-readable findings
        """
        findings = []
        
        # Add ML model findings
        if anomaly_scores.get('composite_score', 50) > 70:
            findings.append("ML models detected significant behavioral anomalies")
        elif anomaly_scores.get('composite_score', 50) > 60:
            findings.append("ML models detected moderate behavioral anomalies")
        
        # Add statistical anomaly findings
        for anomaly in anomaly_scores.get('statistical_anomalies', {}).values():
            findings.append(anomaly['message'])
        
        # Add pattern findings
        for pattern in pattern_analysis.values():
            findings.append(pattern['message'])
        
        # Overall assessment
        if risk_score >= 80:
            findings.append("High behavioral risk detected - strongly recommend investigation")
        elif risk_score >= 65:
            findings.append("Moderate behavioral risk detected - recommend review")
        elif risk_score >= 50:
            findings.append("Some behavioral anomalies detected - monitor closely")
        else:
            findings.append("No significant behavioral anomalies detected")
        
        return findings
    
    def train_models(self, historical_claims):
        """
        Train behavioral models on historical data
        
        Args:
            historical_claims (list): Historical claim data for training
            
        Returns:
            dict: Training results and metrics
        """
        try:
            # Prepare training data
            training_data = []
            labels = []  # 0 for legitimate, 1 for fraudulent
            
            for claim in historical_claims:
                # Skip claims without required fraud labels
                if 'is_fraud' not in claim:
                    continue
                
                # Prepare features
                user_history = [c for c in historical_claims 
                              if c.get('user_id') == claim.get('user_id') 
                              and c.get('submission_date') < claim.get('submission_date')]
                
                features = self._prepare_features(claim, user_history)
                training_data.append(features)
                labels.append(1 if claim['is_fraud'] else 0)
            
            if not training_data:
                return {"success": False, "message": "No valid training data"}
            
            # Convert to DataFrame
            df = pd.DataFrame(training_data)
            
            # Select features for training
            feature_columns = ['claim_amount', 'age_of_policy', 'time_since_last_claim', 
                             'number_of_previous_claims', 'claim_frequency', 
                             'claim_type', 'incident_location', 'policy_type']
            
            # Preprocess features
            X_processed = self.preprocessor.fit_transform(df[feature_columns])
            
            # Train Isolation Forest (unsupervised, doesn't need labels)
            self.models['isolation_forest'].fit(X_processed)
            
            # Save trained models
            joblib.dump(self.models, self.model_path)
            joblib.dump(self.preprocessor, self.scaler_path)
            
            return {
                "success": True,
                "message": f"Models trained on {len(training_data)} samples",
                "fraud_rate": sum(labels) / len(labels) if labels else 0
            }
            
        except Exception as e:
            logger.error(f"Error training models: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def load_models(self):
        """Load trained models from disk"""
        try:
            if os.path.exists(self.model_path):
                self.models = joblib.load(self.model_path)
            if os.path.exists(self.scaler_path):
                self.preprocessor = joblib.load(self.scaler_path)
            logger.info("Behavioral models loaded successfully")
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")

# Singleton instance
behavioral_ai = BehavioralAI()
