"""
Validation script to check your implementation against the reference.

⚠️  IMPORTANT: Complete your own implementation in naive_model/ BEFORE running this.
⚠️  Do NOT copy code from the reference - implement everything yourself.

Run this after completing naive_model/ to verify correctness.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from baseline.merton_reference import merton_model as reference_merton
from naive_model.calibration import calibrate_asset_parameters
from naive_model.risk_measures import compute_risk_measures


def test_single_calibration():
    """Test calibration on a single point."""
    print("Testing single-point calibration...")
    print("-" * 60)
    
    # Test case
    E = 100.0
    sigma_E = 0.30
    D = 80.0
    T = 1.0
    r = 0.05
    
    # Reference result
    ref_result = reference_merton(E, sigma_E, D, T, r)
    
    # Your implementation
    try:
        V, sigma_V = calibrate_asset_parameters(E, sigma_E, D, T, r)
        risk = compute_risk_measures(V, D, T, r, sigma_V)
        
        # Compare
        print(f"Reference vs Your Implementation:")
        print(f"  V:      {ref_result['V']:8.2f} vs {V:8.2f} (diff: {abs(V - ref_result['V']):.2f})")
        print(f"  σ_V:    {ref_result['sigma_V']:8.4f} vs {sigma_V:8.4f} (diff: {abs(sigma_V - ref_result['sigma_V']):.4f})")
        print(f"  DD:     {ref_result['DD']:8.4f} vs {risk['DD']:8.4f} (diff: {abs(risk['DD'] - ref_result['DD']):.4f})")
        print(f"  PD:     {ref_result['PD']:8.4f} vs {risk['PD']:8.4f} (diff: {abs(risk['PD'] - ref_result['PD']):.4f})")
        
        # Check if close (within 1% for V, 5% for others)
        v_ok = abs(V - ref_result['V']) / ref_result['V'] < 0.01
        sigma_ok = abs(sigma_V - ref_result['sigma_V']) / ref_result['sigma_V'] < 0.05
        dd_ok = abs(risk['DD'] - ref_result['DD']) < 0.1
        pd_ok = abs(risk['PD'] - ref_result['PD']) < 0.01
        
        if v_ok and sigma_ok and dd_ok and pd_ok:
            print("\n✅ PASS: Results match reference (within tolerance)")
            return True
        else:
            print("\n❌ FAIL: Results differ significantly from reference")
            if not v_ok:
                print("   - V is off")
            if not sigma_ok:
                print("   - sigma_V is off")
            if not dd_ok:
                print("   - DD is off")
            if not pd_ok:
                print("   - PD is off")
            return False
            
    except NotImplementedError as e:
        print(f"\n❌ FAIL: {e}")
        print("   Complete the implementation first!")
        return False
    except Exception as e:
        print(f"\n❌ FAIL: Error during execution: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_cases():
    """Test on multiple cases with different parameters."""
    print("\n\nTesting multiple cases...")
    print("-" * 60)
    
    test_cases = [
        {'E': 100.0, 'sigma_E': 0.30, 'D': 80.0, 'T': 1.0, 'r': 0.05},
        {'E': 50.0, 'sigma_E': 0.40, 'D': 60.0, 'T': 1.0, 'r': 0.03},
        {'E': 200.0, 'sigma_E': 0.20, 'D': 100.0, 'T': 1.0, 'r': 0.05},
    ]
    
    passed = 0
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest case {i}: E={case['E']}, σ_E={case['sigma_E']}, D={case['D']}")
        try:
            ref = reference_merton(**case)
            V, sigma_V = calibrate_asset_parameters(**case)
            risk = compute_risk_measures(V, case['D'], case['T'], case['r'], sigma_V)
            
            v_diff = abs(V - ref['V']) / ref['V']
            if v_diff < 0.01:
                print(f"  ✅ V matches (diff: {v_diff:.2%})")
                passed += 1
            else:
                print(f"  ❌ V differs (diff: {v_diff:.2%})")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\nPassed {passed}/{len(test_cases)} test cases")
    return passed == len(test_cases)


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Implementation Validation")
    print("=" * 60)
    
    test1 = test_single_calibration()
    test2 = test_multiple_cases()
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✅ ALL TESTS PASSED")
        print("Your implementation appears correct!")
    else:
        print("❌ SOME TESTS FAILED")
        print("Review your implementation and compare with baseline/merton_reference.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

