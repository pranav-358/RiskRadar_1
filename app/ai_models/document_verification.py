# app/ai_models/document_verification.py

import logging
import os
import re
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
import cv2
import numpy as np
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class DocumentVerificationAI:
    def __init__(self):
        self.known_templates = {}
        self.fraud_patterns = self._load_fraud_patterns()
        logger.info("Document Verification AI initialized")
    
    def _load_fraud_patterns(self):
        return {
            'template_mismatch': {'description': 'Document does not match known templates', 'weight': 0.8},
            'metadata_tampering': {'description': 'File metadata suggests editing', 'weight': 0.7},
            'text_inconsistency': {'description': 'Text content shows inconsistencies', 'weight': 0.6},
            'name_mismatch': {'description': 'Name in document does not match claimant', 'weight': 0.9},
            'image_tampering': {'description': 'Image shows signs of digital manipulation', 'weight': 0.85}
        }
    
    def analyze_document(self, file_path, file_type, claim_data=None):
        """
        Perform comprehensive document verification using OCR, name matching, and tampering detection
        
        Args:
            file_path (str): Path to the document file
            file_type (str): Type of document (medical_report, invoice, etc.)
            claim_data (dict): Claim information including claimant name
            
        Returns:
            dict: Analysis results with authenticity score and findings
        """
        try:
            findings = []
            risk_factors = []
            authenticity_score = 100.0  # Start with perfect score, deduct for issues
            
            logger.info(f"="*60)
            logger.info(f"Analyzing document: {file_path}")
            logger.info(f"Document type: {file_type}")
            logger.info(f"="*60)
            
            # 1. Extract text using OCR
            from app.ai_models import ocr_processor
            ocr_result = ocr_processor.extract_text(file_path, file_type)
            extracted_text = ocr_result.get('text', '')
            text_confidence = ocr_result.get('confidence', 0)
            
            logger.info(f"OCR Result: {len(extracted_text)} characters extracted")
            logger.info(f"OCR Confidence: {text_confidence:.2%}")
            logger.info(f"Extracted text preview: {extracted_text[:200]}...")
            
            # 2. Extract claimant name from claim data
            claimant_name = None
            if claim_data and 'claimant' in claim_data:
                claimant_name = claim_data['claimant'].get('name', '').strip()
                logger.info(f"Claimant name: {claimant_name}")
            
            # 3. Handle OCR extraction issues more gracefully
            if len(extracted_text) < 5:
                # OCR extracted very little text - could be poor quality OR tampering
                # Be more lenient - reduce penalty from 50 to 25 points
                authenticity_score -= 25.0  # Moderate penalty instead of massive
                findings.append("⚠️ WARNING: OCR extracted minimal text from document")
                findings.append("📋 Possible reasons:")
                findings.append("   • Image quality is too low (blurry, dark, or low resolution)")
                findings.append("   • Document is handwritten (harder for OCR)")
                findings.append("   • Image is a photo of a document (not a scan)")
                findings.append("   • Document may be tampered or edited")
                findings.append("💡 Recommendation: Upload a clearer, high-resolution scan or photo")
                risk_factors.append({
                    'type': 'low_text_extraction',
                    'severity': 'medium',  # Changed from 'critical' to 'medium'
                    'description': 'OCR extracted minimal text - may indicate poor image quality or tampering',
                    'impact': 25.0  # Reduced from 50.0
                })
                
                logger.warning(f"⚠️ Low text extraction: Only {len(extracted_text)} characters extracted")
            
            # 4. Name Verification - Compare extracted name with claimant name
            # Only check if we have reasonable amount of text
            elif claimant_name and len(extracted_text) >= 10:
                name_match_result = self._verify_name_match(extracted_text, claimant_name)
                
                logger.info(f"Name match result: {name_match_result}")
                
                if not name_match_result['match_found']:
                    # Name mismatch detected - but be more lenient
                    authenticity_score -= 30.0  # Reduced from 40.0
                    findings.append(f"⚠️ WARNING: Name verification issue")
                    findings.append(f"   Expected: '{claimant_name}'")
                    findings.append(f"   Status: Name not clearly found in extracted text")
                    findings.append(f"   Note: This could be due to OCR limitations or document format")
                    risk_factors.append({
                        'type': 'name_not_found',
                        'severity': 'high',  # Changed from 'critical'
                        'description': f"Claimant name '{claimant_name}' not found in extracted text",
                        'impact': 30.0  # Reduced from 40.0
                    })
                elif name_match_result['similarity'] < 0.8:
                    # Partial name match
                    authenticity_score -= 15.0  # Reduced from 20.0
                    findings.append(f"⚠️ Partial name match: Found '{name_match_result['found_name']}' (similarity: {name_match_result['similarity']:.2%})")
                    risk_factors.append({
                        'type': 'name_partial_match',
                        'severity': 'medium',  # Changed from 'high'
                        'description': f"Name similarity only {name_match_result['similarity']:.2%}",
                        'impact': 15.0  # Reduced from 20.0
                    })
                else:
                    findings.append(f"✓ Name verified: '{name_match_result['found_name']}' matches claimant '{claimant_name}'")
            elif claimant_name and len(extracted_text) < 10:
                # Very little text extracted - can't verify name reliably
                authenticity_score -= 20.0  # Moderate penalty
                findings.append("⚠️ Insufficient text extracted to verify claimant name")
                findings.append("💡 Please upload a clearer image for better verification")
                risk_factors.append({
                    'type': 'insufficient_text_for_verification',
                    'severity': 'medium',
                    'description': 'Not enough text extracted to verify document authenticity',
                    'impact': 20.0
                })
            
            # 5. Image Tampering Detection
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                tampering_result = self._detect_image_tampering(file_path)
                
                if tampering_result['is_tampered']:
                    authenticity_score -= 35.0
                    findings.append(f"⚠️ Image tampering detected: {tampering_result['reason']}")
                    risk_factors.append({
                        'type': 'image_tampering',
                        'severity': 'critical',
                        'description': tampering_result['reason'],
                        'impact': 35.0
                    })
                else:
                    findings.append("✓ No obvious image tampering detected")
            
            # 6. Metadata Analysis
            metadata_result = self._analyze_metadata(file_path)
            if metadata_result['suspicious']:
                authenticity_score -= 15.0
                findings.append(f"⚠️ Suspicious metadata: {metadata_result['reason']}")
                risk_factors.append({
                    'type': 'metadata_tampering',
                    'severity': 'medium',
                    'description': metadata_result['reason'],
                    'impact': 15.0
                })
            
            # 7. Document Quality Check - Be more lenient
            if text_confidence < 0.3 and len(extracted_text) > 0:
                authenticity_score -= 10.0  # Reduced from 15.0
                findings.append(f"ℹ️ Low OCR confidence ({text_confidence:.2%}) - document quality could be improved")
                findings.append("💡 Tip: Use a scanner or take photo in good lighting for better results")
                risk_factors.append({
                    'type': 'low_quality',
                    'severity': 'low',  # Changed from 'medium'
                    'description': f'OCR confidence only {text_confidence:.2%} - image quality issue',
                    'impact': 10.0  # Reduced from 15.0
                })
            
            # Ensure score stays in valid range
            authenticity_score = max(0.0, min(100.0, authenticity_score))
            
            # Determine if document is tampered based on score
            is_tampered = authenticity_score < 60.0
            
            if not findings:
                findings.append("✓ Document appears authentic with no major issues detected")
            
            logger.info(f"Final authenticity score: {authenticity_score}/100")
            logger.info(f"Is tampered: {is_tampered}")
            logger.info(f"Findings: {len(findings)}")
            logger.info(f"="*60)
            
            return {
                "authenticity_score": authenticity_score,
                "extracted_text": extracted_text[:500],  # First 500 chars for storage
                "full_text_length": len(extracted_text),
                "text_confidence": text_confidence,
                "findings": findings,
                "risk_factors": risk_factors,
                "is_tampered": is_tampered,
                "claimant_name": claimant_name,
                "metadata": metadata_result.get('metadata', {}),
                "ocr_method": ocr_result.get('method', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Error analyzing document {file_path}: {str(e)}", exc_info=True)
            return {
                "authenticity_score": 30.0,  # Low score for errors
                "extracted_text": "",
                "text_confidence": 0.0,
                "findings": [f"Analysis error: {str(e)}", "⚠️ Document could not be properly analyzed - treating as suspicious"],
                "is_tampered": True,  # Treat errors as suspicious
                "error": str(e)
            }
    
    def _verify_name_match(self, extracted_text, claimant_name):
        """
        Verify if claimant name appears in extracted text
        
        Args:
            extracted_text (str): Text extracted from document
            claimant_name (str): Expected claimant name
            
        Returns:
            dict: Match result with similarity score
        """
        try:
            # Normalize text for comparison
            text_lower = extracted_text.lower()
            name_lower = claimant_name.lower()
            
            # Split name into parts
            name_parts = [part.strip() for part in name_lower.split() if len(part.strip()) > 1]
            
            # Check for exact match
            if name_lower in text_lower:
                return {
                    'match_found': True,
                    'found_name': claimant_name,
                    'similarity': 1.0,
                    'match_type': 'exact'
                }
            
            # Check for partial matches (first name + last name)
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = name_parts[-1]
                
                if first_name in text_lower and last_name in text_lower:
                    return {
                        'match_found': True,
                        'found_name': f"{first_name.title()} {last_name.title()}",
                        'similarity': 0.9,
                        'match_type': 'partial'
                    }
            
            # Try fuzzy matching - find most similar name in text
            # Extract potential names (capitalized words)
            potential_names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', extracted_text)
            
            best_match = None
            best_similarity = 0.0
            
            for potential_name in potential_names:
                similarity = SequenceMatcher(None, name_lower, potential_name.lower()).ratio()
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = potential_name
            
            # Consider it a match if similarity > 70%
            if best_similarity >= 0.7:
                return {
                    'match_found': True,
                    'found_name': best_match,
                    'similarity': best_similarity,
                    'match_type': 'fuzzy'
                }
            
            # No match found
            return {
                'match_found': False,
                'found_name': None,
                'similarity': best_similarity,
                'match_type': 'none'
            }
            
        except Exception as e:
            logger.error(f"Error in name verification: {str(e)}")
            return {
                'match_found': False,
                'found_name': None,
                'similarity': 0.0,
                'match_type': 'error'
            }
    
    def _detect_image_tampering(self, file_path):
        """
        Detect image tampering using Error Level Analysis (ELA) and other techniques
        
        Args:
            file_path (str): Path to image file
            
        Returns:
            dict: Tampering detection result
        """
        try:
            # Read image
            img = cv2.imread(file_path)
            if img is None:
                return {'is_tampered': False, 'reason': 'Unable to read image'}
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 1. Check for copy-paste artifacts using edge detection
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Unusually high edge density can indicate tampering
            if edge_density > 0.3:
                return {
                    'is_tampered': True,
                    'reason': f'High edge density ({edge_density:.2%}) suggests possible copy-paste manipulation',
                    'confidence': 0.7
                }
            
            # 2. Check for noise inconsistencies
            # Calculate noise level in different regions
            h, w = gray.shape
            regions = [
                gray[0:h//2, 0:w//2],
                gray[0:h//2, w//2:w],
                gray[h//2:h, 0:w//2],
                gray[h//2:h, w//2:w]
            ]
            
            noise_levels = []
            for region in regions:
                # Calculate standard deviation as noise measure
                noise = np.std(region)
                noise_levels.append(noise)
            
            # Check if noise levels vary significantly
            noise_variance = np.std(noise_levels)
            if noise_variance > 15:
                return {
                    'is_tampered': True,
                    'reason': f'Inconsistent noise levels across image regions (variance: {noise_variance:.2f})',
                    'confidence': 0.6
                }
            
            # 3. Check for JPEG compression artifacts inconsistency
            # This is a simplified check - real ELA would be more complex
            if file_path.lower().endswith(('.jpg', '.jpeg')):
                # Calculate compression quality estimate
                file_size = os.path.getsize(file_path)
                pixel_count = img.shape[0] * img.shape[1]
                bytes_per_pixel = file_size / pixel_count
                
                # Very low compression (high quality) can indicate re-saving after editing
                if bytes_per_pixel > 3.0:
                    return {
                        'is_tampered': True,
                        'reason': f'Unusually high JPEG quality ({bytes_per_pixel:.2f} bytes/pixel) suggests re-saving after editing',
                        'confidence': 0.5
                    }
            
            return {
                'is_tampered': False,
                'reason': 'No obvious tampering detected',
                'confidence': 0.8
            }
            
        except Exception as e:
            logger.error(f"Error in tampering detection: {str(e)}")
            return {
                'is_tampered': False,
                'reason': f'Tampering detection error: {str(e)}',
                'confidence': 0.0
            }
    
    def _analyze_metadata(self, file_path):
        """
        Analyze file metadata for signs of editing
        
        Args:
            file_path (str): Path to file
            
        Returns:
            dict: Metadata analysis result
        """
        try:
            metadata = {}
            suspicious = False
            reason = ""
            
            # Get file stats
            stat_info = os.stat(file_path)
            metadata['file_size'] = stat_info.st_size
            metadata['created'] = datetime.fromtimestamp(stat_info.st_ctime).isoformat()
            metadata['modified'] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            
            # For images, extract EXIF data
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                try:
                    image = Image.open(file_path)
                    exif_data = image._getexif()
                    
                    if exif_data:
                        for tag_id, value in exif_data.items():
                            tag = TAGS.get(tag_id, tag_id)
                            metadata[tag] = str(value)
                        
                        # Check for editing software signatures
                        software_tags = ['Software', 'ProcessingSoftware', 'HostComputer']
                        editing_software = ['photoshop', 'gimp', 'paint.net', 'pixlr', 'canva']
                        
                        for tag in software_tags:
                            if tag in metadata:
                                software_value = metadata[tag].lower()
                                for editor in editing_software:
                                    if editor in software_value:
                                        suspicious = True
                                        reason = f"Document edited with {editor.title()}"
                                        break
                except Exception as e:
                    logger.debug(f"Could not extract EXIF data: {str(e)}")
            
            return {
                'suspicious': suspicious,
                'reason': reason,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error analyzing metadata: {str(e)}")
            return {
                'suspicious': False,
                'reason': '',
                'metadata': {}
            }

# Singleton instance
document_verifier = DocumentVerificationAI()
