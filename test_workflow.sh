#!/bin/bash

echo "🚀 Starting Workflow Tests..."

# Test 1: Health Check
echo -e "\n1️⃣ Health Check"
curl -s http://localhost:8000/health | jq

# Test 2: Start Workflow
echo -e "\n2️⃣ Starting Workflow"
RESPONSE=$(curl -s -X POST http://localhost:8000/workflow/start \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "AUTO001",
    "amount": 299.99,
    "items": ["laptop", "mouse"]
  }')
echo $RESPONSE | jq
INSTANCE_ID=$(echo $RESPONSE | jq -r '.instance_id')

# Test 3: Check Initial Status
echo -e "\n3️⃣ Checking Initial Status"
curl -s http://localhost:8000/workflow/status/$INSTANCE_ID | jq '.runtime_status'

# Test 4: Wait for Completion
echo -e "\n4️⃣ Waiting 5 seconds for completion..."
sleep 5

# Test 5: Check Final Status
echo -e "\n5️⃣ Checking Final Status"
curl -s http://localhost:8000/workflow/status/$INSTANCE_ID | jq

echo -e "\n✅ Tests Complete!"