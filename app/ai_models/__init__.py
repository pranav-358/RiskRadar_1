# app/ai_models/__init__.py

from .predictive_scoring import predictive_model
from .document_verification import document_verifier
from .behavioral_analysis import behavioral_ai
from .hidden_link import hidden_link_ai
from .explainable_ai import explainable_ai
from .ocr_processor import ocr_processor

__all__ = [
    'predictive_model',
    'document_verifier',
    'behavioral_ai',
    'hidden_link_ai',
    'explainable_ai',
    'ocr_processor'
]
