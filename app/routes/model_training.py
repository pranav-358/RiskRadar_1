from flask import Blueprint, request, jsonify
from app.ai_models import predictive_model
from app.utils.helpers import generate_synthetic_training_data, prepare_training_dataset
import logging

logger = logging.getLogger(__name__)
training_bp = Blueprint('training', __name__)

@training_bp.route('/retrain', methods=['POST'])
def retrain_model():
    """
    Endpoint to retrain the predictive model
    """
    try:
        # In a real application, you would get this from your database
        # For now, we'll use synthetic data
        training_data = generate_synthetic_training_data(10000)
        
        # Prepare features and labels
        features, labels = prepare_training_dataset(training_data)
        
        # Train the model
        results = predictive_model.train(features, labels)
        
        return jsonify({
            'success': True,
            'message': 'Model retrained successfully',
            'metrics': results['val_metrics']
        })
        
    except Exception as e:
        logger.error(f"Error in model training: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Training failed: {str(e)}'
        }), 500
