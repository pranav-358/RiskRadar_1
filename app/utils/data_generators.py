import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

def generate_behavioral_training_data(num_samples=5000):
    """
    Generate synthetic training data for behavioral analysis
    
    Args:
        num_samples (int): Number of samples to generate
        
    Returns:
        list: Synthetic training data
    """
    np.random.seed(42)
    random.seed(42)
    
    data = []
    user_ids = [f"USER_{i:04d}" for i in range(1, 101)]
    claim_types = ['auto', 'health', 'property', 'life']
    locations = ['urban', 'suburban', 'rural']
    policy_types = ['comprehensive', 'basic', 'premium']
    
    # Generate base data for each user
    user_profiles = {}
    for user_id in user_ids:
        user_profiles[user_id] = {
            'base_claim_frequency': np.random.exponential(0.5),  # Claims per year
            'risk_profile': np.random.beta(2, 5),  # 0-1, higher = more risky
            'preferred_claim_type': random.choice(claim_types),
            'preferred_location': random.choice(locations)
        }
    
    start_date = datetime(2020, 1, 1)
    
    for i in range(num_samples):
        user_id = random.choice(user_ids)
        profile = user_profiles[user_id]
        
        # Determine if this is a fraudulent claim
        is_fraud = np.random.random() < (profile['risk_profile'] * 0.3)  # Max 30% fraud rate
        
        # Generate claim date (spread over 3 years)
        days_offset = random.randint(0, 3 * 365)
        claim_date = start_date + timedelta(days=days_offset)
        
        # Base claim amount based on type
        base_amounts = {
            'auto': np.random.lognormal(9, 1.2),      # ~₹10,000-100,000
            'health': np.random.lognormal(10, 1.0),    # ~₹20,000-200,000  
            'property': np.random.lognormal(11, 1.3),  # ~₹50,000-500,000
            'life': np.random.lognormal(12, 1.1)       # ~₹100,000-1,000,000
        }
        
        claim_type = profile['preferred_claim_type']
        if random.random() < 0.2:  # 20% chance of different claim type
            claim_type = random.choice([ct for ct in claim_types if ct != claim_type])
        
        base_amount = base_amounts[claim_type]
        
        # Adjust amount for fraudulent claims
        claim_amount = base_amount
        if is_fraud:
            # Fraudulent claims are typically larger
            claim_amount *= np.random.uniform(1.5, 5.0)
        
        # Add some random noise
        claim_amount *= np.random.uniform(0.8, 1.2)
        
        # Policy age (in days)
        policy_age = random.randint(0, 3650)  # 0-10 years
        
        claim_data = {
            'user_id': user_id,
            'claim_id': f"CLM_{10000 + i}",
            'claim_amount': round(claim_amount, 2),
            'claim_type': claim_type,
            'incident_location': profile['preferred_location'],
            'policy_type': random.choice(policy_types),
            'age_of_policy': policy_age,
            'submission_date': claim_date.strftime('%Y-%m-%d'),
            'submission_time': f"{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:00",
            'is_fraud': 1 if is_fraud else 0
        }
        
        data.append(claim_data)
    
    return data

def prepare_behavioral_dataset(claims_data):
    """
    Prepare dataset for behavioral model training
    
    Args:
        claims_data (list): Raw claims data
        
    Returns:
        tuple: (features, labels) for training
    """
    # This would be implemented based on your specific feature engineering needs
    # Similar to the _prepare_features method in BehavioralAI class
    pass
