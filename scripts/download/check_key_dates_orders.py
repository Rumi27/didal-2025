#!/usr/bin/env python3
"""
Check and download orders for key dates.
"""

import os
import sys

# Order IDs
BEFORE_ORDER_ID = "e3580eef-b181-43e3-b6a8-8152c6aaed9f"  # Sept 4
OCT25_ORDER_ID = "f0aab7bd-5f1c-49dd-95ba-ec61d5cad88b"   # Oct 25

# Import the check script
sys.path.insert(0, os.path.dirname(__file__))

# Update the check script to use these order IDs
ORDER_ID = sys.argv[1] if len(sys.argv) > 1 else None

if ORDER_ID:
    # Check specific order
    exec(open('check_and_download_order.py').read().replace('ORDER_ID = "fee2882b-798b-4b20-9239-ec9fbc072acd"', f'ORDER_ID = "{ORDER_ID}"'))
else:
    # Check both orders
    print("=" * 70)
    print("Check Orders for Key Dates")
    print("=" * 70)
    print()
    print("Order 1: Before Initial Movement (Sept 4)")
    print(f"  Order ID: {BEFORE_ORDER_ID}")
    print()
    print("Order 2: Second Movement (Oct 25)")
    print(f"  Order ID: {OCT25_ORDER_ID}")
    print()
    print("Checking orders...")
    print()
    
    # Check first order
    import subprocess
    result1 = subprocess.run(
        ['python3', 'check_and_download_order.py', BEFORE_ORDER_ID],
        capture_output=True,
        text=True
    )
    print(result1.stdout)
    if result1.stderr:
        print(result1.stderr)
    
    print()
    print("-" * 70)
    print()
    
    # Check second order
    result2 = subprocess.run(
        ['python3', 'check_and_download_order.py', OCT25_ORDER_ID],
        capture_output=True,
        text=True
    )
    print(result2.stdout)
    if result2.stderr:
        print(result2.stderr)

