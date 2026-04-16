import os
import cv2
import numpy as np
import pytesseract
import easyocr
import PyPDF2
import pdf2image
from PIL import Image, ImageEnhance, ImageFilter
import io
import hashlib
import exifread
from datetime import datetime
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self, use_easyocr=True):
        """
        Initialize OCR processor with BOTH English and Hindi support for Indian documents
        
        Args:
            use_easyocr (bool): Whether to use EasyOCR (True) or Tesseract (False)
        """
        self.use_easyocr = use_easyocr
        self.reader = None
        self.tesseract_available = False
        
        if use_easyocr:
            # Initialize EasyOCR for English AND Hindi (critical for Indian documents)
            try:
                logger.info("Initializing EasyOCR with English and Hindi support...")
                self.reader = easyocr.Reader(['en', 'hi'], gpu=False, verbose=False)
                logger.info("✓ EasyOCR initialized successfully with English + Hindi")
            except Exception as e:
                logger.error(f"✗ EasyOCR initialization failed: {e}")
                logger.info("Falling back to Tesseract...")
                self.use_easyocr = False
        
        # Configure Tesseract as backup
        if not self.use_easyocr or True:  # Always configure Tesseract as backup
            try:
                if os.name == 'nt':
                    # Windows paths
                    possible_paths = [
                        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                        r'C:\Tesseract-OCR\tesseract.exe'
                    ]
                    for path in possible_paths:
                        if os.path.exists(path):
                            pytesseract.pytesseract.tesseract_cmd = path
                            self.tesseract_available = True
                            logger.info(f"✓ Tesseract found at: {path}")
                            break
                else:
                    # Linux/Mac - tesseract should be in PATH
                    self.tesseract_available = True
                
                if not self.tesseract_available:
                    logger.warning("✗ Tesseract not found. OCR may have limited functionality.")
            except Exception as e:
                logger.warning(f"Tesseract configuration error: {e}")
        
        logger.info(f"OCR Processor initialized: EasyOCR={'✓' if self.reader else '✗'}, Tesseract={'✓' if self.tesseract_available else '✗'}")
    
    def extract_text(self, file_path, file_type):
        """
        Extract text from document based on file type
        
        Args:
            file_path (str): Path to the file
            file_type (str): Type of file (image/pdf)
            
        Returns:
            dict: Extracted text and metadata
        """
        try:
            if file_type.lower() == 'pdf':
                return self._extract_from_pdf(file_path)
            else:
                return self._extract_from_image(file_path)
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return {"text": "", "confidence": 0, "error": str(e)}
    
    def _extract_from_pdf(self, file_path):
        """
        Extract text from PDF file
        
        Args:
            file_path (str): Path to PDF file
            
        Returns:
            dict: Extracted text and metadata
        """
        text = ""
        confidence = 0
        page_count = 0
        
        try:
            # First try to extract text directly from PDF
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
                
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        confidence += 0.7  # Higher confidence for direct text extraction
            
            # If little text was extracted, use OCR on rendered pages
            if len(text.strip()) < 100:
                text = ""
                confidence = 0
                images = pdf2image.convert_from_path(file_path, dpi=300)
                
                for i, image in enumerate(images):
                    img_path = f"{file_path}_page_{i}.png"
                    image.save(img_path, "PNG")
                    result = self._extract_from_image(img_path)
                    text += result.get("text", "") + "\n"
                    confidence += result.get("confidence", 0) * 0.8  # Slightly lower confidence for OCR
                    os.remove(img_path)
                
                if page_count > 0:
                    confidence /= page_count
        
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
        
        return {
            "text": text.strip(),
            "confidence": min(confidence, 1.0),
            "page_count": page_count
        }
    
    
    def _extract_from_image(self, file_path):
        """
        Extract text from image file using MULTIPLE methods for maximum accuracy
        IMPROVED VERSION: More lenient, better preprocessing, handles poor quality images
        
        Args:
            file_path (str): Path to image file
            
        Returns:
            dict: Extracted text and metadata
        """
        logger.info(f"="*70)
        logger.info(f"Starting IMPROVED OCR extraction from: {file_path}")
        logger.info(f"="*70)
        
        try:
            # Read original image
            original_img = cv2.imread(file_path)
            if original_img is None:
                logger.error(f"Failed to read image: {file_path}")
                return {"text": "", "confidence": 0, "error": "Cannot read image file", "method": "error"}
            
            logger.info(f"Image loaded successfully: {original_img.shape}")
            
            # Try MULTIPLE preprocessing methods and keep ALL results
            results = []
            
            # Method 1: Original image (no preprocessing)
            logger.info("Method 1: Original image (no preprocessing)...")
            result1 = self._try_ocr_extraction(original_img, "original")
            results.append(result1)
            logger.info(f"  → {len(result1['text'])} chars, {result1['confidence']:.2%} confidence")
            
            # Method 2: Grayscale only (simple and effective)
            logger.info("Method 2: Grayscale conversion...")
            gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
            result2 = self._try_ocr_extraction(gray, "grayscale")
            results.append(result2)
            logger.info(f"  → {len(result2['text'])} chars, {result2['confidence']:.2%} confidence")
            
            # Method 3: Adaptive Threshold (BEST for handwritten/varied lighting)
            logger.info("Method 3: Adaptive threshold (for handwritten/varied lighting)...")
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            result3 = self._try_ocr_extraction(adaptive, "adaptive_threshold")
            results.append(result3)
            logger.info(f"  → {len(result3['text'])} chars, {result3['confidence']:.2%} confidence")
            
            # Method 4: Otsu's thresholding (BEST for printed text with uniform background)
            logger.info("Method 4: Otsu threshold (for printed text)...")
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            result4 = self._try_ocr_extraction(otsu, "otsu_threshold")
            results.append(result4)
            logger.info(f"  → {len(result4['text'])} chars, {result4['confidence']:.2%} confidence")
            
            # Method 5: Denoised + Sharpened (for noisy images)
            logger.info("Method 5: Denoised + sharpened (for noisy images)...")
            try:
                denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                sharpened = cv2.filter2D(denoised, -1, kernel)
                result5 = self._try_ocr_extraction(sharpened, "denoised_sharpened")
                results.append(result5)
                logger.info(f"  → {len(result5['text'])} chars, {result5['confidence']:.2%} confidence")
            except Exception as e:
                logger.warning(f"  → Denoising failed: {e}")
            
            # Method 6: CLAHE (Contrast Limited Adaptive Histogram Equalization)
            logger.info("Method 6: CLAHE enhancement (for low contrast)...")
            try:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                enhanced = clahe.apply(gray)
                result6 = self._try_ocr_extraction(enhanced, "clahe_enhanced")
                results.append(result6)
                logger.info(f"  → {len(result6['text'])} chars, {result6['confidence']:.2%} confidence")
            except Exception as e:
                logger.warning(f"  → CLAHE failed: {e}")
            
            # Method 7: Morphological operations (for broken text)
            logger.info("Method 7: Morphological operations (for broken text)...")
            try:
                kernel = np.ones((2,2), np.uint8)
                morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
                result7 = self._try_ocr_extraction(morph, "morphological")
                results.append(result7)
                logger.info(f"  → {len(result7['text'])} chars, {result7['confidence']:.2%} confidence")
            except Exception as e:
                logger.warning(f"  → Morphological operations failed: {e}")
            
            # Method 8: Bilateral filter (preserves edges while reducing noise)
            logger.info("Method 8: Bilateral filter (edge-preserving denoising)...")
            try:
                bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
                result8 = self._try_ocr_extraction(bilateral, "bilateral_filter")
                results.append(result8)
                logger.info(f"  → {len(result8['text'])} chars, {result8['confidence']:.2%} confidence")
            except Exception as e:
                logger.warning(f"  → Bilateral filter failed: {e}")
            
            # Method 9: PIL enhancement (last resort for very poor images)
            logger.info("Method 9: PIL enhancement (aggressive enhancement)...")
            try:
                pil_img = Image.open(file_path)
                # Increase contrast aggressively
                enhancer = ImageEnhance.Contrast(pil_img)
                pil_enhanced = enhancer.enhance(3.0)
                # Increase sharpness
                enhancer = ImageEnhance.Sharpness(pil_enhanced)
                pil_enhanced = enhancer.enhance(2.5)
                # Increase brightness
                enhancer = ImageEnhance.Brightness(pil_enhanced)
                pil_enhanced = enhancer.enhance(1.5)
                # Convert to grayscale
                pil_enhanced = pil_enhanced.convert('L')
                # Convert to numpy array
                pil_array = np.array(pil_enhanced)
                result9 = self._try_ocr_extraction(pil_array, "pil_aggressive")
                results.append(result9)
                logger.info(f"  → {len(result9['text'])} chars, {result9['confidence']:.2%} confidence")
            except Exception as e:
                logger.warning(f"  → PIL enhancement failed: {e}")
            
            # Method 10: Inverted image (for white text on dark background)
            logger.info("Method 10: Inverted image (for white-on-dark text)...")
            try:
                inverted = cv2.bitwise_not(gray)
                result10 = self._try_ocr_extraction(inverted, "inverted")
                results.append(result10)
                logger.info(f"  → {len(result10['text'])} chars, {result10['confidence']:.2%} confidence")
            except Exception as e:
                logger.warning(f"  → Inversion failed: {e}")
            
            logger.info(f"\n{'='*70}")
            logger.info(f"EXTRACTION COMPLETE - Tested {len(results)} methods")
            logger.info(f"{'='*70}")
            
            # Choose the BEST result based on multiple factors
            # Priority: 1) Most text extracted, 2) Reasonable confidence
            valid_results = [r for r in results if len(r.get('text', '')) > 0]
            
            if not valid_results:
                logger.error("❌ ALL METHODS FAILED - No text extracted by any method")
                return {
                    "text": "",
                    "confidence": 0.0,
                    "word_count": 0,
                    "method": "all_failed",
                    "error": "All OCR methods failed to extract text. Image may be corrupted, too low quality, or not contain readable text."
                }
            
            # Sort by text length (more text is usually better)
            valid_results.sort(key=lambda x: len(x.get('text', '')), reverse=True)
            
            # Take top 3 results and choose best based on confidence
            top_results = valid_results[:3]
            best_result = max(top_results, key=lambda x: x.get('confidence', 0) * (1 + len(x.get('text', '')) / 1000))
            
            logger.info(f"\n🏆 BEST RESULT:")
            logger.info(f"   Method: {best_result['method']}")
            logger.info(f"   Text length: {len(best_result['text'])} characters")
            logger.info(f"   Word count: {best_result.get('word_count', 0)} words")
            logger.info(f"   Confidence: {best_result['confidence']:.2%}")
            logger.info(f"   Preview: {best_result['text'][:150]}...")
            logger.info(f"{'='*70}\n")
            
            return best_result
            
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR processing image {file_path}: {str(e)}", exc_info=True)
            return {
                "text": "",
                "confidence": 0.0,
                "word_count": 0,
                "method": "error",
                "error": str(e)
            }
    
    def _try_ocr_extraction(self, image, method_name):
        """
        Try OCR extraction with BOTH EasyOCR and Tesseract, return the best result
        IMPROVED VERSION: More aggressive, tries multiple configurations
        
        Args:
            image: Image array (numpy)
            method_name: Name of preprocessing method
            
        Returns:
            dict: Extraction result with text, confidence, and metadata
        """
        text = ""
        confidence = 0.0
        
        try:
            # Try EasyOCR first (better for handwritten and Hindi)
            if self.reader is not None:
                try:
                    # EasyOCR with multiple parameter combinations
                    results = self.reader.readtext(
                        image, 
                        detail=1, 
                        paragraph=False,
                        min_size=5,  # Detect smaller text
                        text_threshold=0.5,  # Lower threshold for detection
                        low_text=0.3,  # Lower threshold for text regions
                        link_threshold=0.3,  # Lower threshold for linking
                        canvas_size=2560,  # Larger canvas for better detection
                        mag_ratio=1.5  # Magnification ratio
                    )
                    
                    if results:
                        text_parts = []
                        confidences = []
                        
                        for detection in results:
                            bbox, detected_text, conf = detection
                            # Only include text with reasonable confidence
                            if conf > 0.2:  # Very low threshold
                                text_parts.append(detected_text)
                                confidences.append(conf)
                        
                        if text_parts:
                            text = " ".join(text_parts)
                            confidence = sum(confidences) / len(confidences) if confidences else 0.0
                            logger.debug(f"  EasyOCR ({method_name}): {len(text)} chars, {confidence:.2%} confidence")
                except Exception as e:
                    logger.debug(f"  EasyOCR failed for {method_name}: {e}")
            
            # If EasyOCR didn't work well, try Tesseract with MULTIPLE configurations
            if (len(text) < 20 or confidence < 0.4) and self.tesseract_available:
                try:
                    # Ensure image is in correct format for Tesseract
                    if len(image.shape) == 3:
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    
                    # Try MULTIPLE Tesseract configurations
                    configs = [
                        '--psm 6 --oem 3',  # Uniform block of text, LSTM engine
                        '--psm 3 --oem 3',  # Fully automatic, LSTM engine
                        '--psm 11 --oem 3', # Sparse text, LSTM engine
                        '--psm 6 --oem 1',  # Uniform block, Legacy engine
                        '--psm 4 --oem 3',  # Single column, LSTM engine
                        '--psm 1 --oem 3',  # Automatic with OSD, LSTM engine
                    ]
                    
                    best_tess_text = ""
                    best_tess_conf = 0.0
                    
                    for config in configs:
                        try:
                            # Extract text
                            tess_text = pytesseract.image_to_string(
                                image, 
                                config=config, 
                                lang='eng+hin'
                            ).strip()
                            
                            # Get confidence data
                            tess_data = pytesseract.image_to_data(
                                image, 
                                config=config, 
                                lang='eng+hin', 
                                output_type=pytesseract.Output.DICT
                            )
                            
                            # Calculate average confidence (only for valid detections)
                            confs = [
                                float(c) for c in tess_data['conf'] 
                                if str(c).replace('.','').replace('-','').isdigit() and float(c) > 0
                            ]
                            tess_conf = sum(confs) / len(confs) / 100.0 if confs else 0.0
                            
                            # Keep the result with most text
                            if len(tess_text) > len(best_tess_text):
                                best_tess_text = tess_text
                                best_tess_conf = tess_conf
                                logger.debug(f"  Tesseract config '{config}': {len(tess_text)} chars, {tess_conf:.2%} conf")
                        
                        except Exception as e:
                            logger.debug(f"  Tesseract config '{config}' failed: {e}")
                            continue
                    
                    # Use Tesseract result if it's better than EasyOCR
                    if len(best_tess_text) > len(text):
                        text = best_tess_text
                        confidence = best_tess_conf
                        logger.debug(f"  Using Tesseract result: {len(text)} chars, {confidence:.2%} confidence")
                
                except Exception as e:
                    logger.debug(f"  Tesseract processing failed for {method_name}: {e}")
            
            # Clean up the extracted text
            text = text.strip()
            
            # Calculate word count
            word_count = len(text.split()) if text else 0
            
            return {
                "text": text,
                "confidence": confidence,
                "word_count": word_count,
                "method": method_name
            }
            
        except Exception as e:
            logger.error(f"  OCR extraction error for {method_name}: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "word_count": 0,
                "method": method_name,
                "error": str(e)
            }
    
    def _preprocess_image(self, file_path):
        """
        Preprocess image to improve OCR accuracy
        
        Args:
            file_path (str): Path to image file
            
        Returns:
            numpy.array: Preprocessed image
        """
        try:
            # Read image
            image = cv2.imread(file_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply threshold to get binary image
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Apply dilation and erosion to remove noise
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            processed = cv2.medianBlur(processed, 3)
            
            return processed
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}, using original image")
            return cv2.imread(file_path)
    
    def extract_specific_fields(self, text, field_types):
        """
        Extract specific fields from OCR text using regex patterns
        
        Args:
            text (str): Extracted text
            field_types (list): List of field types to extract
            
        Returns:
            dict: Extracted field values
        """
        patterns = {
            'aadhar': [
                r'\b\d{4}\s\d{4}\s\d{4}\b',  # Standard Aadhar format
                r'\b\d{12}\b'  # 12 consecutive digits
            ],
            'pan': [
                r'[A-Z]{5}[0-9]{4}[A-Z]{1}'  # Standard PAN format
            ],
            'date': [
                r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
                r'\b\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s\d{2,4}\b'
            ],
            'amount': [
                r'₹\s?\d+(?:,\d{3})*(?:\.\d{2})?',
                r'Rs\.?\s?\d+(?:,\d{3})*(?:\.\d{2})?',
                r'\b\d+(?:,\d{3})*(?:\.\d{2})?\b'
            ],
            'policy_number': [
                r'[Pp]olicy\s*[Nn]o\.?\s*[:]?\s*[A-Z0-9-]+',
                r'[Pp]olicy\s*[:]?\s*[A-Z0-9-]+',
                r'\b[A-Z]{2,3}\d{6,10}\b'
            ]
        }
        
        results = {}
        for field in field_types:
            if field in patterns:
                for pattern in patterns[field]:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        results[field] = matches
                        break
        
        return results

# Singleton instance
ocr_processor = OCRProcessor()
