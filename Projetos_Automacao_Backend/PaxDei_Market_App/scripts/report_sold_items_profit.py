import os
import glob
import pandas as pd
import json

def analyze_sales_and_profit():
    data_dir = "d:/PaxDei_Tool/data"
    history_dir = os.path.join(data_dir, "history")
    out_file = "d:/PaxDei_Tool/sold_items_report.txt"
    
    # Load Seller ID
    profile_path = os.path.join(data_dir, "user_profile.json")
    if not os.path.exists(profile_path):
        print("User profile not found. Cannot determine Seller ID.")
        return
        
    with open(profile_path, 'r') as f:
        seller_id = json.load(f).get('my_seller_id')
        
    if not seller_id:
        print("Seller ID not found in profile.")
        return
        
    print(f"Analyzing all sales and revenue for Seller ID: {seller_id}")
    
    # Get all history files sorted
    files = sorted(glob.glob(os.path.join(history_dir, '**', '*.parquet'), recursive=True))
    latest_file = os.path.join(data_dir, 'selene_latest.parquet')
    if os.path.exists(latest_file) and latest_file not in files:
        files.append(latest_file)
        
    if not files:
        print("No history files available for analysis.")
        return

    print(f"Scanning {len(files)} snapshots...")
    
    # Tracker: { listing_id: { 'item': str, 'zone': str, 'unit_price': float, 'last_qty': int, 'last_file': str } }
    tracker = {}
    sales_record = [] 

    for fpath in files:
        fname = os.path.basename(fpath)
        date_str = fname.replace("market_", "").replace(".parquet", "").replace("_", " ") if "market_" in fname else fname
        
        try:
            df = pd.read_parquet(fpath)
            scol = 'SellerHash' if 'SellerHash' in df.columns else 'Seller'
            
            if scol not in df.columns:
                continue
                
            my_rows = df[df[scol] == seller_id]
            current_listings = set()
            
            for _, row in my_rows.iterrows():
                lid = row.get('ListingID')
                if not lid: continue
                
                qty = row['Amount']
                price = row['Price']
                item = row['Item']
                zone = row.get('Zone', 'Unknown')
                unit_price = price / qty if qty > 0 else 0
                
                current_listings.add(lid)
                
                if lid not in tracker:
                    tracker[lid] = {
                        'item': item,
                        'zone': zone,
                        'unit_price': unit_price,
                        'last_qty': qty,
                        'last_date': date_str
                    }
                else:
                    prev_qty = tracker[lid]['last_qty']
                    if qty < prev_qty:
                        drop = prev_qty - qty
                        revenue = drop * tracker[lid]['unit_price']
                        sales_record.append({
                            'date': date_str,
                            'item': item,
                            'sold_qty': drop,
                            'unit_price': tracker[lid]['unit_price'],
                            'revenue': revenue,
                            'zone': zone,
                            'type': 'Venda Confirmada (Parcial)'
                        })
                    
                    tracker[lid]['last_qty'] = qty
                    tracker[lid]['last_date'] = date_str
                    tracker[lid]['unit_price'] = unit_price
            
            missing_lids = [lid for lid in tracker.keys() if lid not in current_listings and tracker[lid]['last_qty'] > 0]
            for lid in missing_lids:
                drop = tracker[lid]['last_qty']
                revenue = drop * tracker[lid]['unit_price']
                sales_record.append({
                    'date': date_str, 
                    'item': tracker[lid]['item'],
                    'sold_qty': drop,
                    'unit_price': tracker[lid]['unit_price'],
                    'revenue': revenue,
                    'zone': tracker[lid]['zone'],
                    'type': 'Sumiu (Esgotado/Cancelado/Expirado)'
                })
                tracker[lid]['last_qty'] = 0 
                
        except Exception as e:
            continue

    with open(out_file, 'w', encoding='utf-8') as f:
        if not sales_record:
            f.write("\nNenhuma alteracao detectada no historico analisado.\n")
            return

        sales_df = pd.DataFrame(sales_record)
        sales_df['Day'] = sales_df['date'].str[:10]
        sales_df.sort_values(by=['date', 'type'], inplace=True)
        
        f.write("\n" + "="*90 + "\n")
        f.write(" RELATORIO DE VENDAS E ALTERACOES DE ESTOQUE \n")
        f.write("="*90 + "\n")
        f.write("Aviso: 'Venda Confirmada' = alguem comprou uma fracao do estoque.\n")
        f.write("'Sumiu' = O anuncio sumiu do mercado (pode ter vendido tudo, expirado ou sido cancelado).\n\n")
        
        total_revenue_confirmed = 0
        total_revenue_missing = 0
        
        for day, group in sales_df.groupby('Day'):
            confirmed_group = group[group['type'] == 'Venda Confirmada (Parcial)']
            missing_group = group[group['type'] == 'Sumiu (Esgotado/Cancelado/Expirado)']
            
            day_revenue_c = confirmed_group['revenue'].sum()
            day_revenue_m = missing_group['revenue'].sum()
            
            total_revenue_confirmed += day_revenue_c
            total_revenue_missing += day_revenue_m
            
            f.write(f"\n[DATA]: {day}\n")
            f.write("-" * 90 + "\n")
            
            if not confirmed_group.empty:
                f.write("  >> VENDAS CONFIRMADAS (Estoque reduziu, mas anuncio continuou):\n")
                day_summary_c = confirmed_group.groupby(['item', 'unit_price', 'zone']).agg({'sold_qty': 'sum', 'revenue': 'sum'}).reset_index()
                for _, row in day_summary_c.iterrows():
                    f.write(f"      * {row['item']:<25} | Qtd: {row['sold_qty']:<4} | Preco Un.: {row['unit_price']:>6.2f}g | Lucro: +{row['revenue']:>7.2f}g | Local: {row['zone']}\n")
            
            if not missing_group.empty:
                f.write("  >> ANUNCIOS DESAPARECIDOS (Podem ser Vendas Totais, Cancelamentos ou Expiracoes):\n")
                day_summary_m = missing_group.groupby(['item', 'unit_price', 'zone']).agg({'sold_qty': 'sum', 'revenue': 'sum'}).reset_index()
                for _, row in day_summary_m.iterrows():
                    f.write(f"      * {row['item']:<25} | Qtd: {row['sold_qty']:<4} | Preco Un.: {row['unit_price']:>6.2f}g | Valor: ~{row['revenue']:>7.2f}g | Local: {row['zone']}\n")

        f.write("\n" + "="*90 + "\n")
        f.write(" RESUMO GERAL \n")
        f.write("="*90 + "\n")
        f.write(f"Receita Total (Apenas Vendas Confirmadas/Parciais): {total_revenue_confirmed:.2f}g\n")
        f.write(f"Valor Total de Anuncios que Sumiram (Cancelados/Esgotados): {total_revenue_missing:.2f}g\n")
        f.write("==========================================================================================\n")
        print(f"Relatório salvo em: {out_file}")

if __name__ == "__main__":
    analyze_sales_and_profit()
