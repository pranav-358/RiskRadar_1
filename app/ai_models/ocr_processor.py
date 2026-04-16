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
        
        Args:
            file_path (str): Path to image file
            
        Returns:
            dict: Extracted text and metadata
        """
        logger.info(f"Starting OCR extraction from: {file_path}")
        
        try:
            # Read original image
            original_img = cv2.imread(file_path)
            if original_img is None:
                logger.error(f"Failed to read image: {file_path}")
                return {"text": "", "confidence": 0, "error": "Cannot read image file"}
            
            logger.info(f"Image loaded: {original_img.shape}")
            
            # Try MULTIPLE preprocessing methods and keep the best result
            results = []
            
            # Method 1: Original image with EasyOCR
            logger.info("Method 1: Processing original image...")
            result1 = self._try_ocr_extraction(original_img, "original")
            results.append(result1)
            logger.info(f"Method 1 result: {len(result1['text'])} chars, confidence: {result1['confidence']:.2%}")
            
            # Method 2: Grayscale + Adaptive Threshold (BEST for handwritten)
            logger.info("Method 2: Adaptive threshold (for handwritten)...")
            gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            result2 = self._try_ocr_extraction(adaptive, "adaptive_threshold")
            results.append(result2)
            logger.info(f"Method 2 result: {len(result2['text'])} chars, confidence: {result2['confidence']:.2%}")
            
            # Method 3: Otsu's thresholding (BEST for printed text)
            logger.info("Method 3: Otsu threshold (for printed text)...")
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            result3 = self._try_ocr_extraction(otsu, "otsu_threshold")
            results.append(result3)
            logger.info(f"Method 3 result: {len(result3['text'])} chars, confidence: {result3['confidence']:.2%}")
            
            # Method 4: Denoised + Sharpened
            logger.info("Method 4: Denoised + sharpened...")
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            result4 = self._try_ocr_extraction(sharpened, "denoised_sharpened")
            results.append(result4)
            logger.info(f"Method 4 result: {len(result4['text'])} chars, confidence: {result4['confidence']:.2%}")
            
            # Method 5: Contrast enhancement + Morphological operations
            logger.info("Method 5: Enhanced contrast + morphology...")
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            kernel = np.ones((2,2), np.uint8)
            morph = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
            result5 = self._try_ocr_extraction(morph, "enhanced_morph")
            results.append(result5)
            logger.info(f"Method 5 result: {len(result5['text'])} chars, confidence: {result5['confidence']:.2%}")
            
            # Method 6: PIL enhancement (last resort)
            logger.info("Method 6: PIL enhancement...")
            try:
                pil_img = Image.open(file_path)
                # Increase contrast
                enhancer = ImageEnhance.Contrast(pil_img)
                pil_enhanced = enhancer.enhance(2.5)
                # Increase sharpness
                enhancer = ImageEnhance.Sharpness(pil_enhanced)
                pil_enhanced = enhancer.enhance(2.0)
                # Convert to grayscale
                pil_enhanced = pil_enhanced.convert('L')
                # Convert to numpy array
                pil_array = np.array(pil_enhanced)
                result6 = self._try_ocr_extraction(pil_array, "pil_enhanced")
                results.append(result6)
                logger.info(f"Method 6 result: {len(result6['text'])} chars, confidence: {result6['confidence']:.2%}")
            except Exception as e:
                logger.warning(f"PIL enhancement failed: {e}")
            
            # Choose the BEST result (most text extracted with reasonable confidence)
            best_result = max(results, key=lambda x: len(x.get('text', '')) * (x.get('confidence', 0) + 0.1))
            
            logger.info(f"BEST RESULT: {best_result['method']} - {len(best_result['text'])} chars, {best_result['confidence']:.2%} confidence")
            logger.info(f"Extracted text preview: {best_result['text'][:100]}...")
            
            return best_result
            
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {str(e)}", exc_info=True)
            return {"text": "", "confidence": 0, "error": str(e), "method": "error"}
    
    def _try_ocr_extraction(self, image, method_name):
        """
        Try OCR extraction with both EasyOCR and Tesseract
        
        Args:
            image: Image array (numpy)
            method_name: Name of preprocessing method
            
        Returns:
            dict: Extraction result
        """
        text = ""
        confidence = 0.0
        
        try:
            # Try EasyOCR first (better for handwritten and Hindi)
            if self.reader is not None:
                try:
                    results = self.reader.readtext(image, detail=1, paragraph=False)
                    
                    if results:
                        text_parts = []
                        confidences = []
                        
                        for detection in results:
                            bbox, detected_text, conf = detection
                            text_parts.append(detected_text)
                            confidences.append(conf)
                        
                        text = " ".join(text_parts)
                        confidence = sum(confidences) / len(confidences) if confidences else 0.0
                        
                        logger.debug(f"EasyOCR ({method_name}): {len(text)} chars, {confidence:.2%} confidence")
                except Exception as e:
                    logger.warning(f"EasyOCR failed for {method_name}: {e}")
            
            # If EasyOCR didn't work or got poor results, try Tesseract
            if (len(text) < 10 or confidence < 0.3) and self.tesseract_available:
                try:
                    # Ensure image is in correct format for Tesseract
                    if len(image.shape) == 3:
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    
                    # Try with different Tesseract configs
                    configs = [
                        '--psm 6',  # Assume uniform block of text
                        '--psm 3',  # Fully automatic page segmentation
                        '--psm 11', # Sparse text
                    ]
                    
                    best_text = ""
                    best_conf = 0.0
                    
                    for config in configs:
                        try:
                            tess_text = pytesseract.image_to_string(image, config=config, lang='eng+hin')
                            tess_data = pytesseract.image_to_data(image, config=config, lang='eng+hin', output_type=pytesseract.Output.DICT)
                            
                            # Calculate average confidence
                            confs = [float(c) for c in tess_data['conf'] if str(c).replace('.','').replace('-','').isdigit() and float(c) > 0]
                            tess_conf = sum(confs) / len(confs) / 100.0 if confs else 0.0
                            
                            if len(tess_text) > len(best_text):
                                best_text = tess_text
                                best_conf = tess_conf
                        except Exception as e:
                            logger.debug(f"Tesseract config {config} failed: {e}")
                            continue
                    
                    # Use Tesseract result if better than EasyOCR
                    if len(best_text) > len(text):
                        text = best_text
                        confidence = best_conf
                        logger.debug(f"Tesseract ({method_name}): {len(text)} chars, {confidence:.2%} confidence")
                
                except Exception as e:
                    logger.warning(f"Tesseract failed for {method_name}: {e}")
            
        except Exception as e:
            logger.error(f"OCR extraction error for {method_name}: {e}")
        
        return {
            "text": text.strip(),
            "confidence": confidence,
            "word_count": len(text.split()),
            "method": method_name
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
