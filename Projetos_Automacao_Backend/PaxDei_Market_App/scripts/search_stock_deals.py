import os
import sys
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from modules.market import MarketAnalyzer

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
            if line.startswith("- ") or line.startswith("* "):
                item = line[2:].strip()
                if item.startswith("**") and item.endswith("**"):
                    continue
                if item.startswith("**") and item.endswith(":"):
                     continue
                item = item.replace("**", "")
                if item.endswith(":"):
                    continue
                if "(" in item:
                    item = item.split("(")[0].strip()
                if item:
                    items.append(item)
    return items

def main():
    stock_items = load_stock_list()
    print(f"Loaded {len(stock_items)} items from stock list.")
    
    analyzer = MarketAnalyzer(DATA_DIR)
    listings_file = analyzer.listings_file
    
    if not os.path.exists(listings_file):
        print("Listings file not found. Run sync_data.py first.")
        return
        
    df = pd.read_parquet(listings_file)
    
    # Calculate Unit Price
    if 'UnitPrice' not in df.columns:
        df['UnitPrice'] = df['Price'] / df['Amount']
        
    # Filter by stock items (case insensitive)
    stock_items_lower = {i.lower(): i for i in stock_items}
    df['Item_Lower'] = df['Item'].str.lower()
    
    mask_stock = df['Item_Lower'].isin(stock_items_lower.keys())
    df_stock = df[mask_stock].copy()
    
    if df_stock.empty:
        print("No stock items found in current listings.")
        return

    # 1. Calculate Global Median Price for these items
    median_prices = df_stock.groupby('Item_Lower')['UnitPrice'].median().to_dict()
    
    # 2. Add properties to deals
    deals = []
    for idx, row in df_stock.iterrows():
        item_lower = row['Item_Lower']
        item_name = row['Item']
        amount = row['Amount']
        unit_price = row['UnitPrice']
        zone = row['Zone']
        
        median = median_prices.get(item_lower, 0)
        
        if unit_price < median:
            margin = median - unit_price
            margin_pct = (margin / median) * 100
            
            deals.append({
                'Item': item_name,
                'Zone': zone,
                'Stock': amount,
                'UnitPrice': round(unit_price, 2),
                'MedianPrice': round(median, 2),
                'Discount_%': round(margin_pct, 1),
                'Is_Ingot': 'ingot' in item_lower
            })
            
    deals_df = pd.DataFrame(deals)
    if deals_df.empty:
        print("No deals found below median price.")
        return
        
    # 3. Filter minimum 20 stacks
    deals_df = deals_df[deals_df['Stock'] >= 20]
    
    if deals_df.empty:
        print("No deals found with at least 20 stacks below median price.")
        return
        
    # Agrupar ofertas idênticas para limpar o output
    deals_agrupados = deals_df.groupby(['Item', 'Zone', 'UnitPrice', 'MedianPrice', 'Discount_%', 'Is_Ingot']).agg({'Stock': 'sum'}).reset_index()
    
    # Sort: Ingots first, then Discount %
    deals_agrupados.sort_values(by=['Is_Ingot', 'Discount_%'], ascending=[False, False], inplace=True)
    
    pd.set_option('display.max_rows', 100)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    # Reorder columns
    display_cols = ['Item', 'Zone', 'UnitPrice', 'MedianPrice', 'Discount_%', 'Stock']
    
    print("\n======================================================================")
    print(" STOCK LIST DEALS (BELOW MEDIAN, >= 20 STACKS, GROUPED BY ZONE/PRICE) ")
    print("======================================================================")
    print(deals_agrupados[display_cols].head(100).to_string(index=False))
    
if __name__ == "__main__":
    main()
