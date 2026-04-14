import json

with open('d:/PaxDei_Tool/data/items.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for k, v in list(data.items()):
    if 'Iron' in k or 'Steel' in k or 'Wrought' in k:
        name = v.get('name', {}).get('En', 'Unknown') if isinstance(v, dict) and 'name' in v else str(v)
        if isinstance(v, dict) and ('weapon' in str(v).lower() or 'armor' in str(v).lower() or 'tool' in str(v).lower()):
            print(f"Key: {k}, En: {name}, Data keys: {list(v.keys())}")
        elif isinstance(v, dict):
            # Print at least one to see structure
            pass
        
for k, v in list(data.items())[:2]:
    print(k, v)
