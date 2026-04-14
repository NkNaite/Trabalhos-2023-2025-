import json
import os

def main():
    # Relative Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_dir = os.path.join(base_dir, "temp")
    data_dir = os.path.join(base_dir, "data")
    
    # Source is now in data/
    source_path = os.path.join(data_dir, "pax_tools_data.json")
    output_path = os.path.join(data_dir, "catalogo_manufatura.json")
    
    if not os.path.exists(source_path):
        print(f"Source file missing: {source_path}")
        return

    print("Loading raw data...")
    with open(source_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    items_raw = data.get('items', [])
    recipes_raw = data.get('recipes', [])
    
    print(f"Loaded {len(items_raw)} items and {len(recipes_raw)} recipes.")
    
    # 1. Build Lookups
    # Item ID -> Name, Stack
    item_lookup = {}
    # Recipe ID -> { ItemID -> BatchSize }
    recipe_yield_map = {} 

    print("Indexing Items and Yields...")
    for item in items_raw:
        iid = item.get('id')
        if not iid: continue
        
        # Store basic info
        item_lookup[iid] = {
            "name": item.get('name', f"Unknown_{iid}"),
            "uid": item.get('uid', ""),
            "stack": item.get('stack', 1),
            "tier": item.get('tier', 1)
        }
        
        # Extract Yields (Batches) from the Item's recipe references
        # The 'recipes' list in an Item object says: "This item is made by Recipe X in Batch Y"
        for r_ref in item.get('recipes', []):
            rid = r_ref.get('recipe_id')
            batch = r_ref.get('batch', 1)
            
            if rid not in recipe_yield_map:
                recipe_yield_map[rid] = {}
            
            recipe_yield_map[rid][iid] = batch

    def resolve_name(iid):
        return item_lookup.get(iid, {}).get("name", f"Item_{iid}")

    catalog = {}
    count = 0
    
    # 2. Iterate Recipes
    print("Processing Recipes...")
    for r in recipes_raw:
        rid = r.get('id')
        # The raw name of the recipe
        recipe_name = r.get('name', 'Unknown Recipe')
        
        deliverables = r.get('deliverables', [])
        if not deliverables:
            continue
            
        for product_id in deliverables:
            product_info = item_lookup.get(product_id, {})
            product_name = product_info.get("name", recipe_name)
            product_uid = product_info.get("uid", "")
            stack_size = product_info.get("stack", 1)
            
            # Handle dictionary names
            if isinstance(product_name, dict):
                product_name = product_name.get('En', str(product_name))

            # Disambiguate Props/Buildings
            if "building_" in product_uid or "_prop_" in product_uid:
                product_name = f"{product_name} (Prop)"
            
            # Lookup real yield
            product_yield = 1
            if rid in recipe_yield_map and product_id in recipe_yield_map[rid]:
                product_yield = recipe_yield_map[rid][product_id]
            
            # Inputs
            ingredients = []
            for ing in r.get('ingredients', []):
                ing_id = ing.get('item_id')
                qty = ing.get('qtt', 1)
                ing_name = resolve_name(ing_id)
                # Handle dictionary names
                if isinstance(ing_name, dict):
                    ing_name = ing_name.get('En', str(ing_name))
                
                ingredients.append({
                    "insumo": ing_name,
                    "qtd": qty
                })

            # Build Entry
            entry = {
                "inputs": ingredients,
                "yield": product_yield,
                "stack": stack_size,
                "ingredients": ingredients,
                "tier": product_info.get("tier", 1)
            }
            
            # If collision, we might still overwrite if we have multiple "Resource" recipes.
            # But "Charcoal (Prop)" will now not overwrite "Charcoal".
            catalog[product_name] = entry
            count += 1

    # 3. Save
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=4, ensure_ascii=False)
        
    print(f"Success! Converted {count} recipes to {output_path}")

if __name__ == "__main__":
    main()
