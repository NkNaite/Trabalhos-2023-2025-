import pandas as pd
import os
from datetime import timedelta

ITEM_NAME = "Steel Broadsword"
DATA_DIR = r"d:\PaxDei_Tool\data"
LATEST_FILE = os.path.join(DATA_DIR, "selene_latest.parquet")
HISTORY_FILE = os.path.join(DATA_DIR, "full_history.parquet")

def analyze():
    print(f"Analisando oportunidades para: {ITEM_NAME}")
    
    # Carregar dados
    try:
        df_latest = pd.read_parquet(LATEST_FILE)
        df_latest = df_latest[df_latest['Item'] == ITEM_NAME]
        
        df_hist = pd.read_parquet(HISTORY_FILE)
        df_hist = df_hist[df_hist['Item'] == ITEM_NAME]
        
        if not pd.api.types.is_datetime64_any_dtype(df_hist['Timestamp']):
             df_hist['Timestamp'] = pd.to_datetime(df_hist['Timestamp'])
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return

    # Métricas de Estoque Atual
    stock_metrics = df_latest.groupby('Zone').agg(
        CurrentStock=('Item', 'count'),
        MinPrice=('Price', 'min')
    ).reset_index()

    # Métricas de Histórico (Giro)
    # Agrupar por ListingID dentro de cada Zona
    # Assumindo que ListingID é único per listing. SeListingID repetir entre zonas (erros), agrupar por ListingID pode falhar, mas ok.
    # Melhor agrupar por (Zone, ListingID).
    
    # Calcular duração de cada listing
    listing_stats = df_hist.groupby(['Zone', 'ListingID']).agg(
        FirstSeen=('Timestamp', 'min'),
        LastSeen=('Timestamp', 'max'),
        Price=('Price', 'first') # Preço inicial
    ).reset_index()
    
    listing_stats['Duration'] = listing_stats['LastSeen'] - listing_stats['FirstSeen']
    listing_stats['IsFastSale'] = listing_stats['Duration'] < timedelta(days=2)
    
    # Agrupar por Zona para ter métricas agregadas
    zone_history = listing_stats.groupby('Zone').agg(
        TotalHistory=('ListingID', 'count'),
        FastSales=('IsFastSale', 'sum'),
        AvgFastSalePrice=('Price', lambda x: x[listing_stats.loc[x.index, 'IsFastSale']].mean() if any(listing_stats.loc[x.index, 'IsFastSale']) else 0)
    ).reset_index()
    
    zone_history['FastSaleRatio'] = zone_history['FastSales'] / zone_history['TotalHistory']
    
    # Merge
    merged = pd.merge(zone_history, stock_metrics, on='Zone', how='left')
    merged['CurrentStock'] = merged['CurrentStock'].fillna(0)
    merged['MinPrice'] = merged['MinPrice'].fillna(0)
    
    # Filtrar e Ordenar
    # Prioridade 1: Stock == 0 (Se houver)
    # Prioridade 2: Stock baixo (<= 5)
    
    zero_stock = merged[merged['CurrentStock'] == 0].sort_values(by='FastSaleRatio', ascending=False)
    low_stock = merged[(merged['CurrentStock'] > 0) & (merged['CurrentStock'] <= 35)].sort_values(by='FastSaleRatio', ascending=False) # 35 é um numero alto, mas vou mostrar top 10 independente
    
    print("\n--- Zonas SEM Estoque Atual (Com Histórico) ---")
    if not zero_stock.empty:
        print(zero_stock[['Zone', 'FastSaleRatio', 'FastSales', 'TotalHistory', 'AvgFastSalePrice']].to_string(index=False))
    else:
        print("Nenhuma zona encontrada.")

    print("\n--- Zonas com Baixo Estoque e Alto Giro (Top 10) ---")
    if not low_stock.empty:
        # Filtrar apenas quem tem vendas rápidas no histórico
        valid_low_stock = low_stock[low_stock['FastSales'] > 0]
        print(valid_low_stock[['Zone', 'CurrentStock', 'MinPrice', 'FastSaleRatio', 'FastSales', 'AvgFastSalePrice']].head(10).to_string(index=False))

if __name__ == "__main__":
    analyze()
