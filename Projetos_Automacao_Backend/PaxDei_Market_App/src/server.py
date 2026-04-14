
# === AI AGENT SAFETY DIRECTIVE (DO NOT IGNORE) ===
# 1. NO INFINITE LOOPS: Ensure all loops have break conditions or maximum iterations.
# 2. DATA RESOURCE ECONOMY: Avoid reading large files (e.g., >100MB) directly in the API loop.
#    Use pre-aggregated summaries or indexed data.
# 3. NO SYSTEM OVERLOAD: If a task takes more than 5s, implement a background worker or abort.
# 4. MONITORING: Always log start/end/error for heavy operations.

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os
import pandas as pd
import json

# Add src to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.market import MarketAnalyzer
from modules.crafting import CraftingAnalyzer
from modules.logistics import ArbitrageFinder

app = FastAPI(title="Pax Dei Advisor API")

# Allow CORS for local development (Frontend running on port 5173 usually)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev, allow all. In prod, lock this down.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_data_dir():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data")

# Mount Static Files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/api/market/liquidity")
def get_liquidity():
    data_dir = get_data_dir()
    analyzer = MarketAnalyzer(data_dir)
    df = analyzer.check_liquidity()
    if df is None or df.empty:
        # Try to read generated CSV if live calculation returns nothing (e.g. no new snapshot turnover)
        csv_path = os.path.join(data_dir, "liquidez_diaria.csv")
        if os.path.exists(csv_path):
             df = pd.read_csv(csv_path)
        else:
            return []
            
    # Convert to list of dicts with safety lock to 100 items so UI/Agent doesn't crash
    return df.head(100).to_dict(orient="records")

@app.get("/api/crafting/opportunities")
def get_crafting_opportunities(top: int = 20):
    data_dir = get_data_dir()
    analyzer = CraftingAnalyzer(data_dir)
    df = analyzer.analyze_profitability()
    
    if df is None or df.empty:
        # Fallback to CSV
        csv_path = os.path.join(data_dir, "analise_disparidade.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            # Ensure sort
            df = df.sort_values(by='Spread', ascending=False)
        else:
            return []
            
    # Include Tier if available (it should be added in crafting.py)
    return df.head(top).fillna(0).to_dict(orient="records")

@app.get("/api/logistics/arbitrage")
def get_arbitrage(item: str = None, province: str = None):
    data_dir = get_data_dir()
    finder = ArbitrageFinder(data_dir)
    df = finder.find_opportunities(province=province)
    
    if df is None or df.empty:
        return []
    
    # Filter by item if requested
    if item:
        df = df[df['Item'] == item]
        
    # Deduplicate for variety if no item specified, otherwise show all routes for that item
    if not item:
        df_dedup = df.drop_duplicates(subset=['Item']).head(50) # Increased variety cap slightly, but locked
        return df_dedup.fillna(0).to_dict(orient="records")
    
    # Cap single item arbitrage to 20 results 
    return df.head(20).fillna(0).to_dict(orient="records")

@app.get("/api/market/search")
def search_items(query: str):
    data_dir = get_data_dir()
    # Simple search against latest parquet or catalogue
    # For speed, let's load the latest snapshot's unique items
    analyzer = MarketAnalyzer(data_dir)
    return analyzer.search_items(query)

@app.get("/api/market/item/{item_name}/history")
def get_item_history_api(item_name: str):
    data_dir = get_data_dir()
    analyzer = MarketAnalyzer(data_dir)
    stats = analyzer.get_item_history(item_name)
    if stats is None or stats.empty:
        return []
    
    # Reset index to get SnapshotDate as a column
    stats = stats.reset_index()
    # Convert timestamps to string for JSON serialization
    stats['SnapshotDate'] = stats['SnapshotDate'].astype(str)
    # Fill NaN with 0 to valid JSON error
    stats = stats.fillna(0)
    return stats.to_dict(orient="records")

@app.get("/api/market/item/{item_name}/producers")
def get_item_producers_api(item_name: str):
    data_dir = get_data_dir()
    analyzer = MarketAnalyzer(data_dir)
    stats = analyzer.get_producer_stats(item_name)
    if stats is None or stats.empty:
        return []
        
    stats = stats.reset_index()
    return stats.fillna(0).head(5).to_dict(orient="records")

@app.get("/api/logistics/suppliers")
def get_suppliers():
    data_dir = get_data_dir()
    csv_path = os.path.join(data_dir, "suppliers.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        return df.fillna("").to_dict(orient="records")
    return []

@app.get("/api/logistics/orders")
def get_orders():
    data_dir = get_data_dir()
    csv_path = os.path.join(data_dir, "client_orders.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        return df.fillna("").to_dict(orient="records")
    return []

@app.post("/api/admin/fetch-prices")
def trigger_fetch_prices():
    import subprocess
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "sync_data.py")
    python_exe = r"D:\py\python.exe" # Hardcoded as per environment
    
    try:
        # Run synchronous (blocking) for MVP simplicity to ensure it completes before user feedback
        # In prod, this should be a background task
        result = subprocess.run([python_exe, script_path], capture_output=True, text=True, check=True)
        return {"status": "success", "message": "Market prices updated successfully.", "log": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": "Script execution failed.", "log": e.stderr}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/crafting/item/{item_name}/detailed")
def get_crafting_detailed(item_name: str):
    data_dir = get_data_dir()
    analyzer = CraftingAnalyzer(data_dir)
    blueprint = analyzer.get_crafting_blueprint(item_name)
    if not blueprint:
        return {"error": "Item not found or no recipe"}
    return blueprint

@app.get("/api/market/demand")
def get_demand_intensity():
    data_dir = get_data_dir()
    analyzer = MarketAnalyzer(data_dir)
    df = analyzer.check_demand_intensity()
    if df is None or df.empty:
        return []
    return df.head(50).fillna(0).to_dict(orient="records")

@app.get("/api/market/liquidity/regional")
def get_regional_liquidity():
    data_dir = get_data_dir()
    analyzer = MarketAnalyzer(data_dir)
    df = analyzer.check_regional_liquidity()
    if df is None or df.empty:
        return []
    return df.head(20).fillna(0).to_dict(orient="records")

@app.get("/api/market/locations")
def get_locations():
    data_dir = get_data_dir()
    analyzer = MarketAnalyzer(data_dir)
    locations = analyzer.get_locations()
    return locations

@app.get("/api/market/supply_demand")
def get_supply_demand(province: str = None, valley: str = None, days: int = 7):
    data_dir = get_data_dir()
    analyzer = MarketAnalyzer(data_dir)
    df = analyzer.get_supply_demand(province=province, valley=valley, days=days)
    if df is None or df.empty:
        return []
    # Safety lock to 150 items max to avoid DOM explosion on the client & agent
    return df.head(150).fillna(0).to_dict(orient="records")


if __name__ == "__main__":
    print("Starting API Server on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
