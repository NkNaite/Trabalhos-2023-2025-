import pandas as pd
import os
from datetime import timedelta

# Config
ITEM_NAME = "Steel Broadsword"
DATA_DIR = r"d:\PaxDei_Tool\data"
LATEST_FILE = os.path.join(DATA_DIR, "selene_latest.parquet")
HISTORY_FILE = os.path.join(DATA_DIR, "full_history.parquet")

def analyze():
    print(f"Iniciando análise para: {ITEM_NAME}")
    
    # 1. Carregar Dados Atuais
    try:
        df_latest = pd.read_parquet(LATEST_FILE)
        current_stock_zones = df_latest[df_latest['Item'] == ITEM_NAME]['Zone'].unique()
        print(f"Zonas com estoque atual ({len(current_stock_zones)}): {', '.join(current_stock_zones)}")
    except Exception as e:
        print(f"Erro ao ler latest: {e}")
        return

    # 2. Carregar Histórico
    try:
        df_hist = pd.read_parquet(HISTORY_FILE)
        df_hist = df_hist[df_hist['Item'] == ITEM_NAME]
        
        # Converter Timestamp para datetime se necessário
        if not pd.api.types.is_datetime64_any_dtype(df_hist['Timestamp']):
             df_hist['Timestamp'] = pd.to_datetime(df_hist['Timestamp'])

    except Exception as e:
        print(f"Erro ao ler histórico: {e}")
        return

    all_zones = df_hist['Zone'].unique()
    target_zones = [z for z in all_zones if z not in current_stock_zones]
    
    print(f"Zonas alvo (sem estoque atual mas com histórico): {len(target_zones)}")
    
    results = []

    for zone in target_zones:
        zone_df = df_hist[df_hist['Zone'] == zone]
        
        # Agrupar por ListingID para analisar cada anúncio individualmente
        listings = zone_df.groupby('ListingID')
        
        fast_sales_count = 0
        total_sales_count = 0
        
        for listing_id, listing_data in listings:
            first_seen = listing_data['Timestamp'].min()
            last_seen = listing_data['Timestamp'].max()
            duration = last_seen - first_seen
            
            # Critério do usuário: "vendida em menos de 2 dias"
            if duration < timedelta(days=2):
                fast_sales_count += 1
            
            total_sales_count += 1
            
        if fast_sales_count > 0:
            results.append({
                'Zone': zone,
                'FastSales': fast_sales_count,
                'TotalHistory': total_sales_count,
                'Ratio': fast_sales_count / total_sales_count if total_sales_count > 0 else 0
            })

    # Ordenar por número de vendas rápidas (giro)
    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df = results_df.sort_values(by='FastSales', ascending=False)
        
        print("\n--- Relatório de Oportunidades (Giro Rápido em Zonas sem Estoque) ---")
        print(results_df[['Zone', 'FastSales', 'TotalHistory']].to_string(index=False))
        
        # Salvar relatório se desejar, ou apenas imprimir
    else:
        print("\nNenhuma zona encontrada que atenda aos critérios (sem estoque atual + histórico de vendas rápidas).")

if __name__ == "__main__":
    analyze()
