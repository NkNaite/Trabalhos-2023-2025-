
import pandas as pd
import json
import os
import re

# Configuration (Relative to project root d:\PaxDei_Tool)
PROJECT_ROOT = "d:/PaxDei_Tool"
STOCK_LIST_FILE = os.path.join(PROJECT_ROOT, "Guia_Estoque_Crafting.md")
PARQUET_FILE = os.path.join(PROJECT_ROOT, "data/selene_latest.parquet")
CATALOG_FILE = os.path.join(PROJECT_ROOT, "data/catalogo_manufatura.json")
TARGET_ZONES = [
    'inis_gallia-javerdus', 'inis_gallia-langres', 'inis_gallia-trecassis', 'inis_gallia-morvan', 
    'inis_gallia-nones', 'inis_gallia-ardennes', 'inis_gallia-vitry', 'inis_gallia-aras'
]
HIGH_TIER_THRESHOLD = 4 

def load_stock_list(filepath):
    """Extracts item names from the markdown list."""
    items = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('- '):
                    # Remove markdown bullet and descriptions
                    content = line[2:].strip()
                    # Remove (Detail)
                    content = re.sub(r'\s*\(.*\)$', '', content)
                    # Remove **bold**
                    content = content.replace('**', '')
                    if content:
                        items.add(content)
        # Also include translated names if any in catalog?
        # Assuming names in parquet match names in list (English).
    except Exception as e:
        print(f"Error reading stock list: {e}")
    return items

def main():
    print("--- Starting Analysis ---")
    
    # 1. Load Data
    if not os.path.exists(PARQUET_FILE):
        print(f"Error: {PARQUET_FILE} not found. Please run sync first.")
        return

    print(f"Loading market data from {PARQUET_FILE}...")
    try:
        df = pd.read_parquet(PARQUET_FILE)
    except Exception as e:
        print(f"Error reading parquet: {e}")
        return

    print("Columns:", df.columns.tolist())
    
    # Check if 'Item' column exists, sometimes it's 'ItemName'
    item_col = 'Item' if 'Item' in df.columns else 'ItemName'
    if item_col not in df.columns:
        print("Error: Could not find Item column.")
        return

    print(f"Loading stock list from {STOCK_LIST_FILE}...")
    stock_items = load_stock_list(STOCK_LIST_FILE)
    print(f"Found {len(stock_items)} items in stock list.")
    # Debug stock list
    # print(list(stock_items)[:5])

    print(f"Loading catalog from {CATALOG_FILE}...")
    item_tiers = {} # ItemName -> Tier
    try:
        if os.path.exists(CATALOG_FILE):
            with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
                # Catalog structure: List of dicts? Or Dict of dicts?
                # Based on previous check: it seemed to be a list in "inputs": [ ... ]
                # But check_catalog_sample.py output just one item value.
                # If it's a list of items, each item has 'Item' key?
                # If it's a dict, keys are item names.
                # Let's handle both.
                if isinstance(catalog, dict):
                    for k, v in catalog.items():
                        if isinstance(v, dict):
                            tier = v.get('tier', 1)
                            item_tiers[k] = tier
                        elif isinstance(v, list):
                            # Maybe v is the list of recipes for k?
                            # Check first element
                            if len(v) > 0 and isinstance(v[0], dict):
                                tier = v[0].get('tier', 1)
                                item_tiers[k] = tier
                elif isinstance(catalog, list):
                    for item_data in catalog:
                         name = item_data.get('Item') or item_data.get('ItemName')
                         if name:
                             item_tiers[name] = item_data.get('tier', 1)
    except Exception as e:
        print(f"Error loading catalog: {e}")

    # 2. Calculate Global Medians
    print("Calculating global medians...")
    # Clean prices? 
    # Assume distinct listings.
    # We want median price per item across ALL zones.
    global_medians = df.groupby(item_col)['Price'].median()
    
    # 3. Filter by Zones
    print(f"Filtering for zones: {TARGET_ZONES}")
    # Zones in parquet might be case sensitive?
    # Normalize strings?
    # Let's assume matches.
    original_len = len(df)
    df_route = df[df['Zone'].isin(TARGET_ZONES)].copy()
    print(f"Filtered {len(df_route)} listings from {original_len} total.")
    
    if df_route.empty:
        print("No listings found in the specified zones.")
        return

    # 4. Analyze
    stock_deals = []
    gear_deals = []
    
    for idx, row in df_route.iterrows():
        item = row[item_col]
        price = row['Price']
        zone = row['Zone']
        
        # Determine global median
        if item not in global_medians:
            continue # Should be there if in df
        
        median = global_medians[item]
        if median <= 0: continue

        # Logic 1: Stock List Deals
        if item in stock_items:
            # Exception: Mustard (Always Buy)
            if item == "Mustard":
                 stock_deals.append({
                    'Item': item,
                    'Zone': zone,
                    'Price': price,
                    'Median': median,
                    'Discount_Pct': 0.0, # Irrelevant
                    'Seller': str(row.get('SellerHash', 'Unknown'))[:8] + " (MUST BUY)"
                })
            # Criteria: Price < Median AND Median >= 100 (High Value Items)
            elif price < median and median >= 100:
                diff = median - price
                discount_pct = (diff / median) * 100
                stock_deals.append({
                    'Item': item,
                    'Zone': zone,
                    'Price': price,
                    'Median': median,
                    'Discount_Pct': round(discount_pct, 1),
                    'Seller': str(row.get('SellerHash', 'Unknown'))[:8]
                })

        # Logic 2: High Tier Gear
        # Tier Check
        tier = item_tiers.get(item, 0)
        # Gear Check
        # Durability > 0 usually means gear.
        # Check if durability column exists and > 0.9 (90%)
        is_gear = False
        durability_val = 0.0
        if 'Durability' in row and pd.notnull(row['Durability']):
            try:
                durability_val = float(row['Durability'])
                # Assuming Durability is normalized [0, 1] based on stats (max=1.0)
                if durability_val > 0:
                    is_gear = True
            except:
                pass
        
        # Criteria: High Tier And Gear And Price <= 50% Median AND Durability >= 0.9
        if is_gear and tier >= HIGH_TIER_THRESHOLD and durability_val >= 0.9:
            if price <= (0.5 * median):
                 diff = median - price
                 discount_pct = (diff / median) * 100
                 gear_deals.append({
                    'Item': item,
                    'Tier': tier,
                    'Zone': zone,
                    'Price': price,
                    'Median': median,
                    'Discount_Pct': round(discount_pct, 1),
                    'Durability': row['Durability'],
                    'Seller': str(row.get('SellerHash', 'Unknown'))[:8]
                })

    # 5. Report
    print(f"\n=== STOCK LIST DEALS ({len(stock_deals)}) ===")
    if stock_deals:
        result_df = pd.DataFrame(stock_deals)
        # Sort by Discount
        result_df = result_df.sort_values('Discount_Pct', ascending=False)
        print(result_df[['Item', 'Zone', 'Price', 'Median', 'Discount_Pct', 'Seller']].to_string(index=False))
    else:
        print("No deals found for stock list items (Price < Global Median).")

    print(f"\n=== HIGH TIER GEAR DEALS ({len(gear_deals)}) ===")
    if gear_deals:
        result_df = pd.DataFrame(gear_deals)
        # Sort by Tier desc, then Discount
        result_df = result_df.sort_values(['Tier', 'Discount_Pct'], ascending=[False, False])
        print(result_df[['Item', 'Tier', 'Zone', 'Price', 'Median', 'Discount_Pct', 'Durability', 'Seller']].to_string(index=False))
    else:
        print("No high tier gear deals found (Tier >= 4, Price <= 50% Median).")

if __name__ == "__main__":
    main()
