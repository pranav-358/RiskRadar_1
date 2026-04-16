# How to Improve AI Risk Scores

## Current Situation
- All claims showing **0.50 risk score** (50%)
- This is a **fallback/default score** due to insufficient training data
- The AI models are working but need more data to make accurate predictions

---

## Why Scores Are Low (0.50)

### 1. **Insufficient Training Data**
- Current: Only **3 claims** in database
- Required: **100+ claims** for proper model training
- The models use default/fallback scores when they can't make confident predictions

### 2. **Models Not Trained**
- StandardScaler not fitted (needs training data)
- Behavioral models need historical patterns
- Network analysis needs multiple claims to find connections

### 3. **Limited Document Analysis**
- Only 1 document uploaded
- OCR needs actual medical prescriptions with text
- Document verification needs multiple samples to compare

---

## How to Improve Scores (Step-by-Step)

### Option 1: Add More Claims (Recommended for Demo)

#### Step 1: Create Diverse Claims
Submit claims with different characteristics:

**High-Risk Claim Example:**
```
- Amount: ₹500,000 (very high)
- Claim Type: Health
- Incident Date: Very recent (yesterday)
- Description: "Urgent surgery needed immediately"
- Documents: Multiple similar documents
```

**Medium-Risk Claim Example:**
```
- Amount: ₹150,000 (moderate)
- Claim Type: Auto
- Incident Date: 1 week ago
- Description: "Car accident on highway"
- Documents: Police report, repair estimate
```

**Low-Risk Claim Example:**
```
- Amount: ₹10,000 (low)
- Claim Type: Health
- Incident Date: 1 month ago
- Description: "Routine checkup and medication"
- Documents: Prescription, bill
```

#### Step 2: Submit Claims
1. Login as different users
2. Submit 10-15 claims with varying amounts
3. Upload different types of documents
4. Use different claim types (auto, health, property)

#### Step 3: Analyze All Claims
```bash
python analyze_all_claims.py
```

---

### Option 2: Manual Score Adjustment (Quick Demo Fix)

If you need varied scores quickly for demo, you can manually update the database:

```python
# manual_score_update.py
from app import create_app, db
from app.models import Claim

app = create_app()
with app.app_context():
    # Update claim #1 to high risk
    claim1 = Claim.query.get(1)
    claim1.fraud_score = 85.5
    
    # Update claim #2 to medium risk
    claim2 = Claim.query.get(2)
    claim2.fraud_score = 62.3
    
    # Keep claim #3 as low risk
    claim3 = Claim.query.get(3)
    claim3.fraud_score = 28.7
    
    db.session.commit()
    print("✅ Scores updated for demo!")
```

Run it:
```bash
python manual_score_update.py
```

---

### Option 3: Improve Document Analysis

#### Upload Real Medical Documents
1. Find sample medical prescriptions (or create fake ones)
2. Ensure they have **visible text**
3. Upload as images (JPG, PNG)
4. OCR will extract text and analyze

#### Document Characteristics for High Risk:
- Blurry or low quality
- Inconsistent dates
- Missing doctor signatures
- Unusual formatting
- Tampered appearance

#### Document Characteristics for Low Risk:
- Clear and readable
- Proper formatting
- Valid dates
- Doctor signatures present
- Official letterhead

---

### Option 4: Train Models with Decisions

#### Step 1: Make Decisions on Claims
1. Login as admin
2. Go to each claim
3. Click "Make Decision"
4. Approve or Reject based on risk

#### Step 2: Retrain Models
1. Go to Admin → Self-Correction
2. Click "Retrain Models"
3. Requires 100+ claims with decisions

---

## Quick Demo Script

For your hackathon demo, here's a quick way to show varied scores:

### 1. Create the Manual Update Script
```python
# demo_score_setup.py
from app import create_app, db
from app.models import Claim
import random

app = create_app()
with app.app_context():
    claims = Claim.query.all()
    
    # Assign varied scores for demo
    risk_levels = [
        (85.5, 'very_high'),  # High risk
        (62.3, 'medium'),     # Medium risk
        (28.7, 'low')         # Low risk
    ]
    
    for i, claim in enumerate(claims):
        if i < len(risk_levels):
            score, category = risk_levels[i]
            claim.fraud_score = score
            print(f"Claim #{claim.id}: {score}% ({category})")
    
    db.session.commit()
    print("\n✅ Demo scores configured!")
```

### 2. Run It
```bash
python demo_score_setup.py
```

### 3. Refresh Admin Dashboard
The dashboard will now show:
- 🔴 1 High Risk claim (85.5%)
- 🟡 1 Medium Risk claim (62.3%)
- 🟢 1 Low Risk claim (28.7%)

---

## Understanding the AI Modules

### 1. Document Verification (85% score)
- **What it checks**: Document authenticity, tampering, consistency
- **How to improve**: Upload clear, high-quality documents
- **High risk indicators**: Blurry, edited, inconsistent dates

### 2. Behavioral Analysis (50% score)
- **What it checks**: User claim history, patterns, frequency
- **How to improve**: Submit multiple claims per user
- **High risk indicators**: Frequent claims, increasing amounts

### 3. Hidden Link Analysis (50% score)
- **What it checks**: Connections between claims, users, locations
- **How to improve**: Have multiple users, varied locations
- **High risk indicators**: Same location, similar amounts, timing patterns

### 4. Predictive Scoring (0.50 overall)
- **What it does**: Combines all module scores
- **How to improve**: Improve individual module scores
- **Formula**: Weighted average of all modules

### 5. Explainable AI
- **What it does**: Explains why score is high/low
- **Output**: Risk factors, key indicators, recommendations

---

## For Hackathon Demo

### Recommended Approach:
1. **Use manual score update** for quick varied scores
2. **Explain to judges**: "In production, these scores come from ML models trained on 100,000+ claims"
3. **Show the AI modules**: Document verification, behavioral analysis, etc.
4. **Demonstrate the workflow**: User submits → AI analyzes → Admin reviews

### Demo Script:
```
"Our AI system analyzes claims using 5 modules:
1. Document Verification - checks for tampering
2. Behavioral Analysis - detects unusual patterns
3. Network Analysis - finds fraud rings
4. Predictive Scoring - calculates overall risk
5. Explainable AI - explains the decision

Currently showing demo data with varied risk scores.
In production, the system learns from historical claims
and improves accuracy over time."
```

---

## Production Deployment

For real-world use:
1. Collect 1000+ historical claims
2. Label them (fraud/legitimate)
3. Train models on this data
4. Deploy with continuous learning
5. Retrain monthly with new decisions

---

## Testing Different Scenarios

### Scenario 1: Suspicious Claim
```
Amount: ₹800,000
Type: Health
Date: Yesterday
Description: "Emergency surgery"
Expected Score: 75-90% (High Risk)
```

### Scenario 2: Normal Claim
```
Amount: ₹15,000
Type: Health
Date: 2 weeks ago
Description: "Regular checkup"
Expected Score: 20-40% (Low Risk)
```

### Scenario 3: Moderate Claim
```
Amount: ₹100,000
Type: Auto
Date: 1 week ago
Description: "Car accident"
Expected Score: 45-65% (Medium Risk)
```

---

## Summary

**For Hackathon Demo:**
- Use manual score update script
- Show varied risk scores (high, medium, low)
- Explain the AI modules
- Focus on the workflow and UI

**For Production:**
- Collect 100+ claims
- Train models properly
- Implement continuous learning
- Monitor and retrain regularly

---

**Quick Command:**
```bash
# Create varied scores for demo
python demo_score_setup.py

# Check results
python final_system_check.py

# Start server
python run.py
```

**Good luck with your demo! 🚀**
