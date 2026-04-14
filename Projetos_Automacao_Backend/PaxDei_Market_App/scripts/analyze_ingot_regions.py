import os
import pandas as pd
import sys

DATA_DIR = "d:/PaxDei_Tool/data"
LATEST_FILE = os.path.join(DATA_DIR, "selene_latest.parquet")

def analyze_ingots_by_region():
    if not os.path.exists(LATEST_FILE):
        print("Market data not found.")
        return

    df = pd.read_parquet(LATEST_FILE)
    
    if 'UnitPrice' not in df.columns:
        df['UnitPrice'] = df['Price'] / df['Amount']

    target_items = ['Wrought Iron Ingot', 'Steel Ingot', 'Iron Ingot', 'Bronze Ingot']
    
    # Filter targets
    df_filtered = df[df['Item'].isin(target_items)].copy()
    
    if df_filtered.empty:
        print("No stock found for these ingots.")
        return
        
    # Calculate Global Medians
    median_prices = df_filtered.groupby('Item')['UnitPrice'].median().to_dict()
    
    with open("d:/PaxDei_Tool/ingot_region_deals.txt", "w", encoding='utf-8') as f:
        f.write("=== PRECOS MEDIANOS GLOBAIS ===\n")
        for item in target_items:
            median = median_prices.get(item, 0)
            f.write(f"{item:<20}: {median:.2f}g\n")
        
        deals = []
        for _, row in df_filtered.iterrows():
            item = row['Item']
            price = row['UnitPrice']
            median = median_prices.get(item, 0)
            
            # Considering matches exactly at or below the median
            if price <= median:
                deals.append(row)
                
        if not deals:
            f.write("\nNenhum ingot encontrado abaixo ou igual a mediana.\n")
            return
            
        df_deals = pd.DataFrame(deals)
        
        # Extract Region from Zone: "inis_gallia-langres" -> "Inis Gallia"
        df_deals['Region'] = df_deals['Zone'].apply(lambda z: z.split('-')[0].replace('_', ' ').title() if '-' in z else z)
        
        grouped = df_deals.groupby(['Region', 'Item'])['Amount'].sum().reset_index()
        
        pivot_df = grouped.pivot(index='Region', columns='Item', values='Amount').fillna(0).astype(int)
        
        for item in target_items:
            if item not in pivot_df.columns:
                pivot_df[item] = 0
                
        pivot_df = pivot_df[target_items]
        
        # Sort regions based on user preference: Wrought > Steel > Iron > Bronze
        pivot_df.sort_values(by=target_items, ascending=[False, False, False, False], inplace=True)
        
        f.write("\n=== REGIOES COM MAIOR ESTOQUE BARATO (<= MEDIANA) ===\n")
        f.write("Dados combinam estoques de vales da mesma provincia.\n")
        f.write("Ordenado pela sua prioridade (Wrought > Steel > Iron > Bronze).\n\n")
        
        f.write(pivot_df.to_string() + "\n")
        
        f.write("\n\n=== DETALHAMENTO DOS VALES ===\n")
        top_regions = pivot_df.index.tolist()
        
        df_deals['ItemCat'] = pd.Categorical(df_deals['Item'], categories=target_items, ordered=True)
        
        for region in top_regions:
            f.write(f"\n📍 {region.upper()}\n")
            region_df = df_deals[df_deals['Region'] == region]
            
            # Group by valley and price
            valley_group = region_df.groupby(['Zone', 'Item', 'ItemCat', 'UnitPrice'])['Amount'].sum().reset_index()
            valley_group = valley_group.sort_values(by=['ItemCat', 'UnitPrice', 'Amount'], ascending=[True, True, False])
            
            for _, row in valley_group.iterrows():
                 f.write(f"  - {row['Item']:<20} | {row['Zone']:<22} | Qtd: {row['Amount']:<4} | Preco: {row['UnitPrice']:.2f}g\n")

    print("Analysis saved to ingot_region_deals.txt")

if __name__ == "__main__":
    analyze_ingots_by_region()
