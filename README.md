# Dapr FastAPI Workflow Project

This project demonstrates a Dapr workflow with FastAPI that includes:
- **2 parallel activities**: `process_order` and `check_inventory` (run simultaneously)
- **1 sequential activity**: `send_confirmation` (runs after parallel activities complete)
- **Full Dapr Workflow SDK** with scheduler support
- **Workflow management**: Pause, resume, and terminate capabilities

## Architecture

```
Workflow Start
     |
     ├─── Activity 1: process_order (2s) ────┐
     |                                        ├─── Activity 3: send_confirmation (1s)
     └─── Activity 2: check_inventory (2s) ──┘
                                              |
                                         Workflow End
                                         
Total Execution Time: ~5 seconds (2s parallel + 1s sequential + overhead)
```

## Prerequisites

### 1. Install Dapr CLI
```bash
# macOS/Linux
wget -q https://raw.githubusercontent.com/dapr/cli/master/install/install.sh -O - | /bin/bash

# Windows (PowerShell)
powershell -Command "iwr -useb https://raw.githubusercontent.com/dapr/cli/master/install/install.ps1 | iex"
```

### 2. Initialize Dapr
```bash
dapr init
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Dapr Components
After `dapr init`, check that containers are running:
```bash
docker ps --filter "name=dapr_"
```
You should see `dapr_scheduler`, `dapr_redis`, and other Dapr containers running.

## Project Structure

```
dapr-workflow-demo/
├── app/
│   ├── __init__.py
│   └── main.py                  # FastAPI app + Dapr workflow logic
│
├── components/
│   └── dapr-component.yaml            # Dapr Workflow engine component
│                  
├── requirements.txt             # Python dependencies
├── README.md                    # Setup, run, trigger workflow
└── .gitignore

```

## Running the Application

### ✅ Simple Setup

After running `dapr init`, the scheduler and Redis are **already running** in Docker containers. You only need to start your application:

```bash
dapr run \
  --app-id workflow-app \
  --app-port 8000 \
  --resources-path ./components \
  -- python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

```

**Expected Output:**
```
✅ You're up and running! Both Dapr and your app logs will appear here.
INFO: Started server process
🔧 Registering workflows and activities...
🚀 Starting Dapr Workflow Runtime...
✅ Workflow Runtime started successfully
INFO: Application startup complete.
```

### 🔍 Verify Dapr Components are Running

Check that `dapr init` started the necessary containers:

```bash
docker ps --filter "name=dapr_"
```

**You should see:**
```
CONTAINER ID   IMAGE               PORTS                    NAMES
xxxxx          daprio/dapr        127.0.0.1:50006->50006   dapr_scheduler
xxxxx          redis:6            127.0.0.1:6379->6379     dapr_redis
xxxxx          openzipkin/zipkin  127.0.0.1:9411->9411     dapr_zipkin
```

✅ **Scheduler** is running on port `50006`  
✅ **Redis** is running on port `6379`  
✅ **No manual startup needed!**


## Testing the Workflow

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "workflow_runtime": "running"
}
```

### 2. Start a Workflow
```bash
curl -X POST http://localhost:8000/workflow/start \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORDER001",
    "amount": 99.99,
    "items": ["laptop", "mouse"]
  }'
```

**Response:**
```json
{
  "status": "started",
  "instance_id": "order_ORDER001",
  "order_data": {
    "order_id": "ORDER001",
    "amount": 99.99,
    "items": ["laptop", "mouse"]
  },
  "message": "Workflow is executing. Use /workflow/status/{instance_id} to check progress"
}
```

### 3. Check Workflow Status
```bash
# Check immediately (will show RUNNING)
curl http://localhost:8000/workflow/status/order_ORDER001

# Wait 5 seconds, then check again (will show COMPLETED)
sleep 5
curl http://localhost:8000/workflow/status/order_ORDER001
```

**Response (Completed):**
```json
{
  "instance_id": "order_ORDER001",
  "runtime_status": "WorkflowStatus.COMPLETED",
  "created_at": "2026-01-11T12:00:00Z",
  "last_updated": "2026-01-11T12:00:05Z",
  "output": {
    "workflow_status": "completed",
    "order_id": "ORDER001",
    "process_result": {
      "order_id": "ORDER001",
      "status": "processed",
      "total": 109.989,
      "processed_at": 1736596800.123
    },
    "inventory_result": {
      "order_id": "ORDER001",
      "inventory_status": "available",
      "items_count": 2,
      "checked_at": 1736596800.456
    },
    "confirmation": {
      "confirmation_sent": true,
      "order_id": "ORDER001",
      "message": "Order confirmed with 2 items. Total: $109.99",
      "confirmed_at": 1736596803.789
    },
    "execution_summary": {
      "parallel_activities": ["process_order", "check_inventory"],
      "sequential_activities": ["send_confirmation"],
      "total_activities": 3
    }
  }
}
```

## Advanced Operations

### Pause a Workflow
```bash
curl -X POST http://localhost:8000/workflow/pause/order_ORDER001
```

### Resume a Workflow
```bash
curl -X POST http://localhost:8000/workflow/resume/order_ORDER001
```

### Terminate a Workflow
```bash
curl -X POST http://localhost:8000/workflow/terminate/order_ORDER001
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Get application info |
| GET | `/health` | Health check |
| POST | `/workflow/start` | Start a new workflow |
| GET | `/workflow/status/{instance_id}` | Get workflow status |
| POST | `/workflow/pause/{instance_id}` | Pause a running workflow |
| POST | `/workflow/resume/{instance_id}` | Resume a paused workflow |
| POST | `/workflow/terminate/{instance_id}` | Terminate a workflow |

## Understanding the Workflow Execution

When you start a workflow, you'll see these logs in the Terminal:

```
🚀 Starting workflow for order: ORDER001
⚡ Launching parallel activities...
[Activity 1 - PARALLEL] Processing order: {...}
[Activity 2 - PARALLEL] Checking inventory for order: {...}
✅ Parallel activities completed
   - Process result: {...}
   - Inventory result: {...}
📧 Running sequential confirmation activity...
[Activity 3 - SEQUENTIAL] Sending confirmation with data: {...}
✅ Workflow completed for order: ORDER001
```

**Key Points:**
- Activities 1 & 2 start **simultaneously** (PARALLEL execution)
- Both take ~2 seconds but run at the same time
- Activity 3 runs **only after** both parallel activities complete (SEQUENTIAL execution)
- Total time: ~5 seconds instead of ~7 seconds (if all were sequential)

## Workflow States

| State | Description |
|-------|-------------|
| `RUNNING` | Workflow is currently executing |
| `COMPLETED` | Workflow finished successfully |
| `FAILED` | Workflow encountered an error |
| `TERMINATED` | Workflow was manually terminated |
| `SUSPENDED` | Workflow is paused |

## Testing Scenarios

### Scenario 1: Complete Lifecycle
```bash
# Start workflow
curl -X POST http://localhost:8000/workflow/start \
  -H "Content-Type: application/json" \
  -d '{"order_id":"TEST001","amount":150.00,"items":["item1","item2"]}'

# Check status (RUNNING)
curl http://localhost:8000/workflow/status/order_TEST001

# Wait 5 seconds
sleep 5

# Check status (COMPLETED)
curl http://localhost:8000/workflow/status/order_TEST001
```

### Scenario 2: Pause and Resume
```bash
# Start workflow
curl -X POST http://localhost:8000/workflow/start \
  -H "Content-Type: application/json" \
  -d '{"order_id":"TEST002","amount":200.00,"items":["monitor"]}'

# Pause immediately
curl -X POST http://localhost:8000/workflow/pause/order_TEST002

# Resume after 10 seconds
sleep 10
curl -X POST http://localhost:8000/workflow/resume/order_TEST002
```

### Scenario 3: Multiple Concurrent Workflows
```bash
# Start 5 workflows simultaneously
for i in {1..5}; do
  curl -X POST http://localhost:8000/workflow/start \
    -H "Content-Type: application/json" \
    -d "{\"order_id\":\"BATCH00$i\",\"amount\":$((i*100)),\"items\":[\"item$i\"]}" &
done

# Wait for all to complete
wait

# Check all statuses
for i in {1..5}; do
  echo "Status for BATCH00$i:"
  curl http://localhost:8000/workflow/status/order_BATCH00$i | jq
done
```

## Interactive API Documentation

Once your application is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You can test all endpoints interactively through the Swagger UI.

## Production Deployment

For production deployment with Docker and Kubernetes, see:
- **Docker Compose**: `docker-compose.yml` (in artifacts)
- **Kubernetes**: `deployment.yaml` (in artifacts)
- **Full Guide**: `PRODUCTION_SETUP.md` (in artifacts)

## Features

✅ **Parallel Execution**: Activities 1 & 2 run simultaneously  
✅ **Sequential Execution**: Activity 3 runs after parallel activities  
✅ **Durable Workflows**: Survives application restarts  
✅ **Workflow Management**: Pause, resume, terminate  
✅ **Production Ready**: Full error handling and logging  
✅ **REST API**: Clean FastAPI endpoints  
✅ **Interactive Docs**: Built-in Swagger UI  

## Key Technologies

- **FastAPI**: Modern Python web framework
- **Dapr**: Distributed application runtime
- **Dapr Workflows**: Durable workflow orchestration
- **Pydantic**: Data validation

## Performance

- **Parallel Activities**: 2 seconds (both run simultaneously)
- **Sequential Activity**: 1 second
- **Total Execution Time**: ~5 seconds
- **If Sequential Only**: Would take ~7 seconds (2+2+1+overhead)
- **Performance Gain**: ~30% faster with parallelization

## Stopping the Application

1. Stop the application: Press `Ctrl+C` in the terminal
2. (Optional) Stop Dapr containers:
   ```bash
   docker stop dapr_scheduler dapr_redis dapr_zipkin dapr_placement
   ```
3. (Optional) Completely remove Dapr:
   ```bash
   dapr uninstall
   ```

## Additional Resources

- [Dapr Workflows Documentation](https://docs.dapr.io/developing-applications/building-blocks/workflow/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Dapr Python SDK](https://github.com/dapr/python-sdk)


**Built with ❤️ using Dapr and FastAPI**