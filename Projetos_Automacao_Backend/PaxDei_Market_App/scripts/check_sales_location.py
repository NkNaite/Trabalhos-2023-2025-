
import os
import json
import glob
import pandas as pd

def check_sales_location():
    data_dir = "d:/PaxDei_Tool/data"
    profile_file = os.path.join(data_dir, "user_profile.json")
    
    if not os.path.exists(profile_file):
        print("Profile not found.")
        return

    with open(profile_file, 'r') as f:
        profile = json.load(f)
    
    seller_id = profile.get('my_seller_id')
    if not seller_id:
        print("Seller ID not found.")
        return

    print(f"Analyzing sales for Seller ID: {seller_id}")

    # Load all history + latest
    history_dir = os.path.join(data_dir, "history")
    history_files = sorted(glob.glob(os.path.join(history_dir, '**', '*.parquet'), recursive=True))
    latest_file = os.path.join(data_dir, 'selene_latest.parquet')
    if os.path.exists(latest_file):
        history_files.append(latest_file)

    listings_info = {}

    target_item = "Bold Winter Stout"

    print(f"Scanning {len(history_files)} files for '{target_item}'...")

    for fpath in history_files:
        try:
            df = pd.read_parquet(fpath)
            
            # Identify columns
            scol = 'SellerHash' if 'SellerHash' in df.columns else 'Seller'
            
            # Filter for seller and item
            my_stuff = df[
                (df[scol] == seller_id) & 
                (df['Item'] == target_item)
            ]
            
            if my_stuff.empty:
                continue

            for _, row in my_stuff.iterrows():
                lid = row.get('ListingID')
                if not lid: continue
                
                qty = row['Amount']
                zone = row.get('Zone', 'Unknown')
                
                if lid not in listings_info:
                    listings_info[lid] = {
                        'max_qty': qty,
                        'last_qty': qty,
                        'zone': zone,
                        'last_seen': fpath
                    }
                else:
                    info = listings_info[lid]
                    info['max_qty'] = max(info['max_qty'], qty)
                    info['last_qty'] = qty
                    info['last_seen'] = fpath
                    
        except Exception as e:
            continue

    # Calculate sales per zone
    zone_sales = {}
    
    for lid, info in listings_info.items():
        sold_qty = 0
        is_active = (info['last_seen'] == latest_file)
        
        if is_active:
            sold_qty = info['max_qty'] - info['last_qty']
        else:
            sold_qty = info['max_qty'] # Sold out / Expired
            
        if sold_qty > 0:
            z = info['zone']
            if z not in zone_sales:
                zone_sales[z] = 0
            zone_sales[z] += sold_qty

    print("\n=== Sales Location Report for Bold Winter Stout ===")
    for zone, qty in zone_sales.items():
        print(f"Zone: {zone} | Sold: {qty}")
        
    if not zone_sales:
        print("No sales detected.")

if __name__ == "__main__":
    check_sales_location()
