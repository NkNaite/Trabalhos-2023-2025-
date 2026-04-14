import os
import glob
import pandas as pd
from datetime import datetime
try:
    from huggingface_hub import HfApi, hf_hub_download
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependencies: pip install huggingface_hub python-dotenv")
    exit(1)

# Load Env
load_dotenv()
HF_TOKEN = os.environ.get("HF_TOKEN")
REPO_ID = os.environ.get("HF_REPO_ID")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")

def sync_from_hf():
    if not HF_TOKEN or not REPO_ID:
        print("HF_TOKEN or HF_REPO_ID not set. Skipping download.")
        return

    print(f"Connecting to Hugging Face Repo: {REPO_ID}...")
    api = HfApi(token=HF_TOKEN)
    
    try:
        # List files in repo
        files = api.list_repo_files(repo_id=REPO_ID, repo_type="dataset")
        
        # Filter for history files
        history_files = [f for f in files if f.startswith("history/") and f.endswith(".parquet")]
        
        if not history_files:
            print("No history files found in repo.")
            return

        print(f"Found {len(history_files)} history files in repo.")
        
        # Download missing files
        new_downloads = 0
        for hf_path in history_files:
            # Construct local path: data/history/year=.../month=.../file.parquet
            # hf_path is like "history/year=2024/month=10/market_...parquet"
            # We want to map it to DATA_DIR/history/...
            # Remove "history/" prefix for local join, since HISTORY_DIR is .../data/history
            rel_path = hf_path.replace("history/", "", 1) if hf_path.startswith("history/") else hf_path
            local_path = os.path.join(HISTORY_DIR, rel_path)
            
            if not os.path.exists(local_path):
                print(f"Downloading {hf_path}...")
                hf_hub_download(
                    repo_id=REPO_ID,
                    filename=hf_path,
                    repo_type="dataset",
                    token=HF_TOKEN,
                    local_dir=DATA_DIR, # Using DATA_DIR because hf_path includes "history/..."
                    local_dir_use_symlinks=False
                )
                new_downloads += 1
        
        if new_downloads == 0:
            print("Local history is up to date.")
        else:
            print(f"Downloaded {new_downloads} new snapshots.")

    except Exception as e:
        print(f"Sync failed: {e}")

def aggregate_history():
    print("Aggregating local history...")
    search_path = os.path.join(HISTORY_DIR, "**", "*.parquet")
    files = glob.glob(search_path, recursive=True)
    
    if not files:
        print("No local history files to aggregate.")
        return

    dfs = []
    latest_file = None
    latest_ts = datetime.min

    for f in files:
        try:
            # Parse date from filename for sorting/latest check
            basename = os.path.basename(f)
            # market_YYYY-MM-DD_HH-MM.parquet
            timestamp_str = basename.replace("market_", "").replace(".parquet", "")
            try:
                # Format: YYYY-MM-DD_HH-MM
                file_dt = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M")
            except ValueError:
                file_dt = datetime.fromtimestamp(os.path.getmtime(f))

            # Track latest
            if file_dt > latest_ts:
                latest_ts = file_dt
                latest_file = f

            df = pd.read_parquet(f)
            df['SnapshotDate'] = file_dt
            dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")

    if not dfs:
        return

    # 1. Full History for Analysis
    full_df = pd.concat(dfs, ignore_index=True)
    full_path = os.path.join(DATA_DIR, "full_history.parquet")
    full_df.to_parquet(full_path, compression='snappy')
    print(f"Saved aggregated history to: {full_path} ({len(full_df)} rows)")

    # 2. Latest Snapshot for Dashboard
    if latest_file:
        latest_df = pd.read_parquet(latest_file) # Re-read clean or use from list
        # Ensure it saves as selene_latest.parquet
        latest_out = os.path.join(DATA_DIR, "selene_latest.parquet")
        latest_df.to_parquet(latest_out, compression='snappy')
        print(f"Updated latest snapshot: {latest_out} (from {os.path.basename(latest_file)})")

def generate_summaries():
    print("Generating pre-aggregated summaries for Dashboard...")
    full_path = os.path.join(DATA_DIR, "full_history.parquet")
    if not os.path.exists(full_path):
        print("full_history.parquet not found. Skipping summaries.")
        return
    
    try:
        # Load necessary columns for the last 14 days initially to have a buffer
        df = pd.read_parquet(full_path, columns=['Item', 'Price', 'Zone', 'SnapshotDate'])
        
        # Ensure SnapshotDate is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['SnapshotDate']):
            df['SnapshotDate'] = pd.to_datetime(df['SnapshotDate'])

        # 1. 7-Day Medians
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=7)
        df_7d = df[df['SnapshotDate'] >= cutoff].copy()
        
        if df_7d.empty:
            print("No data in last 7 days for summaries.")
            return

        # Global Medians
        medians_global = df_7d.groupby('Item')['Price'].median().to_dict()
        
        # Regional Medians (for province filtering)
        # Extract Province from Zone (first part before '-')
        def get_prov(z):
            if not isinstance(z, str): return "Unknown"
            return z.split('-')[0].strip().capitalize()
            
        df_7d['Province'] = df_7d['Zone'].apply(get_prov)
        
        # Group by Province and Item
        regional_stats = df_7d.groupby(['Province', 'Item'])['Price'].median().reset_index()
        
        # Convert to nested dict: {Province: {Item: Median}}
        medians_regional = {}
        for prov in regional_stats['Province'].unique():
            prov_df = regional_stats[regional_stats['Province'] == prov]
            medians_regional[prov] = prov_df.set_index('Item')['Price'].to_dict()
        
        # Save to a single JSON with metadata
        import json
        summary = {
            "generated_at": datetime.now().isoformat(),
            "global_7d": medians_global,
            "regional_7d": medians_regional
        }
        
        out_path = os.path.join(DATA_DIR, "7d_medians.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f)
        print(f"Summaries saved to: {out_path}")
        
    except Exception as e:
        print(f"Summary generation failed: {e}")

if __name__ == "__main__":
    sync_from_hf()
    aggregate_history()
    generate_summaries()
