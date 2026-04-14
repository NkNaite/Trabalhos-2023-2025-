
import os
import sys
import pandas as pd
import re

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from modules.market import MarketAnalyzer
from modules.logistics import ArbitrageFinder

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
STOCK_LIST_FILE = os.path.join(os.path.dirname(__file__), '..', 'Guia_Estoque_Crafting.md')

def load_stock_list():
    """Parses Guia_Estoque_Crafting.md to get the list of items."""
    if not os.path.exists(STOCK_LIST_FILE):
        print(f"Error: Stock list file not found at {STOCK_LIST_FILE}")
        return []
        
    items = []
    with open(STOCK_LIST_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Look for bullet points
            if line.startswith("- ") or line.startswith("* "):
                # Remove bullet
                item = line[2:].strip()
                # If it starts with ** and ends with **, it's likely a category header (e.g. **Ferraria:**)
                if item.startswith("**") and item.endswith("**"):
                    continue
                if item.startswith("**") and item.endswith(":"):
                     continue
                
                # Clean up item name
                item = item.replace("**", "")
                
                # Skip if it looks like a header (ends with :)
                if item.endswith(":"):
                    continue
                    
                # Handle "Clean Item (Comment)" format -> "Clean Item"
                if "(" in item:
                    item = item.split("(")[0].strip()
                
                if item:
                    items.append(item)
    return items

def print_deals(title, df):
    print(f"\n{'='*len(title)}")
    print(title)
    print(f"{'='*len(title)}")
    
    if df.empty:
        print("No deals found.")
        return

    # Select relevant columns
    cols = ['Item', 'Zone', 'Buy_Price', 'Ref_Price', 'Margin', 'Margin_%', 'Stock']
    if 'Score' in df.columns:
        cols = ['Item', 'Zone', 'Buy_Price', 'Avg_Sale_Price', 'Unit_Profit', 'Margin', 'Score', 'Units_Sold']
        # Rename for consistency in printing if needed, or just print as is
    
    # Filter columns that exist
    display_cols = [c for c in cols if c in df.columns]
    
    # Formatting
    pd.set_option('display.max_rows', 50)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:.2f}'.format)
    
    print(df[display_cols].to_string(index=False))

def main():
    stock_items = load_stock_list()
    print(f"Loaded {len(stock_items)} items from stock list.")
    
    analyzer = MarketAnalyzer(DATA_DIR)
    
    # --- PART 1: Volvestre & Gravas (Items < Median) ---
    print("\nScanning for Stock List items below median in Volvestre & Gravas...")
    
    # Volvestre
    print("\n--- Volvestre ---")
    volvestre_deals = analyzer.scan_shopping_list(stock_items, "Volvestre")
    print_deals("Deals in Volvestre (Stock List)", volvestre_deals)
    
    # Gravas
    print("\n--- Gravas ---")
    gravas_deals = analyzer.scan_shopping_list(stock_items, "Gravas")
    print_deals("Deals in Gravas (Stock List)", gravas_deals)
    
    # --- PART 2: Arbitrage (Buy in Volvestre/Gravas -> Sell in Aven) ---
    print("\nScanning for Arbitrage: Buy in Volvestre/Gravas -> Sell in Aven (Non-Stock Items)...")
    
    if os.path.exists(analyzer.listings_file):
        df = pd.read_parquet(analyzer.listings_file)
        
        # 1. Identify Non-Stock Items
        stock_items_lower = set([i.lower() for i in stock_items])
        df['Item_Lower'] = df['Item'].str.lower()
        non_stock_df = df[~df['Item_Lower'].isin(stock_items_lower)].copy()
        
        # 2. Get Buy Listings (Volvestre/Gravas)
        buy_mask = non_stock_df['Zone'].str.contains("Volvestre|Gravas", case=False, na=False)
        buy_df = non_stock_df[buy_mask].copy()
        
        # 3. Get Sell Reference (Aven Median)
        sell_mask = df['Zone'].str.contains("Aven", case=False, na=False)
        aven_df = df[sell_mask].copy()
        
        if not aven_df.empty:
            # Calculate Aven Median Price per Item
            if 'UnitPrice' not in aven_df.columns:
                aven_df['UnitPrice'] = aven_df['Price'] / aven_df['Amount']
                
            aven_prices = aven_df.groupby('Item_Lower')['UnitPrice'].median().reset_index()
            aven_prices.rename(columns={'UnitPrice': 'Aven_Price'}, inplace=True)
            
            # 4. Merge
            merged = buy_df.merge(aven_prices, on='Item_Lower', how='inner')
            
            # 5. Calculate Metrics
            if 'UnitPrice' not in merged.columns:
                merged['UnitPrice'] = merged['Price'] / merged['Amount']
                
            merged['Margin'] = merged['Aven_Price'] - merged['UnitPrice']
            merged['Margin_%'] = (merged['Margin'] / merged['Aven_Price']) * 100
            merged['Potential_Profit'] = merged['Margin'] * merged['Amount']
            
            # Filter profitable deals
            opportunities = merged[merged['Margin'] > 0].sort_values('Potential_Profit', ascending=False)
            
            # Format and Print
            opportunities.rename(columns={'UnitPrice': 'Buy_Price', 'Aven_Price': 'Ref_Price', 'Amount': 'Stock'}, inplace=True)
            
            print_deals("Arbitrage Opportunities (Buy Volvestre/Gravas -> Sell Aven)", opportunities.head(20))
            
        else:
            print("No listings found in Aven to compare against.")

        # --- PART 3: High Tier Weapons & Armor (Volvestre/Gravas) ---
        print("\nScanning for High Tier (>= 4) Weapons & Armor in Volvestre/Gravas...")
        
        # Keywords for weapons and armor
        gear_keywords = [
            'Sword', 'Mace', 'Axe', 'Spear', 'Bow', 'Crossbow', 'Shield', 
            'Helm', 'Chest', 'Legs', 'Boots', 'Gloves', 'Pauldrons', 
            'Tunic', 'Gambeson', 'Chainmail', 'Plate', 'Cuirass', 'Greaves', 'Gauntlets'
        ]
        
        # Identify high tier items
        high_tier_gear = []
        for item, tier in analyzer.item_tiers.items():
            if tier >= 4:
                # Check if item name contains any keyword
                if any(kw.lower() in item.lower() for kw in gear_keywords):
                    high_tier_gear.append(item)
                    
        if not high_tier_gear:
            print("No High Tier (>= 4) Weapons/Armor identified in catalog.")
        else:
            # Filter listings for these items in Volvestre/Gravas
            # Use original df (all items)
            buy_mask_gear = df['Zone'].str.contains("Volvestre|Gravas", case=False, na=False) & \
                            df['Item'].isin(high_tier_gear)
            gear_df = df[buy_mask_gear].copy()
            
            if gear_df.empty:
                print("No High Tier Weapons/Armor found in Volvestre/Gravas.")
            else:
                if 'UnitPrice' not in gear_df.columns:
                    gear_df['UnitPrice'] = gear_df['Price'] / gear_df['Amount']
                
                # We might not have a reference price, so just list them sorted by UnitPrice (Cheapest First)
                gear_display = gear_df[['Item', 'Zone', 'UnitPrice', 'Amount', 'SellerHash']].sort_values(['Item', 'UnitPrice'])
                gear_display.rename(columns={'UnitPrice': 'Buy_Price', 'Amount': 'Stock', 'SellerHash': 'Seller'}, inplace=True)
                
                # Add 'Tier' column for display if possible (it's 4+ anyway)
                gear_display['Tier'] = gear_display['Item'].map(analyzer.item_tiers)
                
                print_deals("High Tier Weapons & Armor in Volvestre/Gravas", gear_display)
    else:
        print("Listings file not found.")

if __name__ == "__main__":
    main()
