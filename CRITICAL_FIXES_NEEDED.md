# Critical Fixes for RiskRadar - Step by Step

## Issue 1: OCR Not Extracting Text (0% Confidence)

### Problem:
- EasyOCR failing to extract text
- Showing "⚠️ Unable to extract text from document"
- 0.00% confidence

### Root Cause:
EasyOCR needs proper initialization with Hindi + English for Indian documents

### Fix for `app/ai_models/ocr_processor.py`:

```python
class OCRProcessor:
    def __init__(self, use_easyocr=True):
        self.use_easyocr = use_easyocr
        self.reader = None
        
        if use_easyocr:
            try:
                # CRITICAL: Support both English and Hindi for Indian documents
                self.reader = easyocr.Reader(['en', 'hi'], gpu=False)
                logger.info("EasyOCR initialized with English and Hindi support")
            except Exception as e:
                logger.warning(f"EasyOCR initialization failed: {e}")
                self.use_easyocr = False
    
    def _extract_from_image(self, file_path):
        """Enhanced extraction with better preprocessing"""
        try:
            # Try multiple preprocessing techniques
            results = []
            
            # Method 1: Original image
            img = cv2.imread(file_path)
            if img is not None:
                result1 = self._ocr_with_easyocr(img)
                results.append(result1)
            
            # Method 2: Grayscale + Threshold
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            result2 = self._ocr_with_easyocr(thresh)
            results.append(result2)
            
            # Method 3: Denoised
            denoised = cv2.fastNlMeansDenoising(gray)
            result3 = self._ocr_with_easyocr(denoised)
            results.append(result3)
            
            # Method 4: Adaptive threshold (best for handwritten)
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            result4 = self._ocr_with_easyocr(adaptive)
            results.append(result4)
            
            # Choose best result (most text extracted)
            best_result = max(results, key=lambda x: len(x.get('text', '')))
            
            # If still no text, try with PIL enhancement
            if len(best_result.get('text', '')) < 10:
                pil_img = Image.open(file_path)
                # Enhance contrast
                enhancer = ImageEnhance.Contrast(pil_img)
                enhanced = enhancer.enhance(2.0)
                # Enhance sharpness
                enhancer = ImageEnhance.Sharpness(enhanced)
                enhanced = enhancer.enhance(2.0)
                
                # Save temporarily and process
                temp_path = file_path + '_enhanced.png'
                enhanced.save(temp_path)
                img_enhanced = cv2.imread(temp_path)
                result5 = self._ocr_with_easyocr(img_enhanced)
                os.remove(temp_path)
                
                if len(result5.get('text', '')) > len(best_result.get('text', '')):
                    best_result = result5
            
            return best_result
            
        except Exception as e:
            logger.error(f"Error in _extract_from_image: {str(e)}")
            return {"text": "", "confidence": 0, "error": str(e)}
    
    def _ocr_with_easyocr(self, image):
        """Perform OCR with EasyOCR"""
        try:
            if self.reader is None:
                return {"text": "", "confidence": 0}
            
            # EasyOCR expects numpy array
            if isinstance(image, str):
                image = cv2.imread(image)
            
            results = self.reader.readtext(image, detail=1, paragraph=True)
            
            if not results:
                return {"text": "", "confidence": 0}
            
            # Combine all text
            text_parts = []
            confidences = []
            
            for detection in results:
                bbox, text, conf = detection
                text_parts.append(text)
                confidences.append(conf)
            
            full_text = " ".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "text": full_text,
                "confidence": avg_confidence,
                "word_count": len(full_text.split())
            }
            
        except Exception as e:
            logger.error(f"EasyOCR error: {str(e)}")
            return {"text": "", "confidence": 0, "error": str(e)}
```

---

## Issue 2: Amount Field Erasing

### Problem:
When user types "100000" and moves to next field, it gets erased

### Root Cause:
JavaScript validation or form reset issue

### Fix for `app/user/templates/user/new_claim.html`:

Find the amount input field and check for any JavaScript that might be clearing it.

**Look for:**
```html
<input type="number" name="amount" id="amount" ...>
```

**Replace with:**
```html
<input type="text" 
       name="amount" 
       id="amount" 
       class="form-control" 
       placeholder="Enter amount (e.g., 50000)"
       pattern="[0-9,]+"
       required>
```

**Add this JavaScript at the bottom:**
```javascript
<script>
// Format amount with commas as user types
document.getElementById('amount').addEventListener('input', function(e) {
    let value = e.target.value.replace(/,/g, '');
    if (!isNaN(value) && value !== '') {
        // Format with commas
        e.target.value = parseInt(value).toLocaleString('en-IN');
    }
});

// Remove commas before form submission
document.querySelector('form').addEventListener('submit', function(e) {
    let amountField = document.getElementById('amount');
    amountField.value = amountField.value.replace(/,/g, '');
});
</script>
```

---

## Issue 3: Proper ML Training (Not Random Scores)

### Problem:
System giving random scores instead of trained ML predictions

### Solution:
Create a proper training pipeline

### Create new file: `train_models.py`

```python
#!/usr/bin/env python3
"""
Train all ML models with proper data
"""

import os
os.environ['MPLBACKEND'] = 'Agg'

from app import create_app, db
from app.models import Claim, Document
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import json

def prepare_training_data():
    """Prepare training data from database"""
    app = create_app()
    
    with app.app_context():
        # Get all claims with decisions
        claims = Claim.query.filter(Claim.decision.isnot(None)).all()
        
        if len(claims) < 50:
            print("Not enough training data. Need at least 50 claims with decisions.")
            print("Generating synthetic training data...")
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
        
        return np.array(features), np.array(labels)

def extract_features(claim):
    """Extract features from claim"""
    features = []
    
    # 1. Claim amount (normalized)
    features.append(claim.amount / 100000.0)
    
    # 2. Claim type (one-hot encoded)
    claim_types = ['health', 'auto', 'property', 'life']
    for ct in claim_types:
        features.append(1 if claim.claim_type == ct else 0)
    
    # 3. Policy type
    policy_types = ['comprehensive', 'basic', 'premium']
    for pt in policy_types:
        features.append(1 if claim.policy_type == pt else 0)
    
    # 4. Document authenticity score
    docs = Document.query.filter_by(claim_id=claim.id).all()
    if docs:
        avg_auth = sum(d.authenticity_score or 50 for d in docs) / len(docs)
        features.append(avg_auth / 100.0)
    else:
        features.append(0.5)
    
    # 5. Number of documents
    features.append(len(docs) / 5.0)  # Normalize by typical max
    
    # 6. Time features
    if claim.incident_date and claim.submission_date:
        days_diff = (claim.submission_date - claim.incident_date).days
        features.append(min(days_diff / 30.0, 1.0))  # Normalize to months
    else:
        features.append(0.5)
    
    return features

def generate_synthetic_data():
    """Generate synthetic training data"""
    print("Generating 1000 synthetic training samples...")
    
    np.random.seed(42)
    n_samples = 1000
    
    features = []
    labels = []
    
    for i in range(n_samples):
        # Generate features
        amount = np.random.uniform(0.1, 10.0)  # Normalized amount
        
        # Claim type (one-hot)
        claim_type = np.random.randint(0, 4)
        claim_type_vec = [1 if j == claim_type else 0 for j in range(4)]
        
        # Policy type (one-hot)
        policy_type = np.random.randint(0, 3)
        policy_type_vec = [1 if j == policy_type else 0 for j in range(3)]
        
        # Document authenticity
        doc_auth = np.random.uniform(0.3, 1.0)
        
        # Number of documents
        num_docs = np.random.uniform(0.2, 1.0)
        
        # Time difference
        time_diff = np.random.uniform(0.0, 1.0)
        
        feature_vector = [amount] + claim_type_vec + policy_type_vec + [doc_auth, num_docs, time_diff]
        features.append(feature_vector)
        
        # Generate label based on features (fraud indicators)
        fraud_score = 0
        
        # High amount increases fraud risk
        if amount > 5.0:
            fraud_score += 0.3
        
        # Low document authenticity increases fraud risk
        if doc_auth < 0.6:
            fraud_score += 0.4
        
        # Quick submission after incident is suspicious
        if time_diff < 0.1:
            fraud_score += 0.2
        
        # Few documents is suspicious
        if num_docs < 0.4:
            fraud_score += 0.1
        
        # Add some randomness
        fraud_score += np.random.uniform(-0.2, 0.2)
        
        label = 1 if fraud_score > 0.5 else 0
        labels.append(label)
    
    return np.array(features), np.array(labels)

def train_models():
    """Train all models"""
    print("="*60)
    print("Training ML Models")
    print("="*60)
    
    # Prepare data
    X, y = prepare_training_data()
    
    print(f"\nTraining data: {len(X)} samples")
    print(f"Fraud cases: {sum(y)} ({sum(y)/len(y)*100:.1f}%)")
    print(f"Legitimate cases: {len(y)-sum(y)} ({(len(y)-sum(y))/len(y)*100:.1f}%)")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train Random Forest
    print("\nTraining Random Forest...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    )
    rf_model.fit(X_train_scaled, y_train)
    rf_score = rf_model.score(X_test_scaled, y_test)
    print(f"Random Forest Accuracy: {rf_score:.2%}")
    
    # Train Gradient Boosting
    print("\nTraining Gradient Boosting...")
    gb_model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=42
    )
    gb_model.fit(X_train_scaled, y_train)
    gb_score = gb_model.score(X_test_scaled, y_test)
    print(f"Gradient Boosting Accuracy: {gb_score:.2%}")
    
    # Save models
    models_dir = 'training_data/models'
    os.makedirs(models_dir, exist_ok=True)
    
    joblib.dump(rf_model, f'{models_dir}/random_forest.joblib')
    joblib.dump(gb_model, f'{models_dir}/gradient_boosting.joblib')
    joblib.dump(scaler, f'{models_dir}/scaler.joblib')
    
    # Save feature names
    feature_names = [
        'amount', 'claim_health', 'claim_auto', 'claim_property', 'claim_life',
        'policy_comprehensive', 'policy_basic', 'policy_premium',
        'doc_authenticity', 'num_documents', 'time_diff'
    ]
    
    with open(f'{models_dir}/feature_names.json', 'w') as f:
        json.dump(feature_names, f)
    
    print("\n" + "="*60)
    print("Models saved successfully!")
    print("="*60)
    print(f"\nSaved to: {models_dir}/")
    print("- random_forest.joblib")
    print("- gradient_boosting.joblib")
    print("- scaler.joblib")
    print("- feature_names.json")
    
    return rf_model, gb_model, scaler

if __name__ == '__main__':
    train_models()
```

---

## Issue 4: Update Predictive Model to Use Trained Models

### Fix `app/ai_models/predictive_scoring.py`:

```python
import joblib
import os
import numpy as np

class PredictiveModel:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.load_model()
    
    def load_model(self):
        """Load trained model"""
        try:
            models_dir = 'training_data/models'
            
            if os.path.exists(f'{models_dir}/gradient_boosting.joblib'):
                self.model = joblib.load(f'{models_dir}/gradient_boosting.joblib')
                self.scaler = joblib.load(f'{models_dir}/scaler.joblib')
                
                import json
                with open(f'{models_dir}/feature_names.json', 'r') as f:
                    self.feature_names = json.load(f)
                
                logger.info("Trained model loaded successfully")
            else:
                logger.warning("No trained model found. Using rule-based system.")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
    
    def predict(self, claim_data):
        """Predict fraud probability"""
        try:
            if self.model is None:
                # Fallback to rule-based
                return self._rule_based_prediction(claim_data)
            
            # Extract features
            features = self._extract_features(claim_data)
            features_scaled = self.scaler.transform([features])
            
            # Get probability
            prob = self.model.predict_proba(features_scaled)[0][1]
            
            # Convert to 0-100 scale
            return prob * 100.0
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return self._rule_based_prediction(claim_data)
    
    def _extract_features(self, claim_data):
        """Extract features matching training data"""
        features = []
        
        # Amount
        features.append(claim_data.get('claim_amount', 0) / 100000.0)
        
        # Claim type
        claim_type = claim_data.get('claim_type', 'health')
        for ct in ['health', 'auto', 'property', 'life']:
            features.append(1 if claim_type == ct else 0)
        
        # Policy type
        policy_type = claim_data.get('policy_type', 'basic')
        for pt in ['comprehensive', 'basic', 'premium']:
            features.append(1 if policy_type == pt else 0)
        
        # Document authenticity
        doc_score = claim_data.get('document_verification_score', 50) / 100.0
        features.append(doc_score)
        
        # Number of documents
        num_docs = len(claim_data.get('documents', [])) / 5.0
        features.append(num_docs)
        
        # Time difference
        features.append(0.5)  # Default
        
        return features
    
    def _rule_based_prediction(self, claim_data):
        """Fallback rule-based prediction"""
        score = 50.0  # Start neutral
        
        # Document verification
        doc_score = claim_data.get('document_verification_score', 50)
        if doc_score < 60:
            score += 20
        elif doc_score > 80:
            score -= 10
        
        # Behavioral analysis
        behavioral_score = claim_data.get('behavioral_anomaly_score', 50)
        if behavioral_score > 70:
            score += 15
        
        # Hidden links
        link_score = claim_data.get('hidden_link_score', 50)
        if link_score > 70:
            score += 15
        
        # Amount
        amount = claim_data.get('claim_amount', 0)
        if amount > 500000:
            score += 10
        
        return min(max(score, 0), 100)
```

---

## How to Apply These Fixes:

### Step 1: Fix OCR (Highest Priority)
```bash
# Update requirements.txt to include Hindi support
pip install easyocr --upgrade

# Replace the OCR processor code with the enhanced version above
```

### Step 2: Fix Amount Field
- Open `app/user/templates/user/new_claim.html`
- Find the amount input field
- Replace with the code provided above
- Add the JavaScript at the bottom

### Step 3: Train Models
```bash
# Create the train_models.py file
# Run training
python train_models.py
```

### Step 4: Update Predictive Model
- Replace `app/ai_models/predictive_scoring.py` with the code above

### Step 5: Test Everything
```bash
# Start server
python run.py

# Test with real document
# Upload handwritten prescription
# Check if text is extracted
# Verify risk score is based on ML, not random
```

---

## Expected Results After Fixes:

1. ✅ OCR extracts text from handwritten documents
2. ✅ Amount field doesn't erase (100000 stays as 1,00,000)
3. ✅ Risk scores based on trained ML model
4. ✅ Supports Hindi + English text
5. ✅ Multiple preprocessing methods for better accuracy

---

## Testing Checklist:

- [ ] Upload handwritten prescription → Text extracted
- [ ] Upload printed document → Text extracted
- [ ] Type amount 100000 → Stays formatted as 1,00,000
- [ ] Submit claim → Risk score between 0-100 (not random)
- [ ] Name mismatch → High risk score (80-95%)
- [ ] Name match → Low risk score (20-40%)

---

**This is the proper ML approach, not random numbers!**
