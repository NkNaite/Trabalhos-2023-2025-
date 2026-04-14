import json

with open('d:/PaxDei_Tool/data/pax_tools_data.json', 'r', encoding='utf-8') as f:
    pax_data = json.load(f)

print("Sample items from pax_tools_data.json:")
count = 0
for item_id, item_data in pax_data.items():
    name = item_data.get('name', '').lower()
    if 'sword' in name or 'axe' in name or 'helm' in name or 'armor' in name or 'tool' in name or 'wrought' in name:
        print(f"ID: {item_id}, Name: {item_data.get('name')}, Category: {item_data.get('category')}, Rarity: {item_data.get('rarity')}, Tags: {item_data.get('tags')}")
        count += 1
        if count >= 10:
            break
