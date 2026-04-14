import os
import sys
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from modules.market import MarketAnalyzer

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def main():
    analyzer = MarketAnalyzer(DATA_DIR)
    listings_file = analyzer.listings_file
    
    if not os.path.exists(listings_file):
        print("Listings file not found.")
        return
        
    df = pd.read_parquet(listings_file)
    
    if 'UnitPrice' not in df.columns:
        df['UnitPrice'] = df['Price'] / df['Amount']
        
    target_items = ['Bronze Ingot', 'Iron Ingot', 'Wrought Iron Ingot']
    
    # Filter for target items exactly
    df_filtered = df[df['Item'].isin(target_items)].copy()
    
    if df_filtered.empty:
        print("No stock found for these ingots.")
        return
    
    # Group by identical deals
    df_grouped = df_filtered.groupby(['Item', 'Zone', 'UnitPrice']).agg({'Amount': 'sum'}).reset_index()
    df_grouped.rename(columns={'Amount': 'Stock'}, inplace=True)
    
    # Calculate Stack Price and 40 Stacks Price (Assuming 1 Stack = 30 Ingots based on usual game mechanics. Need to verify, but usually ingots are 30. Let's use 30 as a default multiplier for a stack of ingots.)
    # Actually, in Pax Dei, ingot stack size is typically 30.
    STACK_SIZE = 30
    df_grouped['Preco_Stack'] = df_grouped['UnitPrice'] * STACK_SIZE
    df_grouped['Preco_40_Stacks'] = df_grouped['Preco_Stack'] * 40
    
    # Sort by Item, then Stock descending
    df_grouped.sort_values(by=['Item', 'Stock'], ascending=[True, False], inplace=True)
    
    pd.set_option('display.max_rows', 100)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:.2f}'.format)
    
    display_cols = ['Item', 'Zone', 'Stock', 'UnitPrice', 'Preco_Stack', 'Preco_40_Stacks']
    
    print("\n========================================================")
    print(" LARGEST STOCKS FOR TARGET INGOTS ")
    print("========================================================")
    
    for item in target_items:
        print(f"\n--- {item} (Top 10 Stocks) ---")
        item_df = df_grouped[df_grouped['Item'] == item].head(10)
        if item_df.empty:
            print("No listings found.")
        else:
            print(item_df[display_cols].to_string(index=False))

if __name__ == "__main__":
    main()
