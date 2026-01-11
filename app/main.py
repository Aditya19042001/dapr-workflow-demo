from fastapi import FastAPI, HTTPException
from dapr.ext.workflow import WorkflowRuntime, DaprWorkflowContext, WorkflowActivityContext
from dapr.clients import DaprClient
import asyncio
import logging
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Workflow Activities
def process_order_activity(ctx: WorkflowActivityContext, order_data: dict) -> dict:
    """Activity 1: Process the order"""
    logger.info(f"[Activity 1 - PARALLEL] Processing order: {order_data}")
    import time
    time.sleep(2)  # Simulate processing
    order_id = order_data.get("order_id")
    return {
        "order_id": order_id,
        "status": "processed",
        "total": order_data.get("amount", 0) * 1.1,
        "processed_at": time.time()
    }

def check_inventory_activity(ctx: WorkflowActivityContext, order_data: dict) -> dict:
    """Activity 2: Check inventory (runs in parallel with process_order)"""
    logger.info(f"[Activity 2 - PARALLEL] Checking inventory for order: {order_data}")
    import time
    time.sleep(2)  # Simulate inventory check
    items = order_data.get("items", [])
    return {
        "order_id": order_data.get("order_id"),
        "inventory_status": "available",
        "items_count": len(items),
        "checked_at": time.time()
    }

def send_confirmation_activity(ctx: WorkflowActivityContext, combined_data: dict) -> dict:
    """Activity 3: Send confirmation (runs after parallel activities complete)"""
    logger.info(f"[Activity 3 - SEQUENTIAL] Sending confirmation with data: {combined_data}")
    import time
    time.sleep(1)  # Simulate sending
    return {
        "confirmation_sent": True,
        "order_id": combined_data.get("order_id"),
        "message": f"Order confirmed with {combined_data.get('items_count', 0)} items. Total: ${combined_data.get('total', 0):.2f}",
        "confirmed_at": time.time()
    }

# Workflow Definition
def order_processing_workflow(ctx: DaprWorkflowContext, order_input: dict) -> dict:
    """
    Production Workflow:
    1. Runs process_order and check_inventory in PARALLEL
    2. Runs send_confirmation SEQUENTIALLY after both complete
    """
    logger.info(f"🚀 Starting workflow for order: {order_input.get('order_id')}")
    
    # PARALLEL EXECUTION: Both activities run simultaneously
    logger.info("⚡ Launching parallel activities...")
    process_task = ctx.call_activity(process_order_activity, input=order_input)
    inventory_task = ctx.call_activity(check_inventory_activity, input=order_input)
    
    # Wait for both parallel activities to complete
    process_result = yield process_task
    inventory_result = yield inventory_task
    
    logger.info(f"✅ Parallel activities completed")
    logger.info(f"   - Process result: {process_result}")
    logger.info(f"   - Inventory result: {inventory_result}")
    
    # SEQUENTIAL EXECUTION: Runs after parallel activities
    logger.info("📧 Running sequential confirmation activity...")
    combined_data = {
        "order_id": order_input.get("order_id"),
        "total": process_result.get("total"),
        "items_count": inventory_result.get("items_count"),
        "status": process_result.get("status"),
        "inventory_status": inventory_result.get("inventory_status")
    }
    
    confirmation_result = yield ctx.call_activity(send_confirmation_activity, input=combined_data)
    
    logger.info(f"✅ Workflow completed for order: {order_input.get('order_id')}")
    
    return {
        "workflow_status": "completed",
        "order_id": order_input.get("order_id"),
        "process_result": process_result,
        "inventory_result": inventory_result,
        "confirmation": confirmation_result,
        "execution_summary": {
            "parallel_activities": ["process_order", "check_inventory"],
            "sequential_activities": ["send_confirmation"],
            "total_activities": 3
        }
    }

# Initialize Workflow Runtime
workflow_runtime = WorkflowRuntime()

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage workflow runtime lifecycle"""
    logger.info("🔧 Registering workflows and activities...")
    
    # Register workflow and activities
    workflow_runtime.register_workflow(
    order_processing_workflow,
    name="order_processing_workflow")
    workflow_runtime.register_activity(process_order_activity)
    workflow_runtime.register_activity(check_inventory_activity)
    workflow_runtime.register_activity(send_confirmation_activity)
    
    logger.info("🚀 Starting Dapr Workflow Runtime...")
    # Start workflow runtime in background thread (it's a blocking call)
    loop = asyncio.get_event_loop()
    workflow_task = loop.run_in_executor(None, workflow_runtime.start)
    logger.info("✅ Workflow Runtime started successfully")
    
    yield  # Application runs
    
    # Shutdown
    logger.info("🛑 Shutting down Dapr Workflow Runtime...")
    workflow_runtime.shutdown()
    logger.info("✅ Workflow Runtime shutdown complete")

# FastAPI App
app = FastAPI(
    title="Dapr Workflow Demo - Production",
    description="Production-ready Dapr workflow with parallel and sequential activities",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {
        "message": "Dapr Workflow Demo - Production Mode",
        "workflow_engine": "Dapr SDK with Scheduler",
        "features": {
            "parallel_activities": 2,
            "sequential_activities": 1,
            "state_management": "Redis",
            "scheduler": "Dapr Scheduler"
        },
        "endpoints": {
            "start_workflow": "POST /workflow/start",
            "get_status": "GET /workflow/status/{instance_id}",
            "terminate_workflow": "POST /workflow/terminate/{instance_id}",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "workflow_runtime": "running"}

from pydantic import BaseModel
from typing import List

class WorkflowStartRequest(BaseModel):
    order_id: str
    amount: float
    items: List[str]

@app.post("/workflow/start")
async def start_workflow(request: WorkflowStartRequest):
    """Start a new workflow instance"""
    try:
        with DaprClient() as client:
            order_data = {
                "order_id": request.order_id,
                "amount": request.amount,
                "items": request.items
            }
            
            instance_id = f"order_{request.order_id}"
            
            logger.info(f"🎬 Starting workflow instance: {instance_id}")
            
            client.start_workflow(
                workflow_component="dapr",
                workflow_name="order_processing_workflow",
                input=order_data,
                instance_id=instance_id
            )
            
            logger.info(f"✅ Workflow started: {instance_id}")
            
            return {
                "status": "started",
                "instance_id": instance_id,
                "order_data": order_data,
                "message": "Workflow is executing. Use /workflow/status/{instance_id} to check progress"
            }
    except Exception as e:
        logger.error(f"❌ Error starting workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflow/status/{instance_id}")
async def get_workflow_status(instance_id: str):
    """Get the current status of a workflow instance"""
    try:
        with DaprClient() as client:
            status = client.get_workflow(
                instance_id=instance_id,
                workflow_component="dapr"
            )
            
            # Extract runtime status as string
            runtime_status = str(status.runtime_status) if hasattr(status, 'runtime_status') else "UNKNOWN"
            
            # Build response with safe serialization
            response = {
                "instance_id": instance_id,
                "runtime_status": runtime_status,
            }
            
            # Add created_at if available
            if hasattr(status, 'created_at') and status.created_at:
                try:
                    response["created_at"] = str(status.created_at)
                except:
                    response["created_at"] = None
            
            # Add last_updated if available
            if hasattr(status, 'last_updated') and status.last_updated:
                try:
                    response["last_updated"] = str(status.last_updated)
                except:
                    response["last_updated"] = None
            
            # Add output if workflow is completed
            if hasattr(status, 'serialized_output') and status.serialized_output:
                try:
                    import json
                    response["output"] = json.loads(status.serialized_output)
                except Exception as e:
                    logger.warning(f"Could not parse workflow output: {e}")
                    response["output"] = status.serialized_output
            
            # Add failure details if workflow failed
            if hasattr(status, 'failure_details') and status.failure_details:
                response["failure_details"] = str(status.failure_details)
            
            return response
            
    except Exception as e:
        logger.error(f"❌ Error getting workflow status: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Workflow not found: {str(e)}")

@app.post("/workflow/terminate/{instance_id}")
async def terminate_workflow(instance_id: str):
    """Terminate a running workflow instance"""
    try:
        with DaprClient() as client:
            client.terminate_workflow(
                instance_id=instance_id,
                workflow_component="dapr"
            )
            
            logger.info(f"🛑 Terminated workflow: {instance_id}")
            
            return {
                "status": "terminated",
                "instance_id": instance_id,
                "message": "Workflow has been terminated"
            }
    except Exception as e:
        logger.error(f"❌ Error terminating workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflow/pause/{instance_id}")
async def pause_workflow(instance_id: str):
    """Pause a running workflow instance"""
    try:
        with DaprClient() as client:
            client.pause_workflow(
                instance_id=instance_id,
                workflow_component="dapr"
            )
            
            logger.info(f"⏸️  Paused workflow: {instance_id}")
            
            return {
                "status": "paused",
                "instance_id": instance_id,
                "message": "Workflow has been paused"
            }
    except Exception as e:
        logger.error(f"❌ Error pausing workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflow/resume/{instance_id}")
async def resume_workflow(instance_id: str):
    """Resume a paused workflow instance"""
    try:
        with DaprClient() as client:
            client.resume_workflow(
                instance_id=instance_id,
                workflow_component="dapr"
            )
            
            logger.info(f"▶️  Resumed workflow: {instance_id}")
            
            return {
                "status": "resumed",
                "instance_id": instance_id,
                "message": "Workflow has been resumed"
            }
    except Exception as e:
        logger.error(f"❌ Error resuming workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)