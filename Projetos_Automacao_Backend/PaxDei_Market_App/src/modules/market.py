
# === AI AGENT SAFETY DIRECTIVE (DO NOT IGNORE) ===
# 1. NO INFINITE LOOPS: Ensure all loops have break conditions or maximum iterations.
# 2. DATA RESOURCE ECONOMY: Avoid reading large files (e.g., >100MB) directly in the API loop.
#    Use pre-aggregated summaries or indexed data.
# 3. NO SYSTEM OVERLOAD: If a task takes more than 5s, implement a background worker or abort.
# 4. MONITORING: Always log start/end/error for heavy operations.

import pandas as pd
import os
import glob
from datetime import datetime, timedelta

class MarketAnalyzer:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.history_dir = os.path.join(data_dir, "history")
        self.listings_file = os.path.join(data_dir, "selene_latest.parquet")
        self.catalog_file = os.path.join(data_dir, "catalogo_manufatura.json")
        self._load_tiers()

    def _load_tiers(self):
        """Loads item tiers from catalog."""
        self.item_tiers = {}
        if os.path.exists(self.catalog_file):
            try:
                import json
                with open(self.catalog_file, 'r', encoding='utf-8') as f:
                    catalog = json.load(f)
                    for item, details in catalog.items():
                        if isinstance(details, dict):
                            self.item_tiers[item] = details.get('tier', 1)
                        else:
                            # Default for items without explicit tier structure
                            self.item_tiers[item] = 1
            except Exception as e:
                print(f"Error loading tiers: {e}")

    def _attach_tiers(self, df, item_col='Item'):
        """Attaches tier info to a dataframe."""
        if df is None or df.empty:
            return df
        
        # Simple map
        df['Tier'] = df[item_col].map(self.item_tiers).fillna(1).astype(int)
        return df

    def load_all_history(self, columns=None, filters=None):
        """Loads aggregated history if available, else falls back to individual files."""
        full_history_path = os.path.join(self.data_dir, "full_history.parquet")
        
        if os.path.exists(full_history_path):
            try:
                return pd.read_parquet(full_history_path, columns=columns, filters=filters)
            except Exception as e:
                print(f"Error reading aggregated history: {e}. Falling back to individual files.")
        
        # Fallback to slow loading
        search_path = os.path.join(self.history_dir, "**", "*.parquet")
        files = glob.glob(search_path, recursive=True)
        
        if not files:
            return pd.DataFrame()
            
        dfs = []
        # Exigência do utilizador: aplicar também o limite de data no fallback manual.
        # Procuramos o filtro de data nos argumentos:
        min_date = None
        if filters:
            for f in filters:
                if f[0] == 'SnapshotDate' and f[1] == '>=':
                    min_date = f[2]
        
        for f in files:
            try:
                # Extract date from filename: market_YYYY-MM-DD_HH-MM.parquet
                basename = os.path.basename(f)
                timestamp_str = basename.replace("market_", "").replace(".parquet", "")
                try:
                    snapshot_date = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M")
                except ValueError:
                    snapshot_date = datetime.fromtimestamp(os.path.getmtime(f))
                
                # Se tivermos um filtro de data mínima, pulamos arquivos muito antigos
                if min_date and snapshot_date < min_date:
                    continue
                
                df = pd.read_parquet(f)
                df['SnapshotDate'] = snapshot_date
                dfs.append(df)
            except Exception as e:
                print(f"Skipping {f}: {e}")
                
        if not dfs:
            return pd.DataFrame()
            
        return pd.concat(dfs, ignore_index=True)

    def get_item_history(self, item_name):
        """Analyzes a specific item across snapshots."""
        # Filtra o nome exato do item na base de dados parquety via C++ pra não dar OOM e especifica as colunas certas.
        cols_to_load = ['Item', 'SnapshotDate', 'Price', 'ListingID', 'Zone']
        try:
             full_df = self.load_all_history(
                 columns=cols_to_load,
                 filters=[("Item", "==", item_name)]
             )
        except Exception:
             full_df = self.load_all_history(columns=cols_to_load)

        if full_df.empty:
            return None

        # Filter by substring as fallback (case insensitive) if direct filter failed
        if len(full_df) > 0 and len(full_df['Item'].unique()) > 1:
            mask = full_df['Item'].astype(str).str.contains(item_name, case=False, na=False)
            item_df = full_df[mask].copy()
        else:
            item_df = full_df.copy()
            
        if item_df.empty:
            return None
            
        stats = item_df.groupby('SnapshotDate').agg(
            Min_Price=('Price', 'min'),
            Avg_Price=('Price', 'mean'),
            Median_Price=('Price', 'median'),
            Stock_Count=('ListingID', 'count'),
            Zones=('Zone', lambda x: list(set(x)))
        ).sort_values('SnapshotDate')
        
        # Calculate Churn
        snapshots = sorted(item_df['SnapshotDate'].unique())
        churn_data = []
        
        for i in range(len(snapshots) - 1):
            t0 = snapshots[i]
            t1 = snapshots[i+1]
            
            ids_t0 = set(item_df[item_df['SnapshotDate'] == t0]['ListingID'])
            ids_t1 = set(item_df[item_df['SnapshotDate'] == t1]['ListingID'])
            
            sold_ids = ids_t0 - ids_t1
            units_sold = len(sold_ids)
            
            # Volume
            sold_price_sum = item_df[(item_df['SnapshotDate'] == t0) & (item_df['ListingID'].isin(sold_ids))]['Price'].sum()
            
            churn_data.append({
                'SnapshotDate': t1,
                'Units_Sold_Since_Last': units_sold,
                'Volume_Sold': sold_price_sum
            })
            
        churn_df = pd.DataFrame(churn_data)
        
        if not churn_df.empty:
            stats = stats.merge(churn_df, on='SnapshotDate', how='left')
        else:
            stats['Units_Sold_Since_Last'] = 0
            stats['Volume_Sold'] = 0
            
        return stats

    def check_liquidity(self):
        """Compares the last two snapshots to find sold items (churn)."""
        search_path = os.path.join(self.history_dir, "**", "*.parquet")
        files = glob.glob(search_path, recursive=True)
        files.sort()
        
        if len(files) < 2:
            return None
            
        old_file, new_file = files[-2], files[-1]
        
        try:
            df_old = pd.read_parquet(old_file)
            df_new = pd.read_parquet(new_file)
        except Exception as e:
            print(f"Error reading parquet files: {e}")
            return None
            
        old_ids = set(df_old['ListingID'].dropna().unique())
        new_ids = set(df_new['ListingID'].dropna().unique())
        
        sold_ids = old_ids - new_ids
        
        if not sold_ids:
            return pd.DataFrame()
            
        sold_df = df_old[df_old['ListingID'].isin(sold_ids)].copy()
        
        if 'Amount' in sold_df.columns:
            liquidity_stats = sold_df.groupby('Item').agg(
                Units_Sold=('Amount', 'sum'),
                Total_Volume=('Price', 'sum')
            ).reset_index()
        else:
            liquidity_stats = sold_df.groupby('Item').agg(
                Units_Sold=('ListingID', 'count'),
                Total_Volume=('Price', 'sum')
            ).reset_index()

        # Top Zone
        zone_stats = sold_df.groupby(['Item', 'Zone']).size().reset_index(name='Zone_Count')
        zone_stats = zone_stats.sort_values(['Item', 'Zone_Count'], ascending=[True, False])
        top_zones = zone_stats.drop_duplicates(subset=['Item'])[['Item', 'Zone', 'Zone_Count']]
        top_zones.columns = ['Item', 'Top_Zone', 'Top_Zone_Sales']
        
        liquidity_stats = liquidity_stats.merge(top_zones, on='Item', how='left')
        liquidity_stats = liquidity_stats.sort_values(by='Units_Sold', ascending=False)
        
        return self._attach_tiers(liquidity_stats)

    def get_producer_stats(self, item_name):
        """Finds zones with the most unique sellers for an item."""
        cols_to_load = ['Item', 'Zone', 'SellerHash', 'ListingID']
        try:
             full_df = self.load_all_history(
                 columns=cols_to_load,
                 filters=[("Item", "==", item_name)]
             )
        except Exception:
             full_df = self.load_all_history(columns=cols_to_load)
             
        if full_df.empty:
            return None
            
        if len(full_df) > 0 and len(full_df['Item'].unique()) > 1:
             mask = full_df['Item'].astype(str).str.contains(item_name, case=False, na=False)
             item_df = full_df[mask].copy()
        else:
             item_df = full_df.copy()
        
        if item_df.empty:
            return None
            
        if 'SellerHash' not in item_df.columns:
            return None
            
        stats = item_df.groupby('Zone').agg({
            'SellerHash': 'nunique',
            'ListingID': 'nunique'
        }).rename(columns={
            'SellerHash': 'Unique_Producers',
            'ListingID': 'Unique_Listings'
        })
        
        return stats.sort_values('Unique_Producers', ascending=False)

    def get_top_sellers(self, item_name):
        """Returns the top sellers for a given item based on volume (Current Snapshot)."""
        if os.path.exists(self.listings_file):
            df = pd.read_parquet(self.listings_file)
        else:
            return None
            
        mask = df['Item'].astype(str).str.contains(item_name, case=False, na=False)
        item_df = df[mask].copy()
        
        if item_df.empty:
            return None
            
        if 'SellerHash' not in item_df.columns:
            return None
            
        # Group by SellerHash
        stats = item_df.groupby('SellerHash').agg({
            'Amount': 'sum',
            'ListingID': 'count',
            'Price': 'mean',
            'Zone': lambda x: list(set(x))
        }).rename(columns={
            'Amount': 'Total_Stock',
            'ListingID': 'Listing_Count',
            'Price': 'Avg_Price'
        })
        
        return stats.sort_values('Total_Stock', ascending=False)

    def search_items(self, query):
        """Search for items matching the query in the latest snapshot."""
        if not os.path.exists(self.listings_file):
            return []
            
        try:
            # We only need unique Item names. Reading entire file is heavy but OK for now.
            # Optimization: Cache this.
            df = pd.read_parquet(self.listings_file, columns=['Item'])
            unique_items = df['Item'].dropna().unique()
            
            # Simple substring match
            matches = [item for item in unique_items if query.lower() in item.lower()]
            return sorted(matches)[:20] # Limit to 20 results
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def get_locations(self):
        """Returns a dict mapping Provinces to their Valleys based on the latest snapshot."""
        if not os.path.exists(self.listings_file):
            return {}
        try:
            df = pd.read_parquet(self.listings_file, columns=['Zone'])
            zones = df['Zone'].dropna().unique()
            
            locations = {}
            for zone in zones:
                # Zones are typically formatted as 'province-valley' (e.g., 'kerys-langres')
                parts = str(zone).split('-')
                if len(parts) >= 2:
                    province = parts[0].strip().capitalize()
                    valley = parts[1].strip().capitalize()
                    
                    if province not in locations:
                        locations[province] = []
                    if valley not in locations[province]:
                        locations[province].append(valley)
                else:
                    # Fallback for unexpected formats
                    loc = str(zone).strip().capitalize()
                    if "Unknown" not in locations:
                        locations["Unknown"] = []
                    if loc not in locations["Unknown"]:
                        locations["Unknown"].append(loc)
                        
            # Sort the lists for the UI
            for prov in locations:
                locations[prov].sort()
                
            return locations
            
        except Exception as e:
            print(f"Error getting locations: {e}")
            return {}

    def check_demand_intensity(self):
        """
        Calculates Demand Intensity: Units Sold / Total Listed Count.
        High intensity = High demand relative to supply.
        """
        liquidity = self.check_liquidity()
        if liquidity is None or liquidity.empty:
            return pd.DataFrame()
        
        # We need current total listings count for each item to normalize
        # Check if we have the latest listings file
        if not os.path.exists(self.listings_file):
             return liquidity # Fallback to raw sales

        df_listings = pd.read_parquet(self.listings_file)
        
        # Count total items listed (supply volume in units)
        if 'Amount' in df_listings.columns:
            supply_stats = df_listings.groupby('Item')['Amount'].sum().reset_index(name='Total_Supply')
        else:
             supply_stats = df_listings.groupby('Item')['ListingID'].count().reset_index(name='Total_Supply')
             
        # Merge
        merged = liquidity.merge(supply_stats, on='Item', how='left').fillna(0)
        
        # Calculate Intensity
        # Avoid division by zero
        merged['Intensity_Score'] = merged.apply(
            lambda x: (x['Units_Sold'] * 100) / x['Total_Supply'] if x['Total_Supply'] > 0 else 0, 
            axis=1
        )
        
        return self._attach_tiers(merged)

    def get_supply_demand(self, province=None, valley=None, days=7):
        """
        Calculates the Supply/Demand ratio for the interactive table inspired by Victoria 3.
        Filters by geography and time period.
        """
        # 1. Obter a OFERTA ATUAL (Total_Supply do snapshot mais recente)
        if not os.path.exists(self.listings_file):
            return pd.DataFrame()
            
        df_supply = pd.read_parquet(self.listings_file)
        
        # Filtrar geograficamente a oferta
        if province:
            # Match start of zone string case-insensitively
            df_supply = df_supply[df_supply['Zone'].str.lower().str.startswith(province.lower(), na=False)]
            
        if valley:
            # Match the valley part. e.g. if zone is 'kerys-langres' and valley is 'langres'
            df_supply = df_supply[df_supply['Zone'].str.lower().str.contains(f"-{valley.lower()}", na=False) | 
                                  (df_supply['Zone'].str.lower() == valley.lower())]

        if df_supply.empty:
             return pd.DataFrame()

        if 'Amount' in df_supply.columns:
            supply_stats = df_supply.groupby('Item').agg(
                Total_Supply=('Amount', 'sum'),
                Total_Gold_Supply=('Price', 'sum')
            ).reset_index()
        else:
            supply_stats = df_supply.groupby('Item').agg(
                Total_Supply=('ListingID', 'count'),
                Total_Gold_Supply=('Price', 'sum')
            ).reset_index()
            
        # Optimization: Limit to top 500 items by supply to avoid computing demand for 3000+ items
        supply_stats = supply_stats.sort_values(by='Total_Supply', ascending=False).head(500)
        valid_items = set(supply_stats['Item'])
            
        # 2. Obter a DEMANDA histórica (Vendas nos últimos N dias)
        cols_to_load = ['SnapshotDate', 'ListingID', 'Item', 'Zone', 'Price']
        if 'Amount' in df_supply.columns:
            cols_to_load.append('Amount')
            
        # Calcular limite de busca inicial para o filtro Parquet (evita OOM MemoryError de ~1.5GB+)
        max_lookback = 26 if days == 7 else (14 if days == 3 else (7 if days == 1 else days))
        # Dá 2 dias de margem de segurança devido as diferenças de timezone
        safe_cutoff = datetime.now() - timedelta(days=max_lookback + 2)
        
        try:
            full_df = self.load_all_history(
                columns=cols_to_load, 
                filters=[("SnapshotDate", ">=", safe_cutoff)]
            )
        except Exception as e:
            print(f"Aggregated parquet filter failed due to {e}. Using fallback limits...")
            # Fallback (which now also respects the date filter!)
            full_df = self.load_all_history(columns=cols_to_load, filters=[("SnapshotDate", ">=", safe_cutoff)])
        
        if full_df.empty:
            # Se não houver histórico, a demanda é zero
            df_final = supply_stats.copy()
            df_final['Units_Sold'] = 0
            df_final['Gold_Sold'] = 0
            df_final['Supply_Ratio'] = 100.0 # Excesso total
            return self._attach_tiers(df_final)

        # Ensure Timestamp
        if not pd.api.types.is_datetime64_any_dtype(full_df['SnapshotDate']):
            full_df['SnapshotDate'] = pd.to_datetime(full_df['SnapshotDate'])

        # Filtrar geograficamente a demanda (histórico)
        filtered_history = full_df.copy()
        
        # Super optimization: Discard all historical data for items not in our valid current supply top 200
        filtered_history = filtered_history[filtered_history['Item'].isin(valid_items)]
        
        if province:
             filtered_history = filtered_history[filtered_history['Zone'].str.lower().str.startswith(province.lower(), na=False)]
        if valley:
             filtered_history = filtered_history[filtered_history['Zone'].str.lower().str.contains(f"-{valley.lower()}", na=False) | 
                                            (filtered_history['Zone'].str.lower() == valley.lower())]
        
        if filtered_history.empty:
            df_final = supply_stats.copy()
            df_final['Units_Sold'] = 0
            df_final['Gold_Sold'] = 0
            df_final['Supply_Ratio'] = 100.0
            return self._attach_tiers(df_final)
            
        # Determinar as janelas de tempo com base na seleção
        last_snap_global = filtered_history['SnapshotDate'].max()
        first_date_available = filtered_history['SnapshotDate'].min()
        
        if days == 1:
            lookback_total = 7; lookback_recent = 1; w_total = 0.9; w_recent = 0.1
        elif days == 3:
            lookback_total = 14; lookback_recent = 3; w_total = 0.8; w_recent = 0.2
        elif days == 7:
            lookback_total = 26; lookback_recent = 7; w_total = 0.8; w_recent = 0.2
        else:
            lookback_total = days; lookback_recent = days; w_total = 1.0; w_recent = 0.0

        def get_sales_for_period(df_period):
            if df_period.empty: return pd.DataFrame(columns=['Item', 'Units_Sold', 'Gold_Sold'])
            last_snap_p = df_period['SnapshotDate'].max()
            rh_cols = ['ListingID', 'SnapshotDate', 'Item', 'Price']
            if 'Amount' in df_period.columns: rh_cols.append('Amount')
            
            df_sub = df_period[rh_cols]
            aggd = {'SnapshotDate': 'max', 'Item': 'first', 'Price': 'first'}
            if 'Amount' in df_sub.columns: aggd['Amount'] = 'first'
                
            l_stats = df_sub.groupby('ListingID').agg(aggd)
            sold = l_stats[l_stats['SnapshotDate'] < last_snap_p]
            
            if sold.empty: return pd.DataFrame(columns=['Item', 'Units_Sold', 'Gold_Sold'])
            
            if 'Amount' in sold.columns:
                return sold.groupby('Item').agg(
                    Units_Sold=('Amount', 'sum'),
                    Gold_Sold=('Price', 'sum')
                ).reset_index()
            else:
                return sold.groupby('Item').agg(
                    Units_Sold=('ListingID', 'count'),
                    Gold_Sold=('Price', 'sum')
                ).reset_index()

        # Total Period
        cutoff_total = last_snap_global - timedelta(days=lookback_total)
        actual_total_days = max(1, (last_snap_global - max(cutoff_total, first_date_available)).days)
        df_total = filtered_history[filtered_history['SnapshotDate'] >= cutoff_total]
        sales_total = get_sales_for_period(df_total)
        
        # Recent Period
        cutoff_recent = last_snap_global - timedelta(days=lookback_recent)
        actual_recent_days = max(1, (last_snap_global - max(cutoff_recent, first_date_available)).days)
        df_recent = filtered_history[filtered_history['SnapshotDate'] >= cutoff_recent]
        sales_recent = get_sales_for_period(df_recent)
        
        # Merge recent and total
        sales_merged = pd.merge(sales_total, sales_recent, on='Item', how='outer', suffixes=('_Total', '_Recent')).fillna(0)
        
        def calculate_weighted_metric(row, col_name):
            daily_total = row[f'{col_name}_Total'] / actual_total_days
            daily_recent = row[f'{col_name}_Recent'] / actual_recent_days
            weighted_daily = (daily_total * w_total) + (daily_recent * w_recent)
            return round(weighted_daily * days, 1)

        if not sales_merged.empty:
            sales_merged['Units_Sold'] = sales_merged.apply(lambda r: calculate_weighted_metric(r, 'Units_Sold'), axis=1)
            sales_merged['Gold_Sold'] = sales_merged.apply(lambda r: calculate_weighted_metric(r, 'Gold_Sold'), axis=1)
            demand_stats = sales_merged[['Item', 'Units_Sold', 'Gold_Sold']]
        else:
            demand_stats = pd.DataFrame(columns=['Item', 'Units_Sold', 'Gold_Sold'])
        
        # 3. Mesclar Oferta e Demanda
        merged = supply_stats.merge(demand_stats, on='Item', how='left').fillna({'Units_Sold': 0, 'Gold_Sold': 0})
        
        # 3.5 Adicionar Scores Extras
        try:
            from modules.logistics import ArbitrageFinder
            from modules.crafting import CraftingAnalyzer
            
            # Arbitragem
            arb = ArbitrageFinder(os.path.dirname(self.listings_file))
            df_arb = arb.find_opportunities()
            if df_arb is not None and not df_arb.empty:
                arb_scores = df_arb.groupby('Item')['Score'].max().reset_index(name='Arbitrage_Score')
                merged = merged.merge(arb_scores, on='Item', how='left').fillna({'Arbitrage_Score': 0})
            else:
                merged['Arbitrage_Score'] = 0
                
            # Profitcraft
            craft = CraftingAnalyzer(os.path.dirname(self.listings_file))
            df_craft = craft.analyze_profitability()
            if df_craft is not None and not df_craft.empty:
                # Vamos usar Spread como proxy principal para de "Profitcraft" 
                craft_scores = df_craft[['Produto', 'Spread']].rename(columns={'Produto': 'Item', 'Spread': 'Profitcraft_Score'})
                craft_scores = craft_scores.groupby('Item')['Profitcraft_Score'].max().reset_index()
                merged = merged.merge(craft_scores, on='Item', how='left').fillna({'Profitcraft_Score': 0})
            else:
                merged['Profitcraft_Score'] = 0
                
        except Exception as e:
            print(f"Failed to generate extra scores: {e}")
            merged['Arbitrage_Score'] = 0
            merged['Profitcraft_Score'] = 0

        # 4. Calcular a Barra de Oferta (Supply Ratio) Visual
        # Multiplicador Cronológico Básico: O "peso" será 10 multiplicado pelos dias analisados.
        # Agora que a demanda já está normalizada para a escala de "days", mantemos o multiplicador simples.
        base_multiplier = 10 
        
        # Adjusted Demand = Vendas ponderadas no período * Multiplicador

        def calculate_ratio(row):
            supply = row['Total_Supply']
            demand_period = row['Units_Sold']
            
            # Se não tem oferta mas tem demanda (impossivel, mas como safety check)
            if supply == 0 and demand_period > 0:
                return 0.0 # 0% Azul (100% Vermelho)
            
            # Se não tem demanda, é 100% Azul (Excesso Total)
            if demand_period == 0:
                return 100.0
                
            # Adjusted demand relative to supply. 
            adjusted_demand = demand_period * base_multiplier
            
            ratio = (supply / (supply + adjusted_demand)) * 100.0
            
            # Clamp limits 0-100
            if ratio > 100: ratio = 100.0
            if ratio < 0: ratio = 0.0
            
            return ratio
            
        merged['Supply_Ratio'] = merged.apply(calculate_ratio, axis=1)
        
        # Sort so highest supply items are visible, or maybe most extreme
        merged = merged.sort_values(by='Total_Supply', ascending=False)
        
        return self._attach_tiers(merged)

    def check_regional_liquidity(self):
        """
        Aggregates liquidity by Zone/Region.
        """
        search_path = os.path.join(self.history_dir, "**", "*.parquet")
        files = glob.glob(search_path, recursive=True)
        files.sort()
        
        if len(files) < 2:
            return None
            
        old_file, new_file = files[-2], files[-1]
        
        try:
            df_old = pd.read_parquet(old_file)
            df_new = pd.read_parquet(new_file)
        except Exception as e:
             return None
             
        old_ids = set(df_old['ListingID'].dropna().unique())
        new_ids = set(df_new['ListingID'].dropna().unique())
        sold_ids = old_ids - new_ids
        
        if not sold_ids:
            return pd.DataFrame()
            
        sold_df = df_old[df_old['ListingID'].isin(sold_ids)].copy()
        
        # Extract Region from Zone if possible (e.g. "Kerys - Vale X" -> "Kerys")
        # Assuming Zone format is "Region - Area" or just "Region"
        if 'Zone' not in sold_df.columns:
            return pd.DataFrame()

        # Group by Zone
        if 'Amount' in sold_df.columns:
             stats = sold_df.groupby('Zone').agg(
                Units_Sold=('Amount', 'sum'),
                Volume_Sold=('Price', 'sum'),
                Transaction_Count=('ListingID', 'count')
             ).reset_index()
        else:
             stats = sold_df.groupby('Zone').agg(
                Units_Sold=('ListingID', 'count'),
                Volume_Sold=('Price', 'sum'),
                 Transaction_Count=('ListingID', 'count')
             ).reset_index()
             
        return stats.sort_values('Volume_Sold', ascending=False)

    def analyze_stack_loss(self, item_name, min_stack_size, days=7):
        """
        Analyzes how many deals are lost if filtering by min_stack_size.
        """
        full_df = self.load_all_history()
        if full_df.empty:
            return None

        # Ensure Timestamp
        if not pd.api.types.is_datetime64_any_dtype(full_df['SnapshotDate']):
            full_df['SnapshotDate'] = pd.to_datetime(full_df['SnapshotDate'])

        # Filter Recent & Item
        cutoff = full_df['SnapshotDate'].max() - timedelta(days=days)
        
        mask = (full_df['Item'].astype(str).str.contains(item_name, case=False, na=False)) & \
               (full_df['SnapshotDate'] >= cutoff)
               
        df = full_df[mask].copy()
        
        if df.empty:
            return None # No data found

        # Calculate Median Price for "Deal" definition
        median_price = df['Price'].median()
        
        # All Deals (Anything strictly below median)
        all_deals = df[df['Price'] < median_price]
        total_deals = len(all_deals)
        
        if total_deals == 0:
            return {
                'Item': item_name,
                'Total_Deals': 0,
                'Valid_Deals': 0,
                'Lost_Pct': 0,
                'Median_Price': median_price
            }

        # Valid Deals (Meet stack requirement)
        valid_deals = all_deals[all_deals['Amount'] >= min_stack_size]
        valid_count = len(valid_deals)
        
        lost_count = total_deals - valid_count
        lost_pct = (lost_count / total_deals) * 100
        
        return {
            'Item': item_name,
            'Total_Deals': total_deals,
            'Valid_Deals': valid_count,
            'Lost_Deals': lost_count,
            'Lost_Pct': lost_pct,
            'Median_Price': median_price,
            'Analysis_Days': days
        }
    def scan_shopping_list(self, items, buy_zone_filter=None, sell_zone_filter=None):
        """
        Scans for items from a shopping list.
        Rules:
        1. Discount >= 50% vs 7-day Global Median.
        2. Opportunity if:
           - Total stacks of items meeting rule 1 in the same zone >= 20.
           - OR Item is a 'Token of the Whisper' (any level) -> 1 stack is enough.
        """
        if not os.path.exists(self.listings_file):
            return pd.DataFrame()

        df_current = pd.read_parquet(self.listings_file)
        df_current['Item_Lower'] = df_current['Item'].str.lower()
        items_lower = [i.lower() for i in items]
        
        # 1. Get 7-day Median for all items in list
        print("Calculating 7-day medians from history...")
        cutoff_7d = datetime.now() - timedelta(days=7)
        try:
            df_hist = self.load_all_history(
                columns=['Item', 'Price', 'Amount', 'SnapshotDate'],
                filters=[('SnapshotDate', '>=', cutoff_7d), ('Item', 'in', items)]
            )
        except:
             df_hist = self.load_all_history(columns=['Item', 'Price', 'Amount', 'SnapshotDate'])
             df_hist = df_hist[df_hist['SnapshotDate'] >= cutoff_7d]
             df_hist = df_hist[df_hist['Item'].isin(items)]

        if df_hist.empty:
            print("Warning: No historical data found for these items. Using current global median.")
            sub_df = df_current[df_current['Item_Lower'].isin(items_lower)].copy()
            if 'UnitPrice' not in sub_df.columns:
                 sub_df['UnitPrice'] = sub_df['Price'] / sub_df['Amount']
            ref_prices = sub_df.groupby('Item_Lower')['UnitPrice'].median().to_dict()
        else:
            if 'UnitPrice' not in df_hist.columns:
                 df_hist['UnitPrice'] = df_hist['Price'] / df_hist['Amount']
            ref_prices = df_hist.groupby('Item')['UnitPrice'].median().to_dict()
            # Map back to lower for easy lookup
            ref_prices = {k.lower(): v for k, v in ref_prices.items()}

        # 2. Identify potential deals (Price < 0.5 * Ref)
        if 'UnitPrice' not in df_current.columns:
             df_current['UnitPrice'] = df_current['Price'] / df_current['Amount']
             
        # Filter by zone if provided
        if buy_zone_filter:
            df_cand = df_current[df_current['Zone'].str.contains(buy_zone_filter, case=False, na=False)].copy()
        else:
            df_cand = df_current.copy()
            
        df_cand = df_cand[df_cand['Item_Lower'].isin(items_lower)]
        
        deals = []
        for _, row in df_cand.iterrows():
            item_lower = row['Item_Lower']
            ref_p = ref_prices.get(item_lower)
            if not ref_p: continue
            
            unit_p = row['UnitPrice']
            discount = (ref_p - unit_p) / ref_p
            
            if discount >= 0.5:
                deals.append({
                    'Item': row['Item'],
                    'Item_Lower': item_lower,
                    'Zone': row['Zone'],
                    'Buy_Price': unit_p,
                    'Ref_Price': ref_p,
                    'Margin_%': discount * 100,
                    'Stock': row['Amount'],
                    'ListingID': row['ListingID']
                })
        
        if not deals:
            return pd.DataFrame()
            
        df_deals = pd.DataFrame(deals)
        
        # 3. Apply Volume Rules
        # Group by Zone (Valley)
        final_deals = []
        zones = df_deals['Zone'].unique()
        
        for zone in zones:
            zone_df = df_deals[df_deals['Zone'] == zone]
            total_stacks = len(zone_df) # Each row in selene is usually a listing (stack)
            # Actually, calculate total amount/stacks? 
            # The user said "20 stacks". In Pax Dei, one listing is one stack or multiple?
            # Usually one listing is one stack.
            
            is_token_in_zone = any('token of the whisper' in i for i in zone_df['Item_Lower'])
            
            if total_stacks >= 20 or is_token_in_zone:
                # If it's a token case but < 20 stacks, only include the tokens?
                # The user said "os 20 stacks podem ser de mais de um dos itens... desde que no mesmo vale"
                # And "tokens... podem ser uma oportunidade, mesmo caso seja apenas um stack"
                # This implies if there is a token, it's an opportunity. 
                # Does it make the OTHER items in the same valley opportunities too if they meet the 50% discount?
                # "os 20 stacks podem ser de mais de um dos itens... desde que estejam sendo vendidos no mesmo vale."
                # I'll include all discounted items in the zone if the zone meets the criteria.
                if total_stacks >= 20:
                    final_deals.extend(zone_df.to_dict('records'))
                else:
                    # Only tokens
                    token_deals = zone_df[zone_df['Item_Lower'].str.contains('token of the whisper')]
                    final_deals.extend(token_deals.to_dict('records'))
                    
        return pd.DataFrame(final_deals)
