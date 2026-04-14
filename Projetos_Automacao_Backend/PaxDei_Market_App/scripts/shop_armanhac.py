import os
import pandas as pd
from datetime import datetime
import numpy as np

DATA_DIR = r"d:\PaxDei_Tool\data"
LATEST_FILE = os.path.join(DATA_DIR, "selene_latest.parquet")
HISTORY_FILE = os.path.join(DATA_DIR, "full_history.parquet")

def categorize_item(item_name):
    item = item_name.lower()
    
    is_weapon = any(w in item for w in ['sword', 'battleaxe', 'mace', 'spear', 'maul', 'greatmaul', 'bow', 'dagger', 'blade', 'crossbow', 'lance', 'staff'])
    is_armor = any(a in item for a in ['helm', 'cowl', 'hauberk', 'chainmail', 'breastplate', 'chausses', 'greaves', 'gauntlets', 'gloves', 'shoes', 'boots', 'shield', 'targe', 'kite', 'cap', 'tunic', 'pants', 'bracers'])
    is_tool = any(t in item for t in ['pickaxe', 'woodchopping', 'sickle', 'knife', 'hammer', 'tool'])
    
    is_wrought = 'wrought iron' in item
    is_steel = 'steel' in item
    is_iron = 'iron' in item and not is_wrought
    is_copper = 'copper' in item
    is_bronze = 'bronze' in item
    is_iron_or_wrought = is_wrought or is_iron
    
    if is_steel or ('attuned' in item or 'warded' in item or 'blessed' in item or 'mystic' in item):
        rarity_val = 3 # Rare or equivalent tier
    elif is_wrought:
        rarity_val = 2 # Uncommon
    else:
        rarity_val = 1 # Common
        
    cat = "Other"
    priority = 99
    
    if is_weapon or is_armor:
        # Prioridade 1: armas e armaduras rare > uncommon
        if rarity_val >= 3:
            cat = "Armas_Armaduras_Ra"
            priority = 1
        elif is_wrought: # Prioridade 3: armas e armaduras de wrought ingot rare>uncommon
            cat = "Armas_Armaduras_Wrought"
            priority = 3
    elif is_tool:
        # Prioridade 2: ferramentas rare > uncommon
        if rarity_val >= 3:
            cat = "Ferramentas_Ra"
            priority = 2
        elif is_wrought:
            cat = "Ferramentas_Wrought"
            priority = 2.5
            
    return priority, cat

def main():
    print("Loading history file...")
    df_hist = pd.read_parquet(HISTORY_FILE)
    
    if not pd.api.types.is_datetime64_any_dtype(df_hist['Timestamp']):
        df_hist['Timestamp'] = pd.to_datetime(df_hist['Timestamp'])
        
    # Preço mediano anterior ao dia 21/02
    target_date = pd.to_datetime('2026-02-21').tz_localize(df_hist['Timestamp'].dt.tz) if df_hist['Timestamp'].dt.tz else pd.to_datetime('2026-02-21')
    
    # Check if there is tz info
    if df_hist['Timestamp'].dt.tz is not None and target_date.tzinfo is None:
        target_date = target_date.tz_localize(df_hist['Timestamp'].dt.tz)
    elif df_hist['Timestamp'].dt.tz is None and target_date.tzinfo is not None:
        target_date = target_date.tz_localize(None)

    df_med_hist = df_hist[df_hist['Timestamp'] < target_date].copy()
    
    if 'UnitPrice' not in df_med_hist.columns:
        df_med_hist['UnitPrice'] = df_med_hist['Price'] / df_med_hist['Amount']
        
    medians = df_med_hist.groupby('Item')['UnitPrice'].median().to_dict()
    print(f"Calculated medians for {len(medians)} items based on data before 21/02/2026")
    
    print("Loading latest file...")
    df_latest = pd.read_parquet(LATEST_FILE)
    if 'UnitPrice' not in df_latest.columns:
         df_latest['UnitPrice'] = df_latest['Price'] / df_latest['Amount']
    
    # Filter only Armanhac zone
    df_arm = df_latest[df_latest['Zone'].str.contains('Armanhac', case=False, na=False)].copy()
    
    deals = []
    for _, row in df_arm.iterrows():
        item_name = row['Item']
        price = row['UnitPrice']
        zone = row['Zone']
        amount = row['Amount']
        
        median = medians.get(item_name, 0)
        
        if median > 0 and price < median:
            priority, cat = categorize_item(item_name)
            if priority < 99:
                discount = (median - price) / median * 100
                deals.append({
                    'Item': item_name,
                    'Category': cat,
                    'Priority': priority,
                    'Zone': zone,
                    'Amount': amount,
                    'UnitPrice': round(price, 2),
                    'MedianPrice': round(median, 2),
                    'Discount_%': round(discount, 1)
                })
                
    if not deals:
        print("No deals found matching the criteria.")
        return
        
    df_deals = pd.DataFrame(deals)
    
    # Group identical deals
    df_grouped = df_deals.groupby(['Priority', 'Category', 'Item', 'Zone', 'UnitPrice', 'MedianPrice', 'Discount_%']).agg({'Amount': 'sum'}).reset_index()
    
    # Sort by priority, then discount
    df_grouped = df_grouped.sort_values(by=['Priority', 'Discount_%'], ascending=[True, False])
    
    # Convert to markdown output
    with open("d:/PaxDei_Tool/armanhac_shopping_list.md", "w", encoding='utf-8') as f:
        f.write("# Lista de Compras - Armanhac\n\n")
        f.write("Itens abaixo do preço mediano histórico (antes de 21/02/2026).\n")
        f.write("Prioridades:\n1. Armas e Armaduras Rare/Steel\n2. Ferramentas Rare/Steel\n3. Armas e armaduras de Wrought Iron\n\n")
        
        for priority in sorted(df_grouped['Priority'].unique()):
            group = df_grouped[df_grouped['Priority'] == priority]
            cat_name = group['Category'].iloc[0]
            f.write(f"## {cat_name} (Prioridade {priority})\n\n")
            
            for item in group['Item'].unique():
                f.write(f"### {item}\n")
                item_group = group[group['Item'] == item]
                med = item_group['MedianPrice'].iloc[0]
                f.write(f"* **Mediana (< 21/Fev):** {med:,.0f} Gold\n")
                
                for _, row in item_group.iterrows():
                    f.write(f"  * {row['Zone']}: **{row['UnitPrice']:,.0f} G** (Desconto: {row['Discount_%']}% | Qtd: {row['Amount']})\n")
                f.write("\n")
                
    print("Created d:/PaxDei_Tool/armanhac_shopping_list.md")

if __name__ == "__main__":
    main()
