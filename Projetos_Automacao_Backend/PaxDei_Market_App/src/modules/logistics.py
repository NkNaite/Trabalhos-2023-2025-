# === AI AGENT SAFETY DIRECTIVE (DO NOT IGNORE) ===
# 1. NO INFINITE LOOPS: Ensure all loops have break conditions or maximum iterations.
# 2. DATA RESOURCE ECONOMY: Avoid reading large files (e.g., >100MB) directly in the API loop.
#    Use pre-aggregated summaries or indexed data.
# 3. NO SYSTEM OVERLOAD: If a task takes more than 5s, implement a background worker or abort.
# 4. MONITORING: Always log start/end/error for heavy operations.

import networkx as nx
import heapq
import os
import pandas as pd
from datetime import datetime, timedelta

# Constants provided by user
GRACE_TO_GOLD = 3.0
WALK_TIME_MINUTES = 5.0  
SUICIDE_TIME_MINUTES = 2.0
JUMP_COST_FRESH = 0.0 # Free
JUMP_COST_RECENT = 20.0 * GRACE_TO_GOLD  # 60 Gold
JUMP_COST_REPEATED = 30.0 * GRACE_TO_GOLD # 90 Gold 

class PaxTopology:
    # --- DATA DEFINITIONS ---
    KERYS_ZONES = {
        0: ["Pladenn", "Retz", "Llydaw", "Dolavon"], # Acesso Imediato
        1: ["Bronyr", "Aven", "Dreger"],            # Vizinhança
        2: ["Ewyas", "Vanes", "Tremen"]             # Fundo do Mapa
    }
    KERYS_NEIGHBORS = {
        "Pladenn": ["Dreger", "Bronyr", "Dolavon"],
        "Retz": ["Dolavon", "Llydaw"],
        "Llydaw": ["Retz", "Dolavon", "Tremen"],
        "Dolavon": ["Pladenn", "Bronyr", "Aven", "Tremen", "Llydaw", "Retz"],
        "Bronyr": ["Dreger", "Ewyas", "Aven", "Dolavon", "Pladenn"],
        "Aven": ["Bronyr", "Ewyas", "Vanes", "Tremen", "Dolavon"],
        "Dreger": ["Ewyas", "Bronyr", "Pladenn"],
        "Ewyas": ["Dreger", "Bronyr", "Aven", "Vanes"],
        "Vanes": ["Ewyas", "Aven", "Tremen"],
        "Tremen": ["Vanes", "Aven", "Dolavon", "Llydaw"]
    }

    MERRIE_ZONES = {
        0: ["Yarborn", "Ulaid", "Gael"],
        1: ["Caster", "Down", "Ardbog"],
        2: ["Shire", "Bearm", "Wiht", "Nene"]
    }
    MERRIE_NEIGHBORS = {
        "Yarborn": ["Ulaid", "Ardbog"],
        "Ulaid": ["Gael", "Caster", "Down", "Yarborn"],
        "Gael": ["Ulaid", "Caster"],
        "Caster": ["Gael", "Ulaid", "Down", "Shire"],
        "Down": ["Ulaid", "Caster", "Shire", "Wiht", "Nene", "Ardbog"],
        "Ardbog": ["Yarborn", "Down", "Nene"],
        "Shire": ["Caster", "Down", "Wiht", "Bearm"],
        "Bearm": ["Shire", "Wiht"],
        "Wiht": ["Bearm", "Shire", "Down", "Nene"],
        "Nene": ["Wiht", "Down", "Ardbog"]
    }

    ANCIEN_ZONES = {
        0: ["Gravas", "Volvestre"],
        1: ["Tolosa", "Lavedan", "Armanhac", "Astarac"],
        2: ["Maremna", "Salias", "Libornes", "Tursan"]
    }
    ANCIEN_NEIGHBORS = {
        "Gravas": ["Astarac", "Volvestre"],
        "Volvestre": ["Gravas", "Astarac", "Lavedan", "Tolosa"],
        "Tolosa": ["Volvestre", "Lavedan"],
        "Lavedan": ["Tolosa", "Volvestre", "Astarac", "Salias", "Armanhac"],
        "Armanhac": ["Lavedan", "Maremna"],
        "Astarac": ["Gravas", "Volvestre", "Lavedan", "Salias", "Tursan"],
        "Maremna": ["Armanhac", "Salias", "Libornes"],
        "Salias": ["Lavedan", "Astarac", "Tursan", "Libornes", "Maremna"],
        "Libornes": ["Maremna", "Salias", "Tursan"],
        "Tursan": ["Libornes", "Salias", "Astarac"]
    }

    INIS_GALLIA_ZONES = {
        0: ["Atigny", "Aras", "Javerdus", "Jura"],
        1: ["Vitry", "Langres"],
        2: ["Ardennes", "Morvan", "Trecassis", "Nones"]
    }
    INIS_GALLIA_NEIGHBORS = {
        "Atigny": ["Aras", "Jura", "Javerdus"],
        "Aras": ["Atigny", "Jura", "Vitry"],
        "Javerdus": ["Atigny", "Jura", "Langres"],
        "Jura": ["Aras", "Atigny", "Javerdus", "Langres", "Vitry"],
        "Vitry": ["Aras", "Jura", "Ardennes", "Nones"],
        "Langres": ["Javerdus", "Jura", "Trecassis"],
        "Ardennes": ["Vitry", "Nones"],
        "Morvan": ["Nones", "Trecassis"],
        "Trecassis": ["Langres", "Nones", "Morvan"],
        "Nones": ["Ardennes", "Vitry", "Trecassis", "Morvan"]
    }
    
    PROVINCES = {
        "Kerys": {"zones": KERYS_ZONES, "neighbors": KERYS_NEIGHBORS},
        "Merrie": {"zones": MERRIE_ZONES, "neighbors": MERRIE_NEIGHBORS},
        "Ancien": {"zones": ANCIEN_ZONES, "neighbors": ANCIEN_NEIGHBORS},
        "Inis Gallia": {"zones": INIS_GALLIA_ZONES, "neighbors": INIS_GALLIA_NEIGHBORS}
    }

    @classmethod
    def get_freight_index(cls, province, zone_name):
        """Returns Tier (0, 1, 2) or None if not found."""
        if province not in cls.PROVINCES: return None
        zones_map = cls.PROVINCES[province]["zones"]
        for tier, zones_list in zones_map.items():
            if zone_name in zones_list: return tier
        return None

class PaxLogistics:
    def __init__(self):
        self.full_graph = nx.DiGraph()
        self.hub_node = "Lyonesse_Hub"
        self._build_world()
        
    def _build_world(self):
        self.full_graph.add_node(self.hub_node, type="hub", province="Lyonesse", name="Hub")
        
        for prov_name, data in PaxTopology.PROVINCES.items():
            zones_map = data["zones"]
            neighbors_map = data["neighbors"]
            
            # Create Portal Node ("Base/Portao")
            portal_node = f"{prov_name}_Portal"
            self.full_graph.add_node(portal_node, type="portal", province=prov_name, name="Portal")
            
            # Connect Portal to Hub
            self.full_graph.add_edge(portal_node, self.hub_node, type="hub_teleport")
            self.full_graph.add_edge(self.hub_node, portal_node, type="hub_teleport")
            
            # Create Zone Nodes
            for tier, zones_list in zones_map.items():
                for z in zones_list:
                    node_id = f"{prov_name}_{z}"
                    self.full_graph.add_node(node_id, type="petra", province=prov_name, name=z, tier=tier)
                    
                    # Connect Tier 0 to Portal (Walking access to gate)
                    if tier == 0:
                        self.full_graph.add_edge(node_id, portal_node, type="walk")
                        self.full_graph.add_edge(portal_node, node_id, type="walk")

            # Create Walking Connections from Neighbors
            for z, neighbors in neighbors_map.items():
                p1 = f"{prov_name}_{z}"
                for n in neighbors:
                    p2 = f"{prov_name}_{n}"
                    # Allow edges regardless of definition order, NX handles dupes fine
                    if self.full_graph.has_node(p1) and self.full_graph.has_node(p2):
                        self.full_graph.add_edge(p1, p2, type="walk")
                        # Neighbors dict is usually defining neighbors one way, but graph is undirected
                        # But wait, user provided neighbors for EVERY zone explicitly.
                        # So simply iterating all is fine.
            
        # Inter-Province Connections (Frontier Jumps)
        # Ring Topology Assumption for Portals
        provinces_list = list(PaxTopology.PROVINCES.keys())
        for i in range(len(provinces_list)):
            p1 = f"{provinces_list[i]}_Portal"
            p2 = f"{provinces_list[(i+1)%len(provinces_list)]}_Portal"
            self.full_graph.add_edge(p1, p2, type="portal_jump")
            self.full_graph.add_edge(p2, p1, type="portal_jump")

    def _resolve_node(self, partial_name):
        if partial_name.lower() in ["hub", "lyonesse"]: return self.hub_node
        clean_input = partial_name.lower().replace("merrie-", "").replace("kerys-", "").replace("inis_gallia-", "").replace("ancien-", "")
        shortest = None
        for node, data in self.full_graph.nodes(data=True):
            node_name = data.get("name", "").lower()
            if clean_input == node_name: return node 
            if clean_input in node_name:
                if shortest is None or len(node_name) < len(shortest):
                    shortest = node
        return shortest
    
    def _is_safe_node(self, node): return True 

    def find_best_route_dijkstra(self, start_node, end_node, safety_filter=False):
        # State: (cost_gold, cost_time, current_node, home_ready, unstuck_ready, jump_is_fresh)
        pq = [(0.0, 0.0, start_node, True, True, True, [start_node])]
        visited = set() 
        max_depth = 5000 
        count = 0
        
        while pq:
            gold, time, curr, home_ok, unstuck_ok, jump_fresh, path = heapq.heappop(pq)
            state_key = (curr, home_ok, unstuck_ok, jump_fresh)
            if state_key in visited: continue
            visited.add(state_key)
            
            if curr == end_node:
                return {"gold": gold, "time": time, "path": path} 
            
            count += 1
            if count > max_depth: break
            
            # ACTIONS
            neighbors = self.full_graph[curr]
            for neighbor, edge_data in neighbors.items():
                edge_type = edge_data.get("type")
                n_gold = 0.0
                n_time = 0.0
                n_jump_fresh = jump_fresh
                
                if edge_type == "walk":
                    n_time = WALK_TIME_MINUTES
                elif edge_type == "hub_teleport":
                    n_time = 0.5 
                    if curr == self.hub_node: # Leaving Hub
                        if jump_fresh:
                            n_gold = JUMP_COST_FRESH 
                            n_jump_fresh = False 
                        else:
                            n_gold = JUMP_COST_RECENT 
                    else: pass 
                elif edge_type == "portal_jump":
                    n_gold = JUMP_COST_RECENT 
                    n_time = 0.5
                
                new_gold = gold + n_gold
                new_time = time + n_time
                new_path = path + [f"Travel({edge_type})->{neighbor}"]
                heapq.heappush(pq, (new_gold, new_time, neighbor, home_ok, unstuck_ok, n_jump_fresh, new_path))
            
            if curr != self.hub_node and home_ok:
                new_path = path + ["Ability:Petra_Home->Hub"]
                heapq.heappush(pq, (gold, time + 0.5, self.hub_node, False, unstuck_ok, jump_fresh, new_path))
            
            if not home_ok:
                new_path = path + ["Action:Suicide(Reset_Home)"]
                heapq.heappush(pq, (gold, time + SUICIDE_TIME_MINUTES, curr, True, unstuck_ok, jump_fresh, new_path))

            if unstuck_ok:
                if "Portal" in curr: # Wait, "Portal" node is Abstract. 
                    # If I am at "Merrie_Portal", nearest Petra is any Tier 0 petra.
                    # Let's find neighbors that are "petra".
                    for n in self.full_graph.neighbors(curr):
                         if self.full_graph.nodes[n].get("type") == "petra":
                             new_path = path + [f"Ability:Unstuck->{n}"]
                             heapq.heappush(pq, (gold, time + 0.5, n, home_ok, False, jump_fresh, new_path))
                             break
                elif "petra" in self.full_graph.nodes[curr].get("type", ""):
                     # Already at Petra, Unstuck goes to "Nearest". 
                     # For simplicity, self or neighbor?
                     # Let's assume Unstuck doesn't help if already at Petra unless you are stuck in geometry.
                     pass 

        return None

    def compare_routes(self, origin, destination):
        start_node = self._resolve_node(origin)
        end_node = self._resolve_node(destination)
        if not start_node or not end_node: return None
        res = self.find_best_route_dijkstra(start_node, end_node)
        def fmt(res):
            if not res: return {"cost": -1, "path": []}
            return {"cost": f"{res['gold']:.0f}g ({res['time']:.0f}m)", "path": res['path'], "raw_gold": res['gold']}
        return {"origin": origin, "destination": destination, "safe_route": fmt(res), "pvp_route": fmt(res)}

class ArbitrageFinder:
    def __init__(self, data_dir):
        self.listings_file = os.path.join(data_dir, "selene_latest.parquet")
        self.liquidity_file = os.path.join(data_dir, "liquidez_diaria.csv")
        self.catalog_file = os.path.join(data_dir, "catalogo_manufatura.json")
        self.data_dir = data_dir
        self._load_tiers()

    def _load_tiers(self):
        self.item_tiers = {}
        if os.path.exists(self.catalog_file):
            try:
                import json
                with open(self.catalog_file, 'r', encoding='utf-8') as f:
                    catalog = json.load(f)
                    for item, details in catalog.items():
                        if isinstance(details, dict):
                            self.item_tiers[item] = details.get('tier', 1)
            except: pass

    def find_opportunities(self, budget=2000.0, min_margin=15.0, province=None):
        if not os.path.exists(self.listings_file): return pd.DataFrame()
        df_listings = pd.read_parquet(self.listings_file)
        
        p_col = 'UnitPrice' if 'UnitPrice' in df_listings.columns else 'Price'
        if p_col not in df_listings.columns:
             df_listings['UnitPrice'] = df_listings['Price'] / (df_listings['Amount'] if 'Amount' in df_listings.columns else 1)
             p_col = 'UnitPrice'

        # 1. OBTER MEDIANA DE 7 DIAS (REFERÊNCIA DE VENDA)
        # TENTAR CARREGAR DO RESUMO PRÉ-AGREGADO (MUITO MAIS RÁPIDO)
        summary_path = os.path.join(self.data_dir, "7d_medians.json")
        reference_medians = {}
        
        if os.path.exists(summary_path):
            try:
                import json
                with open(summary_path, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
                    if province and province in summary_data.get('regional_7d', {}):
                        reference_medians = summary_data['regional_7d'][province]
                        print(f"Arbitrage: Using pre-aggregated regional medians for {province}.")
                    else:
                        reference_medians = summary_data.get('global_7d', {})
                        print("Arbitrage: Using pre-aggregated global medians.")
            except Exception as e:
                print(f"Error reading pre-aggregated summary: {e}")

        # FALLBACK: Se o resumo falhar ou não existir, calcular manualmente (PESADO)
        if not reference_medians:
            print("Arbitrage Warning: Pre-aggregated summary not found. Calculating from history (SLOW)...")
            from modules.market import MarketAnalyzer
            analyzer = MarketAnalyzer(self.data_dir)
            cutoff = datetime.now() - timedelta(days=7)
            
            try:
                history_df = analyzer.load_all_history(
                    columns=['Item', 'Price', 'Zone', 'SnapshotDate'],
                    filters=[('SnapshotDate', '>=', cutoff)]
                )
                if not history_df.empty:
                    if province:
                        history_df = history_df[history_df['Zone'].str.lower().str.startswith(province.lower(), na=False)]
                    reference_medians = history_df.groupby('Item')['Price'].median().to_dict()
            except Exception as e:
                print(f"Error loading history for arbitrage: {e}")

        # ÚLTIMO RECURSO: Usar snapshot atual
        if not reference_medians:
            print("Arbitrage Fallback: Using current snapshot medians.")
            reference_medians = df_listings.groupby('Item')[p_col].median().to_dict()

        # 2. IDENTIFICAR PECHINCHAS (LISTAGENS ATUAIS ABAIXO DA MEDIANA)
        # Consider all possible deals globally (Price under budget)
        df_affordable = df_listings[df_listings[p_col] <= budget].copy()
        
        # Map reference medians
        df_affordable['Ref_Median'] = df_affordable['Item'].map(reference_medians)
        df_affordable = df_affordable[df_affordable['Ref_Median'] > 0]
        
        # Desconto em relação à mediana de referência (7 dias)
        df_affordable['Discount_Pct'] = ((df_affordable['Ref_Median'] - df_affordable[p_col]) / df_affordable['Ref_Median']) * 100
        
        # Focus on items with good discount
        df_deals = df_affordable[df_affordable['Discount_Pct'] >= min_margin].copy()
        
        if df_deals.empty: return pd.DataFrame()

        if os.path.exists(self.liquidity_file):
            df_liquidity = pd.read_csv(self.liquidity_file)
            avg_sold = df_liquidity.set_index('Item')['Units_Sold'].to_dict()
        else:
            avg_sold = {}

        results = []
        
        for _, row in df_deals.iterrows():
            item = row['Item']
            buy_zone = row['Zone']
            buy_price = row[p_col]
            
            # O preço de venda agora é fixo pela mediana de referência calculada
            sell_price = reference_medians.get(item, 0)
            
            if sell_price > buy_price:
                unit_profit = sell_price - buy_price
                margin = (unit_profit / buy_price) * 100
                score = unit_profit * avg_sold.get(item, 1) 
                
                results.append({
                    'Item': item,
                    'Buy_Price': buy_price,
                    'Buy_Zone': buy_zone,
                    'Sell_Zone': province if province else "Global (7d Median)",
                    'Avg_Sale_Price': sell_price,
                    'Unit_Profit': unit_profit,
                    'Margin': margin,
                    'Score': score,
                    'Amount_Available': row['Amount'] if 'Amount' in row else 1
                })
        
        if not results: return pd.DataFrame()
        
        res = pd.DataFrame(results)
        res = res.sort_values(by='Score', ascending=False)
        res['Tier'] = res['Item'].map(self.item_tiers).fillna(1).astype(int)
        
        # Trava de Segurança: Retornar no máximo as top 1000 oportunidades para não estourar a memória
        return res.head(1000)

class RouteScanner:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.latest_file = os.path.join(data_dir, "selene_latest.parquet")
        self.history_dir = os.path.join(data_dir, "history")
        self.client_orders_file = os.path.join(data_dir, "client_orders.csv")

    def _normalize_zone(self, zone_str):
        if not isinstance(zone_str, str): return ""
        return zone_str.lower()

    def _is_zone_match(self, zone_full, interests):
        norm = self._normalize_zone(zone_full)
        return any(z in norm for z in interests)

    def get_client_items(self):
        if not os.path.exists(self.client_orders_file):
            return []
        df = pd.read_csv(self.client_orders_file)
        return df['Item'].dropna().unique().tolist()

    def scan_current_market(self, zones_of_interest):
        if not os.path.exists(self.latest_file):
            return pd.DataFrame()

        df = pd.read_parquet(self.latest_file)
        client_items = self.get_client_items()
        
        # Filter for client items
        mask_items = df['Item'].isin(client_items)
        df_items = df[mask_items].copy()
        
        if df_items.empty:
            return pd.DataFrame()

        # Calculate Median Price per Item (Server-wide)
        medians = df_items.groupby('Item')['Price'].median().reset_index().rename(columns={'Price': 'Median_Price'})
        df_items = df_items.merge(medians, on='Item')
        
        # Filter for Target Zones
        df_items['In_Route'] = df_items['Zone'].apply(lambda x: self._is_zone_match(x, zones_of_interest))
        df_route = df_items[df_items['In_Route']].copy()
        
        # Filter for Discount (Price < Median)
        df_opportunities = df_route[df_route['Price'] < df_route['Median_Price']].copy()
        if df_opportunities.empty:
            return pd.DataFrame()

        df_opportunities['Discount_%'] = ((df_opportunities['Median_Price'] - df_opportunities['Price']) / df_opportunities['Median_Price']) * 100
        return df_opportunities.sort_values('Discount_%', ascending=False)

    def scan_history_producers(self, item_filter=None):
        import glob
        search_path = os.path.join(self.history_dir, "**", "*.parquet")
        files = glob.glob(search_path, recursive=True)
        
        if not files: return pd.DataFrame()

        dfs = []
        for f in files:
            try:
                # Only load necessary columns
                df = pd.read_parquet(f, columns=['Item', 'SellerHash', 'Zone', 'Amount', 'ListingID'])
                dfs.append(df)
            except: pass
            
        if not dfs: return pd.DataFrame()

        full_df = pd.concat(dfs, ignore_index=True)
        
        if item_filter:
            mask = full_df['Item'].isin(item_filter)
            relevant_df = full_df[mask].copy()
        else:
            relevant_df = full_df
            
        if relevant_df.empty: return pd.DataFrame()
        
        # Aggregation
        stats = relevant_df.groupby(['Item', 'SellerHash']).agg({
            'Amount': 'sum',
            'ListingID': 'count',
            'Zone': lambda x: sorted(list(set(x)))[:3] # Sample zones
        }).reset_index()
        
        stats.rename(columns={'Amount': 'Total_Volume', 'ListingID': 'Frequency'}, inplace=True)
        return stats.sort_values(['Item', 'Total_Volume'], ascending=[True, False])

