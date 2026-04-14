import os
import sys
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from modules.market import MarketAnalyzer

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'ingot_deals.txt')

def main():
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        analyzer = MarketAnalyzer(DATA_DIR)
        listings_file = analyzer.listings_file
        
        if not os.path.exists(listings_file):
            f.write("Listings file not found. Run sync_data.py first.\n")
            return
            
        df = pd.read_parquet(listings_file)
        
        if 'UnitPrice' not in df.columns:
            df['UnitPrice'] = df['Price'] / df['Amount']
            
        target_items = ['Bronze Ingot', 'Iron Ingot', 'Wrought Iron Ingot']
        
        # Filter for target items
        df_filtered = df[df['Item'].isin(target_items)].copy()
        
        if df_filtered.empty:
            f.write("No stock found for these ingots.\n")
            return
            
        # Calculate global median price for each ingot type
        median_prices = df_filtered.groupby('Item')['UnitPrice'].median().to_dict()
        
        f.write("\n========================================================\n")
        f.write(" MEDIAN PRICES \n")
        f.write("========================================================\n")
        for item, median in median_prices.items():
            f.write(f"{item}: {median:.2f}\n")

        # Group by identical deals to get total stock
        df_grouped = df_filtered.groupby(['Item', 'Zone', 'UnitPrice']).agg({'Amount': 'sum'}).reset_index()
        df_grouped.rename(columns={'Amount': 'Stock'}, inplace=True)
        
        # Check against median
        deals = []
        for idx, row in df_grouped.iterrows():
            item = row['Item']
            zone = row['Zone']
            unit_price = row['UnitPrice']
            stock = row['Stock']
            
            median = median_prices.get(item, 0)
            
            # Allowing up to median 
            discount_pct = ((median - unit_price) / median) * 100 if median > 0 else 0
            
            if unit_price <= median * 1.05: # Changed filter to use <= median price exactly
                 deals.append({
                     'Item': item,
                     'Zone': zone,
                     'UnitPrice': round(unit_price, 2),
                     'MedianPrice': round(median, 2),
                     'Discount_%': round(discount_pct, 1),
                     'Stock': stock
                 })

        deals_df = pd.DataFrame(deals)
        if deals_df.empty:
            f.write("\nNo deals found below or at median price.\n")
            return

        # User prefers quantity
        deals_df.sort_values(by=['Item', 'Stock', 'UnitPrice'], ascending=[True, False, True], inplace=True)
        
        pd.set_option('display.max_rows', 100)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.float_format', '{:.2f}'.format)
        
        display_cols = ['Item', 'Zone', 'Stock', 'UnitPrice', 'MedianPrice', 'Discount_%']
        
        f.write("\n=============================================================================================\n")
        f.write(" INGOT DEALS (AT OR BELOW MEDIAN, SORTED BY QUANTITY DESCENDING) \n")
        f.write("=============================================================================================\n")
        
        for item in target_items:
            f.write(f"\n--- {item} ---\n")
            item_df = deals_df[deals_df['Item'] == item]
            if item_df.empty:
                f.write("No good deals below median price found.\n")
            else:
                f.write(item_df[display_cols].to_string(index=False) + "\n")

    print(f"Analysis saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
