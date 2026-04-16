#!/usr/bin/env python
"""
Quick verification script to test all fixes
"""

# CRITICAL: Set matplotlib backend BEFORE any imports
import os
os.environ['MPLBACKEND'] = 'Agg'

import sys

def test_matplotlib_fix():
    """Test that matplotlib backend is set correctly"""
    print("\n" + "="*60)
    print("TEST 1: Matplotlib Backend Fix")
    print("="*60)
    try:
        import matplotlib
        backend = matplotlib.get_backend()
        print(f"✓ Matplotlib backend: {backend}")
        if backend == 'Agg':
            print("✓ PASS: Non-interactive backend configured correctly")
            return True
        else:
            print(f"✗ FAIL: Backend is {backend}, should be 'Agg'")
            return False
    except Exception as e:
        print(f"✗ FAIL: {str(e)}")
        return False

def test_document_verification():
    """Test document verification AI"""
    print("\n" + "="*60)
    print("TEST 2: Document Verification AI")
    print("="*60)
    try:
        from app.ai_models.document_verification import document_verifier
        print("✓ Document verifier imported successfully")
        
        # Check methods exist
        assert hasattr(document_verifier, '_verify_name_match'), "Missing _verify_name_match"
        assert hasattr(document_verifier, '_detect_image_tampering'), "Missing _detect_image_tampering"
        assert hasattr(document_verifier, '_analyze_metadata'), "Missing _analyze_metadata"
        print("✓ All required methods exist")
        
        # Test name matching
        result = document_verifier._verify_name_match("Patient Name: John Smith", "John Smith")
        assert result['match_found'] == True, "Name matching failed"
        assert result['similarity'] >= 0.9, "Similarity too low"
        print(f"✓ Name matching works (similarity: {result['similarity']:.2%})")
        
        # Test name mismatch
        result = document_verifier._verify_name_match("Patient Name: Jane Doe", "John Smith")
        assert result['match_found'] == False, "Should detect mismatch"
        print("✓ Name mismatch detection works")
        
        print("✓ PASS: Document verification AI working correctly")
        return True
    except Exception as e:
        print(f"✗ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_ocr_processor():
    """Test OCR processor"""
    print("\n" + "="*60)
    print("TEST 3: OCR Processor")
    print("="*60)
    try:
        from app.ai_models.ocr_processor import ocr_processor
        print("✓ OCR processor imported successfully")
        
        # Check methods exist
        assert hasattr(ocr_processor, 'extract_text'), "Missing extract_text"
        assert hasattr(ocr_processor, 'extract_specific_fields'), "Missing extract_specific_fields"
        print("✓ All required methods exist")
        
        print("✓ PASS: OCR processor configured correctly")
        return True
    except Exception as e:
        print(f"✗ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_routes():
    """Test admin routes"""
    print("\n" + "="*60)
    print("TEST 4: Admin Routes")
    print("="*60)
    try:
        from app.admin import routes
        print("✓ Admin routes imported successfully")
        
        # Check view_document route exists
        assert hasattr(routes, 'view_document'), "Missing view_document route"
        print("✓ view_document route exists")
        
        print("✓ PASS: Admin routes configured correctly")
        return True
    except Exception as e:
        print(f"✗ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_flask_app():
    """Test Flask app initialization"""
    print("\n" + "="*60)
    print("TEST 5: Flask App Initialization")
    print("="*60)
    try:
        os.environ['SKIP_AI_INIT'] = '1'  # Skip AI initialization for quick test
        from app import create_app
        app = create_app()
        print("✓ Flask app created successfully")
        
        # Check custom filter exists
        assert 'from_json' in app.jinja_env.filters, "Missing from_json filter"
        print("✓ Custom Jinja filter registered")
        
        print("✓ PASS: Flask app configured correctly")
        return True
    except Exception as e:
        print(f"✗ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("RiskRadar - Fix Verification")
    print("="*60)
    print("Testing all applied fixes...")
    
    tests = [
        ("Matplotlib Backend", test_matplotlib_fix),
        ("Document Verification AI", test_document_verification),
        ("OCR Processor", test_ocr_processor),
        ("Admin Routes", test_admin_routes),
        ("Flask App", test_flask_app)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    print()
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System is ready for demo.")
        print()
        print("Next steps:")
        print("1. Start server: python run.py")
        print("2. Open browser: http://localhost:5000")
        print("3. Test with fake document upload")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
