import os
import glob
import pandas as pd

def analyze_sales():
    data_dir = "d:/PaxDei_Tool/data"
    history_dir = os.path.join(data_dir, "history")
    
    files = sorted(glob.glob(os.path.join(history_dir, '**', '*.parquet'), recursive=True))
    latest_file = os.path.join(data_dir, 'selene_latest.parquet')
    if os.path.exists(latest_file) and latest_file not in files:
        files.append(latest_file)
        
    if not files:
        print("No history files.")
        return
        
    tracker = {}
    sales_data = []

    target_item = "Nubuck Leather"

    for fpath in files:
        try:
            df = pd.read_parquet(fpath)
            
            # Filter for target item
            if 'Item' not in df.columns:
                continue
            item_df = df[df['Item'] == target_item].copy()
            if item_df.empty:
                continue
                
            current_listings = set()
            
            for _, row in item_df.iterrows():
                lid = row.get('ListingID')
                if not lid: continue
                
                qty = row['Amount']
                price = row['Price']
                zone = row.get('Zone', 'Unknown')
                unit_price = price / qty if qty > 0 else 0
                
                current_listings.add(lid)
                
                if lid not in tracker:
                    tracker[lid] = {
                        'zone': zone,
                        'unit_price': unit_price,
                        'last_qty': qty
                    }
                else:
                    prev_qty = tracker[lid]['last_qty']
                    if qty < prev_qty:
                        drop = prev_qty - qty
                        sales_data.append({
                            'zone': zone,
                            'qty_sold': drop,
                            'unit_price': tracker[lid]['unit_price'],
                            'revenue': drop * tracker[lid]['unit_price']
                        })
                    tracker[lid]['last_qty'] = qty
                    
            # Check for vanished listings
            missing = [lid for lid in tracker.keys() if lid not in current_listings and tracker[lid]['last_qty'] > 0]
            for lid in missing:
                drop = tracker[lid]['last_qty']
                sales_data.append({
                    'zone': tracker[lid]['zone'],
                    'qty_sold': drop,
                    'unit_price': tracker[lid]['unit_price'],
                    'revenue': drop * tracker[lid]['unit_price']
                })
                tracker[lid]['last_qty'] = 0
                
        except Exception as e:
            continue
            
    with open("d:/PaxDei_Tool/nubuck_sales_analysis.txt", "w", encoding='utf-8') as f:
        if not sales_data:
            f.write(f"No sales data found for {target_item}.\n")
            print("No sales data found.")
            return
            
        sales_df = pd.DataFrame(sales_data)
        
        # Calculate current median price
        current_prices = {}
        try:
            latest_df = pd.read_parquet(latest_file)
            current_item_df = latest_df[latest_df['Item'] == target_item].copy()
            if not current_item_df.empty:
                current_item_df['UnitPrice'] = current_item_df['Price'] / current_item_df['Amount']
                current_prices = current_item_df.groupby('Zone')['UnitPrice'].median().to_dict()
        except:
            pass
        
        # Aggregate sales data by zone
        zone_stats = sales_df.groupby('zone').agg(
            total_qty_sold=('qty_sold', 'sum'),
            total_revenue=('revenue', 'sum')
        ).reset_index()
        
        zone_stats['avg_sold_price'] = zone_stats['total_revenue'] / zone_stats['total_qty_sold']
        zone_stats['current_median_price'] = zone_stats['zone'].map(current_prices)
        
        # We want to identify the "best" place. High volume + High price
        zone_stats = zone_stats.sort_values(by=['total_qty_sold', 'avg_sold_price'], ascending=[False, False])
        
        f.write(f"=== ANALISE DE VENDA DE: {target_item} ===\n")
        f.write("Ranking de vales combinando Liquidez (Volume Sumido/Vendido) e Preco Historico.\n\n")
        f.write("DICA DE LEITURA:\n")
        f.write("- Alto Volume + Preco Medio Alto: Zona de Ouro (A galera gasta grana aqui).\n")
        f.write("- Alto Volume + Preco Medio Baixo: Zona de Queima (Vende rapido, mas tem q ser preco de banana).\n")
        f.write("- Sem Estoque Atual: Se vendeu historico mas ta sem estoque agora, o preco dita vc.\n")
        f.write("--------------------------------------------------------------------------------------\n\n")
        
        rank = 1
        for _, row in zone_stats.iterrows():
            zone = row['zone']
            qty = int(row['total_qty_sold'])
            avg_price = row['avg_sold_price']
            cur_price = row['current_median_price']
            
            cur_price_str = f"{cur_price:.2f}g" if pd.notnull(cur_price) else "SEM ESTOQUE (Monolpolio Possivel)"
            
            f.write(f"#{rank} - 📍 {zone.upper()}\n")
            f.write(f"   * Liquidez Historica (Vendidos/Sumidos): {qty} unidades\n")
            f.write(f"   * Preco Medio de Saida (Historico)     : {avg_price:.2f}g\n")
            f.write(f"   * Preco Mediano ATUAL na Loja          : {cur_price_str}\n")
            f.write("\n")
            rank += 1

    print("Analysis saved to nubuck_sales_analysis.txt")

if __name__ == "__main__":
    analyze_sales()
