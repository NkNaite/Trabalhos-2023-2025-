
import os
import json
import glob
import pandas as pd
import math
import datetime

class SalesTracker:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.history_dir = os.path.join(data_dir, "history")
        self.profile_file = os.path.join(data_dir, "user_profile.json")
        self.state_file = os.path.join(data_dir, "sales_tracker_state.json")
        self.seller_id = self._load_seller_id()

    def _load_seller_id(self):
        if not os.path.exists(self.profile_file):
             return None
        try:
            with open(self.profile_file, 'r') as f:
                profile = json.load(f)
            return profile.get('my_seller_id')
        except:
            return None

    def _load_state(self):
        if not os.path.exists(self.state_file):
            return {}
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_state(self, state):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not save tracker state: {e}")


    def identify_seller(self, item_name, price):
        """
        Finds a SellerHash that is selling item_name for exactly price.
        """
        latest_file = os.path.join(self.data_dir, 'selene_latest.parquet')
        if not os.path.exists(latest_file):
            return {"error": "No market data found."}
            
        try:
            df = pd.read_parquet(latest_file)
            
            # Find listings matching item and price
            # We check both Price (total) and UnitPrice just in case
            matches = df[
                (df['Item'].str.lower() == item_name.lower()) & 
                ((df['Price'] == price) | (df.get('UnitPrice', -1) == price))
            ]
            
            if matches.empty:
                 return {"error": f"No listings found for '{item_name}' at price {price}."}
            
            # Get seller column
            scol = 'SellerHash' if 'SellerHash' in df.columns else 'Seller'
            
            sellers = matches[scol].unique()
            
            if len(sellers) == 0:
                return {"error": "No sellers found."}
            elif len(sellers) > 1:
                return {
                    "error": f"Multiple sellers found with this price ({len(sellers)}). usage: choose a more unique price.",
                    "candidates": list(sellers)
                }
            else:
                seller_id = sellers[0]
                
                # Save to profile
                profile = {
                    "my_seller_id": seller_id,
                    "last_identified_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                with open(self.profile_file, 'w') as f:
                    json.dump(profile, f, indent=4)
                    
                self.seller_id = seller_id # Update instance
                return {"success": True, "seller_id": seller_id}
                
        except Exception as e:
            return {"error": str(e)}

    def track_sales(self, filter_item=None):
        if not self.seller_id:
            return {"error": "Seller ID not found. Run identification first."}

        # 1. Collect History Files
        history_files = sorted(glob.glob(os.path.join(self.history_dir, '**', '*.parquet'), recursive=True))
        latest_file = os.path.join(self.data_dir, 'selene_latest.parquet')
        if os.path.exists(latest_file):
            history_files.append(latest_file)

        if not history_files:
            return {"error": "No history data found."}

        min_last_seen_file = history_files[-1]
        
        # 2. Build Listing Lifecycle (SCAN ALL ITEMS)
        listings_info = {}
        
        def get_seller_col(columns):
            if 'SellerHash' in columns: return 'SellerHash'
            if 'Seller' in columns: return 'Seller'
            return None

        # Optimization: We scan everything to maintain global state consistency
        for fpath in history_files:
            try:
                df = pd.read_parquet(fpath)
                scol = get_seller_col(df.columns)
                if not scol: continue
                
                # Filter for my listings (ALL items)
                my_stuff = df[df[scol] == self.seller_id]
                
                if my_stuff.empty:
                    continue

                for _, row in my_stuff.iterrows():
                    lid = row.get('ListingID')
                    if not lid: continue
                    
                    qty = row['Amount']
                    item = row['Item']
                    u_price = row.get('UnitPrice', 0)
                    price = row.get('Price', 0)

                    # Update price logic
                    if u_price == 0 and qty > 0:
                        u_price = price / qty
                    
                    if lid not in listings_info:
                        listings_info[lid] = {
                            'item': item,
                            'max_qty': qty,
                            'last_qty': qty,
                            'unit_price': u_price,
                            'lot_price': price if price > 0 else u_price * qty, # Assume max price is initial lot price approx
                            'zone': row.get('Zone', 'Unknown'),
                            'first_seen': fpath,
                            'last_seen': fpath
                        }
                    else:
                        info = listings_info[lid]
                        info['max_qty'] = max(info['max_qty'], qty)
                        info['last_qty'] = qty
                        info['last_seen'] = fpath
                        if u_price > 0: info['unit_price'] = u_price
                        # We keep initial lot price assumption based on first sight or update if price increases (rare)
                        # Actually 'Price' field updates as quantity decreases? 
                        # In Pax Dei market data, 'Price' is usually the total price of the stack.
                        # So if quantity drops, Price drops. 
                        # Correct Fee Basis = Initial Full Price.
                        # We should store max_price seen? 
                        # 'Price' = 'UnitPrice' * 'Amount'.
                        # Fee = 5% of Lot Price.
                        # Lot Price = Unit Price * Initial Quantity (Max Qty).
                        # We calculate Lot Price effectively at end.
                            
            except Exception:
                continue

        # 3. Calculate All-Time Totals
        current_totals = {
            'total_revenue': 0.0,
            'total_fees': 0.0,
            'items': {}  
        }

        TAX_RATE = 0.05

        for lid, info in listings_info.items():
            itm = info['item']
            if itm not in current_totals['items']:
                current_totals['items'][itm] = {'revenue': 0.0, 'fees': 0.0, 'sold': 0, 'stock': 0}

            # Fee Calculation: 5% of Total Lot Value
            # Total Lot Value = Unit Price * Max Quantity (Initial Stack Size)
            lot_value = info['unit_price'] * info['max_qty']
            fee = lot_value * TAX_RATE
            
            # Sales Calculation
            sold_qty = 0
            is_active = (info['last_seen'] == min_last_seen_file)
            
            if is_active:
                sold_qty = info['max_qty'] - info['last_qty']
                current_totals['items'][itm]['stock'] += info['last_qty']
            else:
                sold_qty = info['max_qty']
            
            revenue = sold_qty * info['unit_price']
            
            # Aggregation
            current_totals['items'][itm]['fees'] += fee
            current_totals['items'][itm]['revenue'] += revenue
            current_totals['items'][itm]['sold'] += sold_qty
            
            current_totals['total_fees'] += fee
            current_totals['total_revenue'] += revenue

        # 4. Compare with Previous State (Incremental)
        prev_state = self._load_state()
        
        # Structure of response: Incremental
        diff_summary = {
            'period': 'Since Last Check' if prev_state else 'All Time (First Run)',
            'total_revenue': current_totals['total_revenue'] - prev_state.get('total_revenue', 0),
            'total_fees': current_totals['total_fees'] - prev_state.get('total_fees', 0),
            'net_profit': 0,
            'items': {}
        }
        diff_summary['net_profit'] = diff_summary['total_revenue'] - diff_summary['total_fees']

        # Determine diffs for items
        # If filter_item is set, we still calc diffs but only return specific one?
        # User wants "result counting from last consultation".
        # So we return the diffs.
        
        # We iterate over current items
        all_items = set(current_totals['items'].keys())
        prev_items = prev_state.get('items', {})
        
        for itm in all_items:
            curr = current_totals['items'][itm]
            prev = prev_items.get(itm, {'revenue': 0, 'fees': 0, 'sold': 0})
            
            # Stock is current, not diff
            d_rev = curr['revenue'] - prev['revenue']
            d_fees = curr['fees'] - prev['fees']
            d_sold = curr['sold'] - prev['sold']
            

            # Only include if there's activity or if it's the requested item
            # OR if the user just wants to see current stock status regardless of sales
            # Actually, user wants "stock listed, price per unit, price per lot, region" in the result.
            # So we should always return current stock details even if sold=0
            
            # Find listing details (price, zone) from current data
            # We take the first active listing we find for this item to represent "Price" 
            # (assuming consistent pricing, or we can average)
            # Better: Get weighted average or just ONE representative price
            
            price_repr = 0
            lot_price_repr = 0
            zone_repr = "Multiple"
            
            # Search for an active listing to get current details
            active_zones = set()
            active_prices = []
            
            for lid, info in listings_info.items():
                if info['item'] == itm and info['last_seen'] == min_last_seen_file:
                    active_zones.add(info['zone'])
                    active_prices.append((info['unit_price'], info['lot_price']))
            
            if active_zones:
                zone_repr = ", ".join(sorted(list(active_zones)))
                # Just take the first price found for now, or maybe average?
                # User asked for "price per unit", usually consistent.
                if active_prices:
                    price_repr = active_prices[0][0]
                    lot_price_repr = active_prices[0][1]
            else:
                pass # Defaults 0/Multiple
            
            if not active_zones and curr['stock'] == 0:
                # If no stock, maybe use last known details?
                # For now leave as 0/Multiple if we have no active listings
                pass

            if d_sold > 0 or d_fees > 0 or curr['stock'] > 0 or (filter_item and itm == filter_item):
                diff_summary['items'][itm] = {
                    'sold': d_sold,
                    'revenue': d_rev,
                    'fees': d_fees,
                    'profit': d_rev - d_fees,
                    'stock': curr['stock'],
                    'unit_price': price_repr,
                    'lot_price': lot_price_repr,
                    'zone': zone_repr
                }

        # 5. Save New State (Overwrite)
        # We transform current_totals to be JSON serializable
        # (It is already dicts and floats)
        current_totals['last_check'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save_state(current_totals)

        # 6. Apply Filter if requested
        if filter_item:
            if filter_item in diff_summary['items']:
                # Return just this item, but wrap in structure
                single_item_data = diff_summary['items'][filter_item]
                diff_summary['items'] = {filter_item: single_item_data}
            else:
                 # It might be an item with no new changes, but user asked for it. 
                 # Check current totals if it exists at all
                 if filter_item in current_totals['items']:
                      # No new changes, report 0
                      # But still find price/zone if we have stock
                      price_repr = 0
                      lot_price_repr = 0
                      zone_repr = "Multiple"
                      
                      # Search for details in listings info
                      for lid, info in listings_info.items():
                        if info['item'] == filter_item and info['last_seen'] == min_last_seen_file:
                            price_repr = info['unit_price']
                            lot_price_repr = info['lot_price']
                            zone_repr = info['zone']
                            break
                      
                      curr = current_totals['items'][filter_item]
                      diff_summary['items'] = {filter_item: {
                          'sold': 0, 'revenue': 0, 'fees': 0, 'profit': 0, 
                          'stock': curr['stock'],
                          'unit_price': price_repr,
                          'lot_price': lot_price_repr,
                          'zone': zone_repr
                      }}
                 else:
                     return {"error": f"Item '{filter_item}' not found in history."}

        return diff_summary
