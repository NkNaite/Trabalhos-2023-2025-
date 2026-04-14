import os
import pandas as pd

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LISTINGS_FILE = os.path.join(DATA_DIR, "selene_latest.parquet")
STOCK_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Guia_Estoque_Crafting.md")

STACK_SIZE = 20

def load_stock_items():
    if not os.path.exists(STOCK_FILE):
        return []
    items = []
    with open(STOCK_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("- "):
                item = line[2:].strip()
                # Clean up bolding and parentheses
                item = item.replace("**", "")
                if "(" in item:
                    item = item.split("(")[0].strip()
                if item:
                    items.append(item)
    return items

def main():
    stock_list = load_stock_items()
    if not stock_list:
        print("Stock list is empty or file not found.")
        return

    if not os.path.exists(LISTINGS_FILE):
        print("Data file not found. Run sync_data.py.")
        return

    df = pd.read_parquet(LISTINGS_FILE)
    
    # Unit Price calculation if not present
    if 'UnitPrice' not in df.columns:
        df['UnitPrice'] = df['Price'] / df['Amount']

    # Filter for stock items
    stock_list_lower = [i.lower() for i in stock_list]
    df['Item_Lower'] = df['Item'].str.lower()
    df_stock = df[df['Item_Lower'].isin(stock_list_lower)].copy()

    if df_stock.empty:
        print("No items from stock list found for sale.")
        return

    # Calculate Global Median Price for each item
    medians = df_stock.groupby('Item')['UnitPrice'].median().to_dict()

    # Define "Below Median" filter
    def is_below_median(row):
        median = medians.get(row['Item'], 0)
        return row['UnitPrice'] < median

    df_deals = df_stock[df_stock.apply(is_below_median, axis=1)].copy()

    # Calculate special prices
    df_deals['Price_20_Stacks'] = df_deals['UnitPrice'] * (20 * STACK_SIZE)
    df_deals['Price_40_Stacks'] = df_deals['UnitPrice'] * (40 * STACK_SIZE)
    df_deals['Median'] = df_deals['Item'].map(medians)

    # Separate Ingots, Lavedan, and others
    is_ingot = df_deals['Item'].str.contains('Ingot', case=False)
    is_lavedan = df_deals['Zone'].str.contains('lavedan', case=False)
    
    df_lavedan = df_deals[is_lavedan].copy()
    df_ingots = df_deals[is_ingot & ~is_lavedan].copy()
    df_others = df_deals[~is_ingot & ~is_lavedan].copy()

    # Grouping to clean output
    def format_deals(df_group, title, show_median=True):
        if df_group.empty:
            print(f"\n--- {title} (No deals found) ---")
            return

        # Aggregate by Item, Zone, and Price
        agg_cols = ['Item', 'Zone', 'UnitPrice', 'Median', 'Price_20_Stacks', 'Price_40_Stacks']
        aggregated = df_group.groupby(agg_cols).agg({'Amount': 'sum'}).reset_index()
        
        # Apply Rule: Total Available >= 5 stacks (100 units)
        MIN_TOTAL_QTY = 5 * STACK_SIZE
        aggregated = aggregated[aggregated['Amount'] >= MIN_TOTAL_QTY].copy()

        if aggregated.empty:
            print(f"\n--- {title} (No deals with total > 5 stacks) ---")
            return

        print(f"\n==============================================================================================================================")
        print(f" {title.upper()} (Min 5 Stacks Total, Below Median) ")
        print(f"==============================================================================================================================")
        
        # Sort by Item and UnitPrice
        aggregated = aggregated.sort_values(by=['Item', 'UnitPrice'])
        
        # Rename Amount for clarity
        aggregated.rename(columns={'Amount': 'Total_Avail'}, inplace=True)

        display_cols = ['Item', 'Zone', 'Total_Avail', 'UnitPrice', 'Median', 'Price_20_Stacks', 'Price_40_Stacks']
        if not show_median:
             display_cols.remove('Median')

        print(aggregated[display_cols].to_string(index=False))

    format_deals(df_others, "General Market Deals", show_median=False)
    format_deals(df_ingots, "Ingot Deals", show_median=True)
    format_deals(df_lavedan, "Lavedan Special List", show_median=True)

if __name__ == "__main__":
    main()
