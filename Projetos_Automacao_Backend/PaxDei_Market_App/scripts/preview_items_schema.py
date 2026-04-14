import json
with open('d:/PaxDei_Tool/data/items.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print("items.json sample:")
    for k, v in list(data.items())[:2]:
        print(f"{k}: {v}")

with open('d:/PaxDei_Tool/data/pax_tools_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print("\npax_tools_data.json sample:")
    for k, v in list(data.items())[:2]:
        print(f"{k}: {v}")
