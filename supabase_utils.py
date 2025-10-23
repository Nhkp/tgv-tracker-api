import logging
import pandas as pd # type: ignore
import os
import sys
from dotenv import load_dotenv # type: ignore
from fastapi import FastAPI # type: ignore
from pathlib import Path
from supabase import create_client, Client # type: ignore
from typing import Optional
import json
from datetime import date, datetime


load_dotenv()

# Configure logging
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

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Optional[Client] = None

async def initialize_supabase():
    """Initialize Supabase client"""
    global supabase
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized")
    else:
        logger.error("Supabase credentials not found in environment variables")

async def check_table_exists(table_name: str = "tgv-data"):
    """Check if a table exists in Supabase"""
    if supabase is None:
        logger.error("Supabase client not initialized")
        return {"exists": False, "error": "Supabase client not initialized"}
    
    try:
        # Check if table exists and get row count
        result = supabase.table(table_name).select("*", count="exact").limit(0).execute()
        row_count = result.count if hasattr(result, 'count') else 0

        logger.info(f"Table '{table_name}' exists with {row_count} rows")

    except Exception as e:
        logger.info(f"Table '{table_name}' does not exist : {str(e)}")

async def get_table_info(table_name: str = "tgv-data"):
    if supabase is None:
        logger.error("Supabase client not initialized")
        return {"exists": False, "error": "Supabase client not initialized"}
    
    # Check if table exists and get row count
    result = supabase.table(table_name).select("*", count="exact").limit(0).execute()
    return result.count if hasattr(result, 'count') else 0

async def get_avg_delay_by_station(table_name: str = "tgv-data", limit: int = 10, order: str = "asc"):
    """
    Group by 'gare_depart' and calculate average 'retard_moyen_depart',
    ordered by order parameter (asc/desc), returning first 'limit' rows
    Only for National service
    """
    if supabase is None:
        logger.error("Supabase client not initialized")
        return {"error": "Supabase client not initialized"}
    
    try:
        # Fetch all data first (for simple implementation) - filter by service = "National"
        result = supabase.table(table_name).select("gare_depart, retard_moyen_depart, service").eq("service", "National").execute()
        
        if not result.data:
            logger.warning(f"No National service data found in table '{table_name}'")
            return {"data": [], "message": "No National service data found"}
        
        # Convert to pandas DataFrame for aggregation
        df = pd.DataFrame(result.data)
        
        # Clean and convert retard_moyen_depart to numeric
        df['retard_moyen_depart'] = pd.to_numeric(df['retard_moyen_depart'], errors='coerce')
        
        # Determine sort order
        ascending = order.lower() == "asc"
        
        # Group by gare_depart and calculate mean, then sort and limit
        avg_delays = (df.groupby('gare_depart')['retard_moyen_depart']
                    .mean()
                    .reset_index()
                    .sort_values('retard_moyen_depart', ascending=ascending)
                    .head(limit))
        
        # Convert back to list of dictionaries
        result_data = avg_delays.to_dict('records')
        
        order_desc = "lowest" if ascending else "highest"
        logger.info(f"Retrieved top {len(result_data)} National service stations with {order_desc} average delays")
        
        return {
            "data": result_data,
            "count": len(result_data),
            "table_name": table_name,
            "order": order,
            "service_filter": "National",
            "description": f"Top {limit} National service stations with {order_desc} average delays"
        }
        
    except Exception as e:
        logger.error(f"Error getting average delays by station: {str(e)}")
        return {"error": str(e)}

async def get_unique_stations_count_from_db(table_name: str = "tgv-data"):
    """Get the total number of unique gare_depart stations for National service"""
    if supabase is None:
        logger.error("Supabase client not initialized")
        return {"error": "Supabase client not initialized"}
    
    try:
        # Fetch all gare_depart data for National service
        result = supabase.table(table_name).select("gare_depart").execute()
        
        if not result.data:
            logger.warning(f"No National service data found in table '{table_name}'")
            return {
                "unique_stations_count": 0,
                "message": "No National service data found",
                "service_filter": "National"
            }
        
        # Convert to pandas DataFrame and get unique count
        df = pd.DataFrame(result.data)
        unique_count = df['gare_depart'].nunique()
        
        logger.info(f"Found {unique_count} unique stations for National service in table '{table_name}'")
        
        return {
            "unique_stations_count": unique_count,
            "total_records": len(result.data),
            "table_name": table_name,
            "service_filter": "National"
        }
        
    except Exception as e:
        logger.error(f"Error getting unique stations count: {str(e)}")
        return {"error": str(e)}
