import os
import pandas as pd
import json
import sys

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LISTINGS_FILE = os.path.join(DATA_DIR, "selene_latest.parquet")
MEDIANS_FILE = os.path.join(DATA_DIR, "7d_medians.json")
STOCK_FILE = os.path.join(BASE_DIR, "Guia_Estoque_Crafting.md")

def load_stock_config():
    if not os.path.exists(STOCK_FILE):
        return {}
    
    config = {}
    with open(STOCK_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("- "):
                line = line[2:].strip()
                if "(" in line and ")" in line:
                    item_parts = line.split("(")
                    item_name = item_parts[0].strip()
                    stack_size_str = item_parts[1].split(")")[0].strip()
                    try:
                        stack_size = int(stack_size_str)
                        config[item_name.lower()] = {
                            "name": item_name,
                            "stack_size": stack_size
                        }
                    except ValueError:
                        continue
    return config

def main():
    print("Checking for stock opportunities based on Guia_Estoque_Crafting.md...")
    stock_config = load_stock_config()
    if not stock_config:
        print("Error: Could not load stock config from Guia_Estoque_Crafting.md.")
        return

    if not os.path.exists(LISTINGS_FILE):
        print("Error: Listings file not found (selene_latest.parquet).")
        return

    if not os.path.exists(MEDIANS_FILE):
        print("Error: 7d Medians file not found (7d_medians.json).")
        return

    # Load data
    df = pd.read_parquet(LISTINGS_FILE)
    with open(MEDIANS_FILE, 'r', encoding='utf-8') as f:
        median_data = json.load(f)
        medians_global = median_data.get('global_7d', {})

    # Calculate UnitPrice
    if 'UnitPrice' not in df.columns:
        df['UnitPrice'] = df['Price'] / df['Amount']

    # Normalize medians for lookup
    medians_lower = {k.lower(): v for k, v in medians_global.items()}

    # Filter for items in stock guide
    df['Item_Lower'] = df['Item'].str.lower()
    df_stock = df[df['Item_Lower'].isin(stock_config.keys())].copy()

    if df_stock.empty:
        print("No stock items found in listings.")
        return

    # Map Median and calculate stacks
    df_stock['Median_7d'] = df_stock['Item_Lower'].map(medians_lower)
    
    # Filter only those that have a reference median
    df_stock = df_stock[df_stock['Median_7d'].notnull()].copy()
    
    # Calculate stacks based on guide sizes
    def get_stacks(row):
        item_lower = row['Item_Lower']
        size = stock_config[item_lower]['stack_size']
        return row['Amount'] / size

    df_stock['Stacks'] = df_stock.apply(get_stacks, axis=1)
    df_stock['Discount_%'] = ((df_stock['Median_7d'] - df_stock['UnitPrice']) / df_stock['Median_7d']) * 100

    # APPLICATION OF GUIDE RULES
    # RULE 1: Minimum 50% discount vs 7d Median
    df_deals = df_stock[df_stock['Discount_%'] >= 49.5].copy() # Using 49.5 for rounding protection

    if df_deals.empty:
        print("No items found with 50% discount or more compared to 7d Median.")
        return

    # Define if it's a Token (Exception rule)
    df_deals['Is_Token'] = df_deals['Item'].str.contains('Token', case=False)

    # Opportunity Validation (Aggregate by Zone/Seller)
    # The rule says: "Volume Mínimo: 20 stacks... (pode ser a soma de diferentes itens da lista no mesmo vale)"
    # We group by Zone to find vendors that have enough stock of guide items.
        # Opportunity Validation (Grouping by Seller in Zone)
    # Each Seller identified by SellerHash within a Zone
    
    all_opportunities = []

    # Filter to group by Zone and SellerHash
    # First, separate deals from tokens vs total volume
    
    # We group by Zone and SellerHash to find vendors that have enough stock
    seller_groups = df_deals.groupby(['Zone', 'SellerHash'])
    
    for (zone, seller), group in seller_groups:
        total_stacks_for_seller = group['Stacks'].sum()
        
        # RULE: Total Volume per Seller >= 20 stacks
        # EXCEPTION: Tokens Satisfying 50% discount and >= 1 stack
        
        # Find tokens that already satisfy 1 stack in this group
        token_deals = group[group['Is_Token'] & (group['Stacks'] >= 1.0)]
        for _, row in token_deals.iterrows():
            all_opportunities.append({
                'Item': row['Item'],
                'Zone': zone,
                'Seller': seller,
                'Stacks': round(row['Stacks'], 1),
                'UnitPrice': round(row['UnitPrice'], 2),
                'Median_7d': round(row['Median_7d'], 2),
                'Discount_%': round(row['Discount_%'], 1),
                'Reason': 'Token Stand (>= 1 stack)'
            })

        if total_stacks_for_seller >= 20.0:
            # Add all items from this seller that satisfy conditions
            # (Avoid duplication if it was a token already added)
            already_added_items = set([o['Item'] for o in all_opportunities if o['Seller'] == seller and o['Zone'] == zone])
            
            non_added_rows = group[~group['Item'].isin(already_added_items)]
            for _, row in non_added_rows.iterrows():
                all_opportunities.append({
                    'Item': row['Item'],
                    'Zone': zone,
                    'Seller': seller,
                    'Stacks': round(row['Stacks'], 1),
                    'UnitPrice': round(row['UnitPrice'], 2),
                    'Median_7d': round(row['Median_7d'], 2),
                    'Discount_%': round(row['Discount_%'], 1),
                    'Reason': f'Major Stand Opp (Seller Total: {round(total_stacks_for_seller, 1)} Stacks)'
                })

    if not all_opportunities:
        print("No major stands (>= 20 stacks) or token opportunities found within parameters.")
        return

    # GROUPING BY SELLER FOR "STANDS" (VIAGENS)
    # Convert back to DataFrame
    result_df = pd.DataFrame(all_opportunities)
    
    # AGGREGATE IDENTICAL ITEMS PER SELLER (summing stacks)
    # Group by Zone, Seller, and Item
    item_aggregation = result_df.groupby(['Zone', 'Seller', 'Item']).agg({
        'Stacks': 'sum',
        'UnitPrice': 'min', # Best price
        'Median_7d': 'first',
        'Discount_%': 'max', # Best discount
        'Reason': 'first'
    }).reset_index()
    
    # Calculate total stacks per seller again from the aggregated items
    seller_totals = item_aggregation.groupby(['Zone', 'Seller']).agg({
        'Stacks': 'sum',
        'Item': 'count',
        'Discount_%': 'mean'
    }).rename(columns={'Item': 'Num_Items', 'Stacks': 'Total_Stacks_Seller', 'Discount_%': 'Avg_Discount'})
    
    # Sort sellers by Total Stacks descending
    seller_totals.sort_values(by='Total_Stacks_Seller', ascending=False, inplace=True)

    # Save full results to file
    full_output_path = os.path.join(BASE_DIR, "results_guia_estoque.txt")
    with open(full_output_path, 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("                      RELATÓRIO DE BANCAS (STANDS): MÍNIMO 20 STACKS\n")
        f.write("="*100 + "\n")
        
        for (zone, seller), stats in seller_totals.iterrows():
            f.write(f"\n📍 LOCAL: {zone.upper()} | VENDEDOR: {seller[:15]}...\n")
            f.write(f"   Volume na Banca: {round(stats['Total_Stacks_Seller'], 1)} Stacks | Itens Diferentes: {int(stats['Num_Items'])}\n")
            f.write(f"   {'-'*80}\n")
            seller_items = item_aggregation[(item_aggregation['Zone'] == zone) & (item_aggregation['Seller'] == seller)].sort_values(by='Stacks', ascending=False)
            f.write(seller_items[['Item', 'Stacks', 'UnitPrice', 'Median_7d', 'Discount_%']].to_string(index=False) + "\n")
            f.write(f"   {'-'*80}\n")

    print("\n" + "="*100)
    print("                      BANCAS RECOMMENDED (GUIA DE ESTOQUE)")
    print("   Total de Stacks por Vendedor >= 20 (ou Tokens)")
    print("="*100)
    
    # Show Top 8 Sellers/Stands
    top_stands = seller_totals.head(10)
    if top_stands.empty:
        print("Nenhuma banca encontrada com o volume mínimo exigido de 20 stacks.")
    else:
        for (zone, seller), stats in top_stands.iterrows():
            print(f"\n🚀 REGIAO: {zone.upper()} | BANCA: {seller[:10]}...")
            print(f"   TOTAL: {round(stats['Total_Stacks_Seller'], 1)} Stacks | ITENS: {int(stats['Num_Items'])} | DESC. MÉDIO: {round(stats['Avg_Discount'], 1)}%")
            
            # Show up to 10 items for this seller
            seller_items = item_aggregation[(item_aggregation['Zone'] == zone) & (item_aggregation['Seller'] == seller)].sort_values(by='Stacks', ascending=False).head(10)
            print("   Breakdown por Item:")
            for _, row in seller_items.iterrows():
                print(f"     - {row['Item']}: {round(row['Stacks'], 1)} stacks")
    
    print("\n" + "="*100)
    print(f"Relatório detalhado por item salvo em: {full_output_path}")

if __name__ == "__main__":
    main()
