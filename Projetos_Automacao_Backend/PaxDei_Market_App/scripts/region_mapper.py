import os
import glob
import pandas as pd
from datetime import datetime, timedelta
import sys

# Add src to path to import MarketAnalyzer for tiers
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
try:
    from modules.market import MarketAnalyzer
except ImportError:
    print("Could not import MarketAnalyzer")
    sys.exit(1)

def get_snapshot_files(history_dir):
    search_path = os.path.join(history_dir, "**", "*.parquet")
    files = glob.glob(search_path, recursive=True)
    
    parsed_files = []
    for f in files:
        basename = os.path.basename(f)
        timestamp_str = basename.replace("market_", "").replace(".parquet", "")
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M")
            parsed_files.append((dt, f))
        except ValueError:
            pass
            
    parsed_files.sort(key=lambda x: x[0])
    return parsed_files

def find_target_snapshots(parsed_files):
    if not parsed_files: return None, None, None
    
    t0_dt, t0_file = parsed_files[-1]
    
    target_5d = t0_dt - timedelta(days=5)
    target_20d = t0_dt - timedelta(days=20)
    
    # Extract closest file
    t5_file = None
    t20_file = None
    
    # 5 days ago
    closest_5 = min(parsed_files, key=lambda x: abs(x[0] - target_5d))
    if abs(closest_5[0] - target_5d) <= timedelta(days=2):
        t5_file = closest_5[1]
        
    # 20 days ago
    closest_20 = min(parsed_files, key=lambda x: abs(x[0] - target_20d))
    if abs(closest_20[0] - target_20d) <= timedelta(days=2):
        t20_file = closest_20[1]
        
    return t0_file, t5_file, t20_file

def clean_zone(zone_str):
    if pd.isna(zone_str): return "Unknown"
    parts = str(zone_str).split('-')
    return parts[-1].strip().title()

def get_churn_stats(df_old, df_new):
    if df_old is None or df_new is None:
        return pd.DataFrame()
        
    # Standardize Zone
    df_old['Vale'] = df_old['Zone'].apply(clean_zone)
    df_new['Vale'] = df_new['Zone'].apply(clean_zone)
    
    old_ids = set(df_old['ListingID'].dropna().unique())
    new_ids = set(df_new['ListingID'].dropna().unique())
    sold_ids = old_ids - new_ids
    
    if not sold_ids:
        return pd.DataFrame()
        
    sold_df = df_old[df_old['ListingID'].isin(sold_ids)].copy()
    
    # Some older schemas might not have Amount or UnitPrice correctly populated 
    if 'Amount' not in sold_df.columns:
        sold_df['Amount'] = 1
    
    stats = sold_df.groupby('Vale').agg(
        Churn_Qty=('Amount', 'sum'),
        Churn_Gold=('Price', 'sum')
    ).reset_index()
    
    return stats

def calculate_item_churn(df_old, df_new, analyzer):
    if df_old is None or df_new is None:
        return pd.DataFrame()
        
    df_old['Vale'] = df_old['Zone'].apply(clean_zone)
    df_new['Vale'] = df_new['Zone'].apply(clean_zone)
    
    old_ids = set(df_old['ListingID'].dropna().unique())
    new_ids = set(df_new['ListingID'].dropna().unique())
    sold_ids = old_ids - new_ids
    
    if not sold_ids:
        return pd.DataFrame()
        
    sold_df = df_old[df_old['ListingID'].isin(sold_ids)].copy()
    sold_df = analyzer._attach_tiers(sold_df)
    
    item_stats = sold_df.groupby(['Vale', 'Item', 'Tier']).agg(
        Gold_Volume=('Price', 'sum')
    ).reset_index()
    
    return item_stats

def main():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    history_dir = os.path.join(data_dir, "history")
    
    print("Loading Tiers...")
    m = MarketAnalyzer(data_dir)
    
    print("Finding Snapshots...")
    parsed = get_snapshot_files(history_dir)
    t0_file, t5_file, t20_file = find_target_snapshots(parsed)
    
    print(f"T0: {os.path.basename(t0_file) if t0_file else 'None'}")
    print(f"T-5: {os.path.basename(t5_file) if t5_file else 'None'}")
    print(f"T-20: {os.path.basename(t20_file) if t20_file else 'None'}")
    
    df0 = pd.read_parquet(t0_file)
    df0['Vale'] = df0['Zone'].apply(clean_zone)
    df0 = m._attach_tiers(df0)
    if 'Amount' not in df0.columns: df0['Amount'] = 1
    
    df5 = pd.read_parquet(t5_file) if t5_file else None
    df20 = pd.read_parquet(t20_file) if t20_file else None
    
    # Rank 1: Total Listing Volume & Tier Breakdown
    print("Calculating Rank 1...")
    r1 = df0.groupby(['Vale', 'Tier']).agg(
        Active_Listings=('Amount', 'sum')
    ).reset_index()
    
    r1_pivot = r1.pivot(index='Vale', columns='Tier', values='Active_Listings').fillna(0)
    r1_pivot['Total'] = r1_pivot.sum(axis=1)
    
    # Calculate percentages relative to the valley
    for t in [0, 1, 2, 3, 4]:
        if t in r1_pivot.columns:
            r1_pivot[f'T{t}_%'] = (r1_pivot[t] / r1_pivot['Total']) * 100
        else:
            r1_pivot[f'T{t}_%'] = 0.0
            
    # Need historical totals for 5d and 20d variance
    def get_total_listings(df):
        if df is None: return {}
        df['Vale'] = df['Zone'].apply(clean_zone)
        if 'Amount' not in df.columns: df['Amount'] = 1
        return df.groupby('Vale')['Amount'].sum().to_dict()
        
    t5_totals = get_total_listings(df5)
    t20_totals = get_total_listings(df20)
    
    var_5d_list = []
    var_20d_list = []
    for vale in r1_pivot.index:
        curr = r1_pivot.loc[vale, 'Total']
        v5 = t5_totals.get(vale, 0)
        v20 = t20_totals.get(vale, 0)
        
        pct5 = ((curr - v5) / v5 * 100) if v5 > 0 else 0
        pct20 = ((curr - v20) / v20 * 100) if v20 > 0 else 0
        
        var_5d_list.append(pct5)
        var_20d_list.append(pct20)
        
    r1_pivot['Var_5d_%'] = var_5d_list
    r1_pivot['Var_20d_%'] = var_20d_list
    r1_final = r1_pivot[['Total', 'T0_%', 'T1_%', 'T2_%', 'T3_%', 'T4_%', 'Var_5d_%', 'Var_20d_%']].sort_values('Total', ascending=False)
    
    
    # Rank 2 & 3: Churn (Qty and Gold)
    print("Calculating Ranks 2 & 3...")
    churn_recent = get_churn_stats(df5, df0)
    churn_past5 = get_churn_stats(df20, df5) if df20 is not None else pd.DataFrame()
    # For a 20d window we need T-40, but since we don't have it easily mapped, 
    # we will show 5d pacing vs previous 5d pacing (delta)
    
    if not churn_recent.empty:
        churn_recent = churn_recent.set_index('Vale')
        global_gold = churn_recent['Churn_Gold'].sum()
        churn_recent['Gold_%_Global'] = (churn_recent['Churn_Gold'] / global_gold) * 100
        
        if not churn_past5.empty:
            churn_past5 = churn_past5.set_index('Vale')
            # Delta 5d pacing
            joined = churn_recent.join(churn_past5, lsuffix='_now', rsuffix='_past')
            joined['Qty_Pacing_%'] = ((joined['Churn_Qty_now'] - joined['Churn_Qty_past']) / joined['Churn_Qty_past'] * 100).fillna(0)
            joined['Gold_Pacing_%'] = ((joined['Churn_Gold_now'] - joined['Churn_Gold_past']) / joined['Churn_Gold_past'] * 100).fillna(0)
            
            churn_recent['Qty_Pacing_%'] = joined['Qty_Pacing_%']
            churn_recent['Gold_Pacing_%'] = joined['Gold_Pacing_%']
        else:
            churn_recent['Qty_Pacing_%'] = 0.0
            churn_recent['Gold_Pacing_%'] = 0.0
            
        r2_final = churn_recent[['Churn_Qty', 'Qty_Pacing_%']].sort_values('Churn_Qty', ascending=False)
        r3_final = churn_recent[['Churn_Gold', 'Gold_%_Global', 'Gold_Pacing_%']].sort_values('Churn_Gold', ascending=False)
    else:
        r2_final = pd.DataFrame()
        r3_final = pd.DataFrame()
        
    # Rank 4: Top Items
    print("Calculating Rank 4...")
    item_churn = calculate_item_churn(df5, df0, m)
    top_items = {}
    if not item_churn.empty:
        for vale, grp in item_churn.groupby('Vale'):
            sorted_grp = grp.sort_values('Gold_Volume', ascending=False).head(3)
            tops = []
            for _, row in sorted_grp.iterrows():
                tops.append(f"{row['Item']} (T{row['Tier']})")
            
            while len(tops) < 3: tops.append("-")
            top_items[vale] = tops
            
    r4_final = pd.DataFrame.from_dict(top_items, orient='index', columns=['Top 1', 'Top 2', 'Top 3'])
    
    
    # Rank 5: Seller Concentration
    print("Calculating Rank 5...")
    scol = 'SellerHash' if 'SellerHash' in df0.columns else 'Seller'
    
    if scol in df0.columns:
        # Group by Vale and Seller
        seller_stats = df0.groupby(['Vale', scol]).agg(
            Seller_Volume=('Amount', 'sum'),
            Unique_Items=('Item', 'nunique')
        ).reset_index()
        
        r5_data = []
        for vale, grp in seller_stats.groupby('Vale'):
            total_vale_vol = grp['Seller_Volume'].sum()
            unique_sellers = len(grp)
            
            if unique_sellers == 0 or total_vale_vol == 0:
                continue
                
            sorted_grp = grp.sort_values('Seller_Volume', ascending=False)
            biggest_share = (sorted_grp.iloc[0]['Seller_Volume'] / total_vale_vol) * 100
            avg_items_all = grp['Unique_Items'].mean()
            avg_items_top5 = sorted_grp.head(5)['Unique_Items'].mean()
            
            r5_data.append({
                'Vale': vale,
                'Unique_Sellers': unique_sellers,
                'Biggest_Marketshare_%': biggest_share,
                'Avg_Items_Per_Seller': avg_items_all,
                'Avg_Items_Top5_Sellers': avg_items_top5
            })
            
        r5_final = pd.DataFrame(r5_data).set_index('Vale').sort_values('Unique_Sellers', ascending=False)
    else:
        r5_final = pd.DataFrame()


    # Export to Markdown
    print("Exporting Report...")
    out_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mapeamento_regioes.md")
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("# Mapeamento de Regiões de Pax Dei\n\n")
        f.write("*Rankings baseados nos snapshots históricos mais recentes (Análise Relativa e Interna de Vales)*\n\n")
        
        f.write("## RANK 1: Vales com Maior Volume de Listagens (Ativas)\n")
        f.write(r1_final.to_markdown(floatfmt=".1f"))
        f.write("\n\n")
        
        if not r2_final.empty:
            f.write("## RANK 2: Vales com Maior Liquidez (Churn Qtd - Últimos 5 dias)\n")
            f.write(r2_final.to_markdown(floatfmt=".1f"))
            f.write("\n\n")
            
        if not r3_final.empty:
            f.write("## RANK 3: Vales com Maior Volume Financeiro (Churn Gold - Últimos 5 dias)\n")
            f.write(r3_final.to_markdown(floatfmt=".1f"))
            f.write("\n\n")
            
        if not r4_final.empty:
            f.write("## RANK 4: Dinâmica de Itens (Top 3 Mais Lucrativos por Vale - Últimos 5 dias)\n")
            f.write(r4_final.to_markdown())
            f.write("\n\n")
            
        if not r5_final.empty:
            f.write("## RANK 5: Concentração de Lojas e Players (Oligopólios e Concorrência)\n")
            f.write(r5_final.to_markdown(floatfmt=".1f"))
            f.write("\n\n")

    print(f"Report Generated: {out_file}")

if __name__ == "__main__":
    main()
    
