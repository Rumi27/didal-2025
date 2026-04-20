#!/usr/bin/env python3
"""
Check detailed error information for failed order.
"""

import os
import requests
import json

ORDER_ID = "1ed55f0f-79cf-4ab7-9c6b-9fb8bcbb6c88"
API_KEY = os.environ.get("PL_API_KEY", "PLAK97848b681d244728a5a7a02e73eb23d5")

url = f"https://api.planet.com/compute/ops/orders/v2/{ORDER_ID}"
resp = requests.get(url, auth=(API_KEY, ""))
data = resp.json()

print("=" * 70)
print("Full Order Response")
print("=" * 70)
print()
print(json.dumps(data, indent=2, default=str))
print()

# Check for error hints
if "error_hints" in data:
    print("Error hints:")
    for hint in data["error_hints"]:
        print(f"  - {hint}")

# Check last message
if "last_message" in data:
    print(f"\nLast message: {data['last_message']}")


