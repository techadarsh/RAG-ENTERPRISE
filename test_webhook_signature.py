#!/usr/bin/env python3
"""
Test script for Confluence webhook with signature validation
"""
import hmac
import hashlib
import json
import requests

# Webhook secret (should match CONFLUENCE_WEBHOOK_SECRET in .env.local)
WEBHOOK_SECRET = "test-secret-key-12345"

# Webhook payload
payload = {
    "event": "page_updated",
    "page": {
        "id": "98317",
        "title": "Confluence API Integration - TEST",
        "url": "http://localhost:8090/wiki/spaces/ENG/pages/98317"
    }
}

# Convert to JSON bytes
payload_bytes = json.dumps(payload).encode('utf-8')

# Compute HMAC-SHA256 signature
signature = hmac.new(
    WEBHOOK_SECRET.encode('utf-8'),
    payload_bytes,
    hashlib.sha256
).hexdigest()

print(f"📝 Payload: {json.dumps(payload, indent=2)}")
print(f"🔐 Signature: {signature}")
print()

# Test 1: WITH valid signature
print("=" * 60)
print("TEST 1: Webhook WITH valid signature")
print("=" * 60)
response = requests.post(
    "http://localhost:8000/api/webhook/confluence",
    headers={
        "Content-Type": "application/json",
        "X-Atlassian-Webhook-Signature": signature
    },
    data=payload_bytes
)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
print()

# Test 2: WITHOUT signature (should fail)
print("=" * 60)
print("TEST 2: Webhook WITHOUT signature (should be rejected)")
print("=" * 60)
response = requests.post(
    "http://localhost:8000/api/webhook/confluence",
    headers={"Content-Type": "application/json"},
    json=payload
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
print()

# Test 3: WITH invalid signature (should fail)
print("=" * 60)
print("TEST 3: Webhook WITH invalid signature (should be rejected)")
print("=" * 60)
response = requests.post(
    "http://localhost:8000/api/webhook/confluence",
    headers={
        "Content-Type": "application/json",
        "X-Atlassian-Webhook-Signature": "invalid-signature-12345"
    },
    json=payload
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
