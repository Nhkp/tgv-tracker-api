import logging
import sys
import time
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal

from supabase_utils import initialize_supabase, get_table_info, check_table_exists, get_avg_delay_by_station


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tgv_tracker.log")
    ]
)

logger = logging.getLogger("tgv_tracker")

app = FastAPI(
    title="TGV Tracker API",
    description="A minimal API for TGV tracking",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8002", "http://localhost:5173", "http://localhost:8080",
                "http://172.19.0.3:8002", "http://172.19.0.3:5173", "http://172.19.0.3:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("TGV Tracker API starting up...")
    await initialize_supabase()
    await check_table_exists()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("TGV Tracker API shutting down...")

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to TGV Tracker API"}

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}

@app.get("/api/count_rows")
async def get_count_rows():
    logger.info("Count rows endpoint accessed")
    table_info = await get_table_info()
    return {"row_count": table_info}

@app.get("/api/delays")
async def get_delays(
    table_name: str = Query(default="tgv-data", description="Table name to query"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of results to return"),
    order: Literal["asc", "desc"] = Query(default="asc", description="Sort order: 'asc' for best (lowest delays), 'desc' for worst (highest delays)")
):
    """Get average delays by station using pandas technique"""
    logger.info(f"Delays pandas endpoint accessed - table: {table_name}, limit: {limit}, order: {order}")
    
    start_time = time.time()
    result = await get_avg_delay_by_station(table_name, limit, order)
    end_time = time.time()
    
    execution_time = round((end_time - start_time) * 1000, 2)  # Convert to milliseconds
    
    logger.info(f"Pandas query executed in {execution_time}ms")
    
    order_description = "best (lowest delays)" if order == "asc" else "worst (highest delays)"
    
    return {
        "method": "pandas",
        "execution_time_ms": execution_time,
        "table_name": table_name,
        "limit": limit,
        "order": order,
        "description": f"Top {limit} {order_description} stations",
        "result": result
    }
    