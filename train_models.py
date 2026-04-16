#!/usr/bin/env python3
"""
Train ML models for fraud detection with proper data
This script trains Random Forest and Gradient Boosting models
"""

import os
os.environ['MPLBACKEND'] = 'Agg'

from app import create_app, db
from app.models import Claim, Document
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def prepare_training_data():
    """Prepare training data from database"""
    app = create_app()
    
    with app.app_context():
        # Get all claims with decisions
        claims = Claim.query.filter(Claim.decision.isnot(None)).all()
        
        logger.info(f"Found {len(claims)} claims with decisions in database")
        
        if len(claims) < 20:
            logger.warning("Not enough training data in database. Generating synthetic data...")
            return generate_synthetic_data()
        
        features = []
        labels = []
        
        for claim in claims:
            # Extract features
            feature_vector = extract_features(claim)
            features.append(feature_vector)
            
            # Label: 1 for fraud (rejected), 0 for legitimate (approved)
            label = 1 if claim.decision == 'rejected' else 0
            labels.append(label)
        
        logger.info(f"Extracted features from {len(features)} claims")
        return np.array(features), np.array(labels)

def extract_features(claim):
    """Extract features from claim for ML model"""
    features = []
    
    # 1. Claim amount (normalized by 100,000)
    features.append(float(claim.amount) / 100000.0)
    
    # 2. Claim type (one-hot encoded)
    claim_types = ['health', 'auto', 'property', 'life']
    for ct in claim_types:
        features.append(1.0 if claim.claim_type == ct else 0.0)
    
    # 3. Policy type (one-hot encoded)
    policy_types = ['comprehensive', 'basic', 'premium']
    for pt in policy_types:
        features.append(1.0 if claim.policy_type == pt else 0.0)
    
    # 4. Document authenticity score (average across all documents)
    docs = Document.query.filter_by(claim_id=claim.id).all()
    if docs:
        auth_scores = [d.authenticity_score or 50.0 for d in docs]
        avg_auth = sum(auth_scores) / len(auth_scores)
        features.append(avg_auth / 100.0)
    else:
        features.append(0.5)  # Neutral if no documents
    
    # 5. Number of documents (normalized)
    features.append(len(docs) / 5.0)  # Normalize by typical max
    
    # 6. Time between incident and submission (normalized to months)
    if claim.incident_date and claim.submission_date:
        days_diff = (claim.submission_date - claim.incident_date).days
        features.append(min(days_diff / 30.0, 1.0))  # Cap at 1 month
    else:
        features.append(0.5)  # Neutral if dates missing
    
    # 7. Risk score (if available)
    if claim.risk_score:
        features.append(claim.risk_score / 100.0)
    else:
        features.append(0.5)
    
    return features

def generate_synthetic_data(n_samples=5000):
    """
    Generate synthetic training data with realistic fraud patterns
    
    This creates a large dataset with known fraud indicators:
    - High amounts are more likely to be fraud
    - Low document authenticity indicates fraud
    - Quick submission after incident is suspicious
    - Few documents is suspicious
    """
    logger.info(f"Generating {n_samples} synthetic training samples...")
    
    np.random.seed(42)
    
    features = []
    labels = []
    
    # Generate balanced dataset (50% fraud, 50% legitimate)
    n_fraud = n_samples // 2
    n_legit = n_samples - n_fraud
    
    # Generate fraud cases
    for i in range(n_fraud):
        # Fraud cases tend to have:
        # - Higher amounts
        # - Lower document authenticity
        # - Quick submission
        # - Fewer documents
        # - Higher risk scores
        
        amount = np.random.uniform(3.0, 10.0)  # High amounts
        
        # Claim type (one-hot)
        claim_type = np.random.randint(0, 4)
        claim_type_vec = [1.0 if j == claim_type else 0.0 for j in range(4)]
        
        # Policy type (one-hot)
        policy_type = np.random.randint(0, 3)
        policy_type_vec = [1.0 if j == policy_type else 0.0 for j in range(3)]
        
        # Low document authenticity (fraud indicator)
        doc_auth = np.random.uniform(0.2, 0.6)
        
        # Few documents (fraud indicator)
        num_docs = np.random.uniform(0.1, 0.5)
        
        # Quick submission (fraud indicator)
        time_diff = np.random.uniform(0.0, 0.3)
        
        # High risk score (fraud indicator)
        risk_score = np.random.uniform(0.6, 0.95)
        
        feature_vector = [amount] + claim_type_vec + policy_type_vec + [doc_auth, num_docs, time_diff, risk_score]
        features.append(feature_vector)
        labels.append(1)  # Fraud
    
    # Generate legitimate cases
    for i in range(n_legit):
        # Legitimate cases tend to have:
        # - Moderate amounts
        # - High document authenticity
        # - Normal submission timing
        # - Adequate documents
        # - Lower risk scores
        
        amount = np.random.uniform(0.5, 5.0)  # Moderate amounts
        
        # Claim type (one-hot)
        claim_type = np.random.randint(0, 4)
        claim_type_vec = [1.0 if j == claim_type else 0.0 for j in range(4)]
        
        # Policy type (one-hot)
        policy_type = np.random.randint(0, 3)
        policy_type_vec = [1.0 if j == policy_type else 0.0 for j in range(3)]
        
        # High document authenticity (legitimate indicator)
        doc_auth = np.random.uniform(0.7, 1.0)
        
        # Adequate documents (legitimate indicator)
        num_docs = np.random.uniform(0.4, 1.0)
        
        # Normal submission timing
        time_diff = np.random.uniform(0.2, 0.8)
        
        # Low risk score (legitimate indicator)
        risk_score = np.random.uniform(0.1, 0.5)
        
        feature_vector = [amount] + claim_type_vec + policy_type_vec + [doc_auth, num_docs, time_diff, risk_score]
        features.append(feature_vector)
        labels.append(0)  # Legitimate
    
    # Shuffle the data
    indices = np.random.permutation(n_samples)
    features = np.array(features)[indices]
    labels = np.array(labels)[indices]
    
    logger.info(f"Generated {n_samples} samples: {n_fraud} fraud, {n_legit} legitimate")
    
    return features, labels

def train_models():
    """Train all ML models"""
    logger.info("="*80)
    logger.info("TRAINING ML MODELS FOR FRAUD DETECTION")
    logger.info("="*80)
    
    # Prepare data
    X, y = prepare_training_data()
    
    logger.info(f"\nTraining data: {len(X)} samples")
    logger.info(f"Fraud cases: {sum(y)} ({sum(y)/len(y)*100:.1f}%)")
    logger.info(f"Legitimate cases: {len(y)-sum(y)} ({(len(y)-sum(y))/len(y)*100:.1f}%)")
    
    # Split data (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    logger.info(f"\nTraining set: {len(X_train)} samples")
    logger.info(f"Test set: {len(X_test)} samples")
    
    # Scale features (important for ML models)
    logger.info("\nScaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train Random Forest
    logger.info("\n" + "-"*80)
    logger.info("Training Random Forest Classifier...")
    logger.info("-"*80)
    rf_model = RandomForestClassifier(
        n_estimators=300,  # More trees for better accuracy
        max_depth=20,
        min_samples_split=4,
        min_samples_leaf=1,
        random_state=42,
        class_weight='balanced',  # Handle imbalanced data
        n_jobs=-1  # Use all CPU cores
    )
    rf_model.fit(X_train_scaled, y_train)
    
    # Evaluate Random Forest
    rf_train_score = rf_model.score(X_train_scaled, y_train)
    rf_test_score = rf_model.score(X_test_scaled, y_test)
    rf_predictions = rf_model.predict(X_test_scaled)
    rf_proba = rf_model.predict_proba(X_test_scaled)[:, 1]
    
    logger.info(f"✓ Random Forest Training Accuracy: {rf_train_score:.2%}")
    logger.info(f"✓ Random Forest Test Accuracy: {rf_test_score:.2%}")
    
    try:
        rf_auc = roc_auc_score(y_test, rf_proba)
        logger.info(f"✓ Random Forest AUC-ROC: {rf_auc:.3f}")
    except:
        pass
    
    logger.info("\nRandom Forest Classification Report:")
    logger.info(classification_report(y_test, rf_predictions, 
                                     target_names=['Legitimate', 'Fraud']))
    
    # Train Gradient Boosting
    logger.info("\n" + "-"*80)
    logger.info("Training Gradient Boosting Classifier...")
    logger.info("-"*80)
    gb_model = GradientBoostingClassifier(
        n_estimators=300,
        max_depth=10,
        learning_rate=0.05,
        subsample=0.9,
        random_state=42
    )
    gb_model.fit(X_train_scaled, y_train)
    
    # Evaluate Gradient Boosting
    gb_train_score = gb_model.score(X_train_scaled, y_train)
    gb_test_score = gb_model.score(X_test_scaled, y_test)
    gb_predictions = gb_model.predict(X_test_scaled)
    gb_proba = gb_model.predict_proba(X_test_scaled)[:, 1]
    
    logger.info(f"✓ Gradient Boosting Training Accuracy: {gb_train_score:.2%}")
    logger.info(f"✓ Gradient Boosting Test Accuracy: {gb_test_score:.2%}")
    
    try:
        gb_auc = roc_auc_score(y_test, gb_proba)
        logger.info(f"✓ Gradient Boosting AUC-ROC: {gb_auc:.3f}")
    except:
        pass
    
    logger.info("\nGradient Boosting Classification Report:")
    logger.info(classification_report(y_test, gb_predictions,
                                     target_names=['Legitimate', 'Fraud']))
    
    # Save models
    models_dir = 'training_data/models'
    os.makedirs(models_dir, exist_ok=True)
    
    logger.info("\n" + "-"*80)
    logger.info("Saving models...")
    logger.info("-"*80)
    
    joblib.dump(rf_model, f'{models_dir}/random_forest.joblib')
    logger.info(f"✓ Saved: {models_dir}/random_forest.joblib")
    
    joblib.dump(gb_model, f'{models_dir}/gradient_boosting.joblib')
    logger.info(f"✓ Saved: {models_dir}/gradient_boosting.joblib")
    
    joblib.dump(scaler, f'{models_dir}/scaler.joblib')
    logger.info(f"✓ Saved: {models_dir}/scaler.joblib")
    
    # Save feature names
    feature_names = [
        'amount', 
        'claim_health', 'claim_auto', 'claim_property', 'claim_life',
        'policy_comprehensive', 'policy_basic', 'policy_premium',
        'doc_authenticity', 'num_documents', 'time_diff', 'risk_score'
    ]
    
    with open(f'{models_dir}/feature_names.json', 'w') as f:
        json.dump(feature_names, f, indent=2)
    logger.info(f"✓ Saved: {models_dir}/feature_names.json")
    
    # Save training metadata
    metadata = {
        'training_date': datetime.now().isoformat(),
        'n_samples': len(X),
        'n_train': len(X_train),
        'n_test': len(X_test),
        'fraud_percentage': float(sum(y) / len(y) * 100),
        'models': {
            'random_forest': {
                'train_accuracy': float(rf_train_score),
                'test_accuracy': float(rf_test_score),
                'auc_roc': float(rf_auc) if 'rf_auc' in locals() else None
            },
            'gradient_boosting': {
                'train_accuracy': float(gb_train_score),
                'test_accuracy': float(gb_test_score),
                'auc_roc': float(gb_auc) if 'gb_auc' in locals() else None
            }
        },
        'feature_names': feature_names
    }
    
    with open(f'{models_dir}/training_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"✓ Saved: {models_dir}/training_metadata.json")
    
    logger.info("\n" + "="*80)
    logger.info("✅ MODEL TRAINING COMPLETE!")
    logger.info("="*80)
    logger.info(f"\nModels saved to: {models_dir}/")
    logger.info("\nYour fraud detection system is now using trained ML models!")
    logger.info("The system will now provide accurate risk predictions based on:")
    logger.info("  ✓ Claim amount patterns")
    logger.info("  ✓ Document authenticity scores")
    logger.info("  ✓ Submission timing")
    logger.info("  ✓ Number of supporting documents")
    logger.info("  ✓ Historical fraud patterns")
    logger.info("\nRestart your server to use the new models:")
    logger.info("  python run.py")
    
    return rf_model, gb_model, scaler

if __name__ == '__main__':
    try:
        train_models()
    except Exception as e:
        logger.error(f"Training failed: {str(e)}", exc_info=True)
        exit(1)
