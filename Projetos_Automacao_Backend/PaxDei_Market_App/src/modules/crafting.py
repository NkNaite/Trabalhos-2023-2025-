
import json
import pandas as pd
import os

class CraftingAnalyzer:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.bom_file = os.path.join(data_dir, "catalogo_manufatura.json")
        self.prices_file = os.path.join(data_dir, "selene_latest.parquet")

    def _build_price_lookup(self, df_prices):
        """Standardizes listing data for easier access."""
        # Clean col names
        if 'UnitPrice' in df_prices.columns:
            # Prevent duplicate 'Price' columns if both exist
            if 'Price' in df_prices.columns:
                df_prices = df_prices.drop(columns=['Price'])
            df_prices = df_prices.rename(columns={'UnitPrice': 'Price'})
        
        # Group all listings
        self.listings_map = {}
        grouped = df_prices.groupby('Item')
        for item, group in grouped:
            self.listings_map[item] = group.sort_values('Price')

    def calculate_material_cost(self, item_name, required_qty):
        """
        Smart Sourcing: Walking the order book.
        - Fills required_qty from cheapest listings.
        - Penalty: 5% cost increase per additional zone used.
        """
        listings = self.listings_map.get(item_name)
        if listings is None or listings.empty:
            return None, [], {}

        collected_qty = 0
        total_cost = 0
        participating_zones = set()
        details = []

        for _, row in listings.iterrows():
            if collected_qty >= required_qty:
                break
            
            # Simplified Walk: Assume availability
            available = 9999 
            take = min(required_qty - collected_qty, available)
            
            cost = take * row['Price']
            total_cost += cost
            collected_qty += take
            participating_zones.add(row['Zone'])
            
        # Penalty Logic
        zone_penalty = max(0, len(participating_zones) - 1) * 0.05
        final_cost = total_cost * (1 + zone_penalty)
        
        detail_str = f"{item_name}: {len(participating_zones)} Zones (+{zone_penalty*100:.0f}%)"
        
        # Detailed Breakdown for Blueprint
        breakdown = {
            'Item': item_name,
            'Qty_Needed': required_qty,
            'Qty_Found': collected_qty,
            'Total_Cost': final_cost,
            'Avg_Unit_Cost': final_cost / collected_qty if collected_qty > 0 else 0,
            'Zones': list(participating_zones)
        }
        
        return final_cost, [detail_str], breakdown

    def calculate_sell_price(self, item_name):
        """
        Stock-Weighted Median: Price where 50% of market stock is found.
        """
        listings = self.listings_map.get(item_name)
        if listings is None or listings.empty:
            return 0, "No Data"
        
        metric = listings['Price'].median()
        return metric, "Median"

    def analyze_profitability(self):
        """Calculates spread for all recipes using Smart Sourcing."""
        if not os.path.exists(self.bom_file) or not os.path.exists(self.prices_file):
            return None

        with open(self.bom_file, 'r', encoding='utf-8') as f:
            bom_catalog = json.load(f)
            
        df_prices = pd.read_parquet(self.prices_file)
        self._build_price_lookup(df_prices)
        
        results = []
        
        for product, recipe_data in bom_catalog.items():
            # Sell Price (Weighted Median)
            sell_price, _ = self.calculate_sell_price(product)
            if sell_price <= 0:
                continue
            
            # Handle Schema: Dict or List (Legacy Check)
            if isinstance(recipe_data, list):
                # Legacy List format (assume Yield=1)
                ingredients = recipe_data
                product_yield = 1
                stack_size = 1
            else:
                # New Dict format
                ingredients = recipe_data.get('ingredients', [])
                product_yield = recipe_data.get('yield', 1)
                stack_size = recipe_data.get('stack', 1)
            
            total_cost = 0
            sourcing_notes = []
            possible = True
            
            for ing in ingredients:
                ing_name = ing['insumo']
                qty = ing['qtd']
                
                # Smart Sourcing
                cost, details, _ = self.calculate_material_cost(ing_name, qty)
                
                if cost is None:
                    possible = False
                    break
                    
                total_cost += cost
                sourcing_notes.extend(details)
                
            if possible:
                # Cost is for the WHOLE BATCH.
                # Unit Cost = Total Batch Cost / Yield
                unit_cost = total_cost / product_yield
                
                spread = sell_price - unit_cost
                margin = (spread / sell_price) * 100 if sell_price > 0 else 0
                
                results.append({
                    'Produto': product,
                    'Yield': product_yield,
                    'Stack': stack_size,
                    'Custo_Manufatura': round(unit_cost, 2), # Per Unit!
                    'Preco_Venda': round(sell_price, 2),
                    'Spread': round(spread, 2),
                    'Margem_Perc': round(margin, 1),
                    'Mercado_Venda': "Median", 
                    'Sourcing_Insumos': "; ".join(sourcing_notes),
                    'Tier': recipe_data.get('tier', 1)
                })
                
        if not results:
            return pd.DataFrame()
            
        df_results = pd.DataFrame(results)
        return df_results.sort_values(by='Spread', ascending=False)

    def get_crafting_blueprint(self, item_name):
        """Returns detailed crafting plan."""
        if not os.path.exists(self.bom_file):
            return None
            
        with open(self.bom_file, 'r', encoding='utf-8') as f:
            bom = json.load(f)
            
        recipe = bom.get(item_name)
        if not recipe:
            return None
            
        # Ensure we have prices
        if not hasattr(self, 'listings_map'):
             if os.path.exists(self.prices_file):
                 self._build_price_lookup(pd.read_parquet(self.prices_file))
             else:
                 return None

        # Normalize recipe
        if isinstance(recipe, list):
             ingredients = recipe
             yield_amt = 1
        else:
             ingredients = recipe.get('ingredients', [])
             yield_amt = recipe.get('yield', 1)

        blueprint = {
            'Product': item_name,
            'Yield': yield_amt,
            'Ingredients': []
        }
        
        total_cost = 0
        
        for ing in ingredients:
            ing_name = ing['insumo']
            qty = ing['qtd']
            
            cost, _, breakdown = self.calculate_material_cost(ing_name, qty)
            
            if cost is None:
                blueprint['Status'] = 'Missing Materials'
                return blueprint
                
            blueprint['Ingredients'].append(breakdown)
            total_cost += cost
            
        blueprint['Total_Batch_Cost'] = total_cost
        blueprint['Unit_Cost'] = total_cost / yield_amt
        blueprint['Sell_Price'], _ = self.calculate_sell_price(item_name)
        blueprint['Profit'] = blueprint['Sell_Price'] - blueprint['Unit_Cost']
        
        return blueprint

    def recipe_breakdown(self, item_name, recursive=True):
        """
        Recursively resolves recipe ingredients to find raw materials and complexity.
        """
        if not os.path.exists(self.bom_file):
            return None
            
        with open(self.bom_file, 'r', encoding='utf-8') as f:
            bom = json.load(f)
            
        recipe_info = bom.get(item_name)
        if not recipe_info:
             return None

        # Tier Info
        tier = recipe_info.get('tier', 0) if isinstance(recipe_info, dict) else 0

        raw_materials = {}
        intermediates = {}
        complexity_sc = 0 # Using different variable name to avoid confusion
        
        def _resolve(current_item, qty_needed=1, depth=0):
            nonlocal complexity_sc
            recipe = bom.get(current_item)
            
            # If no recipe, it's a raw material (or base item)
            if not recipe:
                if current_item not in raw_materials:
                    raw_materials[current_item] = 0
                raw_materials[current_item] += qty_needed
                complexity_sc += 1
                return

            # It's an intermediate or final product
            if depth > 0:
                 if current_item not in intermediates:
                     intermediates[current_item] = 0
                 intermediates[current_item] += qty_needed
            
            # Recipe Handling
            if isinstance(recipe, list):
                ingredients = recipe
                yield_amt = 1
            else:
                ingredients = recipe.get('ingredients', [])
                yield_amt = recipe.get('yield', 1)
            
            # Scaling Factor: How many times run recipe to get qty_needed
            # E.g. Need 10. Yield 5. Run 2 times.
            runs = qty_needed / yield_amt

            if recursive:
                for ing in ingredients:
                    ing_name = ing['insumo']
                    ing_qty = ing['qtd']
                    total_ing_needed = runs * ing_qty
                    _resolve(ing_name, total_ing_needed, depth + 1)
            else:
                pass 

        _resolve(item_name)
        
        return {
            'Item': item_name,
            'Tier': tier,
            'Complexity': complexity_sc,
            'Raw_Materials': raw_materials,
            'Intermediates': intermediates
        }
