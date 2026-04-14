import pandas as pd
import os

DATA_DIR = r"d:\PaxDei_Tool\data"
LATEST_FILE = os.path.join(DATA_DIR, "selene_latest.parquet")
HISTORY_FILE = os.path.join(DATA_DIR, "full_history.parquet")

def analyze():
    print("Buscando oportunidades de Snapdragon, Ambergrasp e Cannonite (>= 100 un)...")

    # Load latest data
    try:
        df_latest = pd.read_parquet(LATEST_FILE)
    except Exception as e:
        print(f"Erro ao carregar dados atuais: {e}")
        return

    # Filter items
    targets = ['snapdragon', 'ambergrasp', 'cannonite']
    mask = df_latest['Item'].str.lower().apply(lambda x: any(t in str(x).lower() for t in targets))
    df_targets = df_latest[mask].copy()

    if df_targets.empty:
        print("Nenhum desses itens encontrado no mercado atual.")
        return

    # Filter Amount >= 100
    df_targets = df_targets[df_targets['Amount'] >= 100]

    if df_targets.empty:
        print("Nenhuma oferta com 100+ unidades encontrada para esses itens.")
        return

    # Load history for medians
    try:
        df_hist = pd.read_parquet(HISTORY_FILE)
        item_names = df_targets['Item'].unique()
        df_hist_targets = df_hist[df_hist['Item'].isin(item_names)]
        
        # Calculate Medians on UnitPrice to evaluate stacks!
        # Because different stack sizes make absolute Price hard to compare
        if not df_hist_targets.empty:
            medians = df_hist_targets.groupby('Item')['UnitPrice'].median().reset_index()
            medians.rename(columns={'UnitPrice': 'MedianUnitPrice'}, inplace=True)
        else:
            medians = pd.DataFrame(columns=['Item', 'MedianUnitPrice'])
    except Exception as e:
        print(f"Erro ao carregar histórico: {e}")
        medians = pd.DataFrame(columns=['Item', 'MedianUnitPrice'])

    # Merge
    if not medians.empty:
        merged = pd.merge(df_targets, medians, on='Item', how='left')
    else:
        merged = df_targets
        merged['MedianUnitPrice'] = 0

    # Sort -> Item, UnitPrice ASC
    merged = merged.sort_values(by=['Item', 'UnitPrice'])

    # Print results
    output = []
    output.append("## Oportunidades - Snapdragon, Ambergrasp e Cannonite (>= 100 un)")
    
    for item_name, group in merged.groupby('Item'):
        median_val = group['MedianUnitPrice'].iloc[0] if 'MedianUnitPrice' in group.columns and pd.notnull(group['MedianUnitPrice'].iloc[0]) else 0
        output.append(f"\n### {item_name} (Mediana Unitária: {median_val:,.2f} G/un)")
        
        # We will separate deals below median vs above median
        for _, row in group.iterrows():
            zone = row['Zone']
            price = row['Price']
            amount = row['Amount']
            unit_price = row['UnitPrice']
            
            discount_str = ""
            if median_val > 0 and unit_price < median_val:
                discount = (1 - (unit_price / median_val)) * 100
                discount_str = f" **[Desconto: {discount:.0f}% vs Mediana]**"
            elif median_val > 0 and unit_price > median_val:
                premium = ((unit_price / median_val) - 1) * 100
                discount_str = f" [Acima da mediana: +{premium:.0f}%]"
                
            output.append(f"  * {zone}: {amount} und por {price:,.0f} G ({unit_price:,.2f} G/un){discount_str}")

    with open(r'd:\PaxDei_Tool\ofertas_materiais.md', 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
        
    print("Salvo em ofertas_materiais.md")

if __name__ == "__main__":
    analyze()
