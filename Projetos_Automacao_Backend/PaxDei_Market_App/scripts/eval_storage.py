import pandas as pd
import re
from collections import defaultdict
import os

raw_data = """
55 snapdragon
18 Yellow Runic Leash
4 Crimson Runic Leash
14 Red Runic Leash
703 Canonite
850 Ambergrasp
15 Cracked Sigil
13 Worn Out Sigil
6 Tattered Sigil
9 Tattered Locket
62 Worn Out Locket
29 Cracked Locket 
59 Aurum Ore
1 Amulet of Holy Wound
1 Great Orb of the Twilight
1 Majestic SIgil of Samalo
1 Great Amulet of Martyr's Crown
1 Sigi of Pellipis
1 Seal of the Martyrs
2 The Sigil of Amatia
1 Majestic Seal of Creed
1 Sigil of MAgalast
1 Pendant of the Tide
1 Blessed Ligarius
1 Great Saint Veridiana's Breath
15 Cracked Ethereal Crystal
14 Multifaceted Ethereal Crystal
4 Cubic Ethereal Crystal
272 Cotton Fiber 
529 Finen Linen Cloth
1365 Wrough Iron Ingot 
60 Silver Ingot
1600 Iron studs
800 Bronze studs 
2238 Iron Nails
2000 Bronze nails
2000 Iron Studs
196 Silver ore
17 Aurum Ore
1022 Iron Ingot
1140 Bronze Ingot
480 Antler
"""

def clean_item_name(name):
    name = name.strip()
    # Apply some manual corrections from typos
    if name.lower() == 'snapdragon': return 'Snapdragon'
    if name.lower() == 'finen linen cloth': return 'Fine Linen Cloth'
    if name.lower() == 'wrough iron ingot': return 'Wrought Iron Ingot'
    if name.lower() == 'iron studs': return 'Iron Studs'
    if name.lower() == 'bronze studs': return 'Bronze Studs'
    if name.lower() == 'iron nails': return 'Iron Nails'
    if name.lower() == 'bronze nails': return 'Bronze Nails'
    if name.lower() == 'silver ore': return 'Silver Ore'
    if name.lower() == 'aurum ore': return 'Aurum Ore'
    if name.lower() == 'majestic sigil of samalo': return 'Majestic Sigil of Samalo'
    if name.lower() == 'sigi of pellipis': return 'Sigil of Pellipis'
    if name.lower() == 'sigil of magalast': return 'Sigil of Magalast'
    if name.lower() == 'antler': return 'Antler'
    # Capitalize words properly
    return " ".join(word.capitalize() for word in name.split())

inventory = defaultdict(int)
for line in raw_data.split('\n'):
    line = line.strip()
    if not line or line.lower() == 'x': continue
    match = re.match(r'^(\d+)\s+(.+)$', line)
    if match:
        qty = int(match.group(1))
        name = clean_item_name(match.group(2))
        inventory[name] += qty
    else:
        print(f"Failed to parse line: {line}")

data_path = "data/selene_latest.parquet"
df = pd.read_parquet(data_path)

# Ensure Item is string for reliable matching
df['Item'] = df['Item'].astype(str)

# Ensure UnitPrice is numeric (float) so we can do math
df['UnitPrice'] = pd.to_numeric(df['UnitPrice'], errors='coerce')

results = []
total_stash_value = 0

for item, qty in inventory.items():
    item_df = df[df['Item'].str.lower() == item.lower()]
    if not item_df.empty:
        # Use simple global median price from the dataset
        median_price = item_df['UnitPrice'].median()
        total_price = median_price * qty
        total_stash_value += total_price
        results.append({
            'Item': item,
            'Quantity': qty,
            'Median Price': median_price,
            'Total Value': total_price,
            'Found': True
        })
    else:
        results.append({
            'Item': item,
            'Quantity': qty,
            'Median Price': 0,
            'Total Value': 0,
            'Found': False
        })
        print(f"Warning: Item not found in market data: {item}")

# Sort results by total value descending
results.sort(key=lambda x: x['Total Value'], reverse=True)

md_content = "# Storage Inventory Valuation\n\n"
md_content += "Based on current overall median market prices.\n\n"
md_content += f"**Total Estimated Storage Value: {total_stash_value:,.2f} g**\n\n"

md_content += "| Item | Quantity | Median Price (ea) | Total Value |\n"
md_content += "| :--- | :--- | :--- | :--- |\n"

for r in results:
    if r['Found']:
        md_content += f"| {r['Item']} | {r['Quantity']} | {r['Median Price']:.2f} g | **{r['Total Value']:,.2f} g** |\n"
    else:
        md_content += f"| {r['Item']} | {r['Quantity']} | N/A (Not Found) | N/A |\n"

output_file = "storage_valuation.md"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(md_content)

print(f"Successfully evaluated inventory. Report saved to {output_file}")
print(f"Total Valued: {total_stash_value:,.2f}g")
