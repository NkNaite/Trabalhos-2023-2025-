import pandas as pd
import os
from datetime import datetime, timedelta

DATA_DIR = r"d:\PaxDei_Tool\data"
HISTORY_FILE = os.path.join(DATA_DIR, "full_history.parquet")

def check_item_liquidity(item_name, days=7):
    if not os.path.exists(HISTORY_FILE):
        print("History file not found.")
        return

    cutoff = datetime.now() - timedelta(days=days)
    
    # Load only what we need
    print(f"Reading history for items containing '{item_name}' since {cutoff.date()}...")
    
    # We load everything matching and filter locally to be sure
    df_all = pd.read_parquet(
        HISTORY_FILE, 
        columns=['Item', 'SnapshotDate', 'ListingID', 'Amount', 'Price', 'Zone'],
        filters=[('SnapshotDate', '>=', cutoff)]
    )
    
    df = df_all[df_all['Item'].str.contains(item_name, case=False, na=False)].copy()
    
    if df.empty:
        print(f"Nenhum registro encontrado para {item_name} nos últimos {days} dias.")
        return

    # Info about listings
    latest_snap = df['SnapshotDate'].max()
    current_listings = df[df['SnapshotDate'] == latest_snap]
    print(f"Atualmente há {len(current_listings)} listagens em: {', '.join(current_listings['Zone'].unique())}")

    # Identify sales (ListingIDs that disappear between snapshots)
    snaps = sorted(df['SnapshotDate'].unique())
    print(f"Analisando {len(snaps)} snapshots históricos...")
    
    total_sold = 0
    total_volume = 0
    
    for i in range(len(snaps)-1):
        # A sale happens if an ID is present in snap i but not in snap i+1
        # BUT only if it didn't just expire. Snapshots are usually hourly.
        current_snap = snaps[i]
        next_snap = snaps[i+1]
        
        current_ids = set(df[df['SnapshotDate'] == current_snap]['ListingID'])
        next_ids = set(df[df['SnapshotDate'] == next_snap]['ListingID'])
        
        sold_ids = current_ids - next_ids
        if sold_ids:
            # We filter out IDs that might have just moved? 
            # In this simple model, we count as sold.
            sold_df = df[(df['SnapshotDate'] == current_snap) & (df['ListingID'].isin(sold_ids))]
            total_sold += sold_df['Amount'].sum() if 'Amount' in sold_df.columns else len(sold_df)
            total_volume += sold_df['Price'].sum()

    print(f"\n--- Liquidez: {item_name} (Ultimos {days} dias) ---")
    print(f"Total de Unidades Vendidas: {total_sold}")
    print(f"Volume Total de Ouro: {total_volume:,.2f}g")
    
    if total_sold > 0:
        print(f"Media de Preço de Venda: {total_volume/total_sold:,.2f}g")
        print("Parece que há movimentação no mercado!")
    else:
        print("Nenhuma venda detectada no período.")

if __name__ == "__main__":
    check_item_liquidity("Iron Ore", days=3)
