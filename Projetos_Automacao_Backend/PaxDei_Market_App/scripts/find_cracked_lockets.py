import os
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LISTINGS_FILE = os.path.join(DATA_DIR, "selene_latest.parquet")

def main():
    if not os.path.exists(LISTINGS_FILE):
        print("Data file not found. Run sync_data.py first.")
        return

    df = pd.read_parquet(LISTINGS_FILE)
    
    # Calculate Unit Price
    if 'UnitPrice' not in df.columns:
        df['UnitPrice'] = df['Price'] / df['Amount']
        
    # Filter for Cracked Locket
    item_name = "Cracked Locket"
    df_item = df[df['Item'] == item_name].copy()
    
    if df_item.empty:
        print(f"No listings found for {item_name}.")
        return

    # Calculate Median Price
    median_price = df_item['UnitPrice'].median()
    print(f"Global Median Price for {item_name}: {median_price:.2f}")
    
    # Filter below median
    deals_df = df_item[df_item['UnitPrice'] < median_price].copy()
    
    if deals_df.empty:
        print("No deals found below median price.")
        return

    # Aggregate by Zone and Price to show Total Quantity
    aggregated = deals_df.groupby(['Item', 'Zone', 'UnitPrice']).agg({
        'Amount': 'sum',
        'Price': 'sum' # Total gold for all items in that bucket
    }).reset_index()
    
    # Sort by Total Amount descending
    aggregated.sort_values(by=['Amount', 'UnitPrice'], ascending=[False, True], inplace=True)
    
    print("\n==========================================================")
    print(f" AGGREGATED DEALS FOR {item_name.upper()}")
    print(f" (BELOW MEDIAN '{median_price:.2f}')")
    print(" Sorted by Total Quantity per Zone/Price")
    print("==========================================================")
    
    # Rename columns for clarity
    aggregated.rename(columns={'Amount': 'Total_Qty', 'Price': 'Total_Gold'}, inplace=True)
    
    output_cols = ['Item', 'Zone', 'Total_Qty', 'UnitPrice', 'Total_Gold']
    print(aggregated[output_cols].head(30).to_string(index=False))

if __name__ == "__main__":
    main()
