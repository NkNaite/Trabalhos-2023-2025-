import json
import pandas as pd

try:
    with open('data/pax_tools_data.json', 'r', encoding='utf-8') as f:
        pax_data = json.load(f)
        
    print("--- pax_tools_data.json Keys ---")
    keys = list(pax_data.keys())
    print(keys[:10])
    
    max_tier = 0
    tiers_set = set()
    uid_parts = set()
    for item_data in pax_data.get('items', []):
        uid = item_data.get('uid', '')
        tier = item_data.get('tier', 0)
        
        if uid.startswith('wearable') or uid.startswith('wieldable') or uid.endswith('_bow') or 'shield' in uid:
            max_tier = max(max_tier, tier)
            tiers_set.add(tier)
            for part in uid.split('_'):
                uid_parts.add(part)
                
    print(f"Max tier: {max_tier}")
    print(f"All tiers: {tiers_set}")
    print(f"UID parts (potential rarities): {sorted(list(uid_parts))}")


except Exception as e:
    print(f"Error reading pax_tools_data.json: {e}")

try:
    df = pd.read_parquet('data/selene_latest.parquet')
    print("\n--- selene_latest.parquet Schema ---")
    print(df.dtypes)
except Exception as e:
    print(f"Error reading parquet: {e}")
