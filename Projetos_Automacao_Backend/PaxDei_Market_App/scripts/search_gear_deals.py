import pandas as pd
import os
import json

DATA_DIR = r"d:\PaxDei_Tool\data"
LATEST_FILE = os.path.join(DATA_DIR, "selene_latest.parquet")
HISTORY_FILE = os.path.join(DATA_DIR, "full_history.parquet")
PAX_TOOLS_JSON = os.path.join(DATA_DIR, "pax_tools_data.json")

def is_target_equipment(item_name, item_uid, tier):
    # Tier min 3 and 4 (last two tiers)
    if tier not in [3, 4]:
        return False
        
    # Ignore broadsword
    if "broadsword" in item_name.lower():
        return False
        
    # Ignore common and poor rarity correctly without matching uncommon
    parts = item_uid.lower().split('_')
    if "common" in parts or "poor" in parts:
        return False
        
    # Must be weapon, shield or armor
    if item_uid.startswith('wearable_') or item_uid.startswith('wieldable_') or item_uid.endswith('_bow') or 'shield' in item_uid:
        return True
        
    return False

def get_target_items():
    try:
        with open(PAX_TOOLS_JSON, 'r', encoding='utf-8') as f:
            pax_data = json.load(f)
            
        target_items = []
        for item in pax_data.get('items', []):
            name = item.get('name')
            uid = item.get('uid', '')
            tier = item.get('tier', 0)
            
            if name and is_target_equipment(name, uid, tier):
                target_items.append(name)
                
        return set(target_items)
    except Exception as e:
        print(f"Error loading items JSON: {e}")
        return set()

def analyze_opportunities():
    target_items = get_target_items()
    if not target_items:
        print("No target items found.")
        return

    print(f"Buscando oportunidades para {len(target_items)} itens diferentes de T3 e T4...")

    try:
        # Load history
        df_hist = pd.read_parquet(HISTORY_FILE)
        
        # Calculate Medians for target items
        df_hist_target = df_hist[df_hist['Item'].isin(target_items)]
        
        if df_hist_target.empty:
            print("Nenhum histórico encontrado para os itens alvo.")
            return
            
        # Agrupar e calcular a mediana por item
        medians = df_hist_target.groupby('Item')['Price'].median().reset_index()
        medians.rename(columns={'Price': 'MedianPrice'}, inplace=True)
        
        # Load latest data
        df_latest = pd.read_parquet(LATEST_FILE)
        df_latest_target = df_latest[df_latest['Item'].isin(target_items)]
        
        if df_latest_target.empty:
            print("Nenhum item alvo no mercado atual.")
            return

        # Mesclar as medianas nos itens do mercado atual
        merged = pd.merge(df_latest_target, medians, on='Item', how='inner')
        
        # Encontrar descontos (Preço da listagem atual < Mediana)
        # Além disso, vamos calcular o % de desconto
        
        deals = merged[merged['Price'] < merged['MedianPrice']].copy()
        
        if deals.empty:
            print("Nenhuma oportunidade com preço abaixo da mediana foi encontrada.")
            return
            
        deals['DiscountRatio'] = 1 - (deals['Price'] / deals['MedianPrice'])
        # Sort by best discounts
        deals = deals.sort_values(by=['Item', 'DiscountRatio'], ascending=[True, False])
        
        # Gerar Output Markdown
        output_lines = []
        output_lines.append("## Oportunidades - Abaixo da Mediana (Armas e Armaduras T3/T4)")
        output_lines.append("> Excluídos: Comuns, Poor, Broadswords, e Tiers < 3\n")
        
        grouped_deals = deals.groupby('Item')
        
        for item_name, group in grouped_deals:
            median_val = group['MedianPrice'].iloc[0]
            output_lines.append(f"### {item_name}")
            output_lines.append(f"* **Mediana Histórica:** {median_val:,.0f} Gold")
            
            for _, row in group.iterrows():
                zone = row['Zone']
                price = row['Price']
                discount_perc = row['DiscountRatio'] * 100
                amount = row['Amount']
                qty_str = f" x{amount}" if amount > 1 else ""
                output_lines.append(f"  * {zone}: **{price:,.0f} G** (Desconto: {discount_perc:.0f}%){qty_str}")
            
            output_lines.append("")

        output_md = "\n".join(output_lines)
        
        with open('melhores_ofertas_armaduras_armas_t3_t4.md', 'w', encoding='utf-8') as f:
            f.write(output_md)
            
        print("Arquivo 'melhores_ofertas_armaduras_armas_t3_t4.md' gerado com sucesso.")
        print("Uma prévia das oportunidades encontradas:")
        print(output_md[:500])
        print("...")

    except Exception as e:
        print(f"Erro ao processar oportunidades: {e}")

if __name__ == "__main__":
    analyze_opportunities()
