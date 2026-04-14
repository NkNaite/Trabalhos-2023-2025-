
# === AI AGENT SAFETY DIRECTIVE (DO NOT IGNORE) ===
# 1. NO INFINITE LOOPS: Ensure all loops have break conditions or maximum iterations.
# 2. DATA RESOURCE ECONOMY: Avoid reading large files (e.g., >100MB) directly in the API loop.
#    Use pre-aggregated summaries or indexed data.
# 3. NO SYSTEM OVERLOAD: If a task takes more than 5s, implement a background worker or abort.
# 4. MONITORING: Always log start/end/error for heavy operations.

import argparse
import sys
import os
import pandas as pd

# Add src to path just in case
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.market import MarketAnalyzer
from modules.crafting import CraftingAnalyzer
from modules.logistics import PaxLogistics, ArbitrageFinder, RouteScanner
from modules.sales_tracker import SalesTracker

def get_data_dir():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data")

def handle_market(args):
    data_dir = get_data_dir()
    analyzer = MarketAnalyzer(data_dir)
    
    if args.liquidity:
        print("Running Liquidity Analysis...")
        df = analyzer.check_liquidity()
        if df is not None and not df.empty:
            print("\n--- TOP LIQUIDITY ITEMS (Recent Sales) ---")
            print(df.head(10)[['Item', 'Units_Sold', 'Total_Volume', 'Top_Zone']].to_string(index=False))
            # Save report
            out_file = os.path.join(data_dir, "liquidez_diaria.csv")
            df.to_csv(out_file, index=False)
            print(f"\nReport saved to {out_file}")
        else:
            print("No liquidity data found.")
            
    if args.sellers:
        print(f"Analyzing Producers for: {args.sellers}")
        stats = analyzer.get_top_sellers(args.sellers)
        if stats is not None:
            print(f"\n--- TOP PRODUCERS (SELLERS) FOR {args.sellers} ---")
            print(stats.head(10).to_string())
        else:
            print(f"No seller data found for {args.sellers}")

    if args.analyze_stacks:
        print(f"Analyzing Stack Loss for: {args.analyze_stacks} (Min: {args.min_stack})")
        stats = analyzer.analyze_stack_loss(args.analyze_stacks, args.min_stack)
        if stats:
             print("\n--- STACK SIZE IMPACT ANALYSIS ---")
             print(f"Item: {stats['Item']}")
             print(f"Days Analyzed: {stats['Analysis_Days']}")
             print(f"Total Deals (< Median): {stats['Total_Deals']}")
             print(f"Valid Deals (>= {args.min_stack}): {stats['Valid_Deals']}")
             print(f"Lost Deals: {stats['Lost_Deals']} ({stats['Lost_Pct']:.1f}%)")
             
             if stats['Lost_Pct'] > 15:
                 print("\n[WARNING] High loss rate! Consider lowering minimum stack size.")
             else:
                 print("\n[OK] Safe filtering level.")
        else:
            print("No data found for stack analysis.")

def handle_crafting(args):
    data_dir = get_data_dir()
    analyzer = CraftingAnalyzer(data_dir)
    
    print("Analyzing Crafting Profitability...")
    df = analyzer.analyze_profitability()
    
    if df is not None and not df.empty:
        print("\n--- TOP PROFITABLE RECIPES ---")
        cols = ['Produto', 'Spread', 'Margem_Perc', 'Mercado_Venda']
        print(df.head(args.top)[cols].to_string(index=False))
        
        out_file = os.path.join(data_dir, "analise_disparidade.csv")
        df.to_csv(out_file, index=False)
        print(f"\nFull report saved to {out_file}")
    else:
        print("No profitable recipes found.")

def handle_recipe(args):
    data_dir = get_data_dir()
    analyzer = CraftingAnalyzer(data_dir)
    
    print(f"Analyzing Recipe: {args.item}")
    data = analyzer.recipe_breakdown(args.item, recursive=args.recursive)
    
    if not data:
        print("Item not found or no recipe data.")
        return
        
    print(f"\n--- RECIPE BREAKDOWN: {data['Item']} (Tier {data['Tier']}) ---")
    print(f"Complexity Score: {data['Complexity']}")
    
    print("\n[Raw Materials Needed]")
    if data['Raw_Materials']:
        # Sort by qty desc
        sorted_mats = sorted(data['Raw_Materials'].items(), key=lambda x: x[1], reverse=True)
        for mat, qty in sorted_mats:
            print(f"  - {mat}: {qty:.1f}")
    else:
        print("  None (Is this a raw material?)")
        
    if data['Intermediates']:
        print("\n[Intermediate Steps]")
        sorted_inter = sorted(data['Intermediates'].items(), key=lambda x: x[1], reverse=True)
        for item, qty in sorted_inter:
            print(f"  - {item}: {qty:.1f}")


def handle_logistics(args):
    data_dir = get_data_dir()
    
    if args.route:
        # Expected format: start,end (comma separated) or just two args? 
        # Argparse 'nargs' can capture multiple. let's use nargs=2
        start, end = args.route
        logistics = PaxLogistics()
        print(f"Calculating route: {start} -> {end}")
        res = logistics.compare_routes(start, end)
        if res:
            print(f"\n--- Route Report: {start} -> {end} ---")
            print(f"Safe Route Cost: {res['safe_route']['cost']}")
            print(f"Safe Path: {' -> '.join(res['safe_route']['path'])}")
            print(f"PvP Route Cost: {res['pvp_route']['cost']}")
            print(f"PvP Path: {' -> '.join(res['pvp_route']['path'])}")
        else:
            print("Could not resolve locations.")
            
    if args.arbitrage:
        finder = ArbitrageFinder(data_dir)
        print("Scanning for Arbitrage Opportunities...")
        df = finder.find_opportunities()
        if not df.empty:
            print("\n--- TOP ARBITRAGE DEALS ---")
            # De-duplicate items
            df_dedup = df.drop_duplicates(subset=['Item']).head(10)
            cols = ['Item', 'Buy_Price', 'Avg_Sale_Price', 'Unit_Profit', 'Margin', 'Buy_Zone', 'Sell_Zone']
            print(df_dedup[cols].to_string(index=False, float_format="%.1f"))
        else:
            print("No arbitrage opportunities found.")

    if args.scan:
        scanner = RouteScanner(data_dir)
        print("Scanning current market for Route Opportunities in Kerys...")
        # Zones for Kerys Region
        ZONES_OF_INTEREST = [
            'pladenn', 'retz', 'llydaw', 'dolavon', 
            'bronyr', 'aven', 'dreger', 
            'ewyas', 'vanes', 'tremen'
        ]
        
        df = scanner.scan_current_market(ZONES_OF_INTEREST)
        if not df.empty:
            print("\n--- CURRENT DISCOUNTS IN ROUTE ---")
            cols = ['Item', 'Price', 'Median_Price', 'Discount_%', 'Amount', 'Zone']
            print(df.head(20)[cols].to_string(index=False, float_format="%.2f"))
        else:
            print("No discounts found in route.")
            
        print("\n--- HISTORICAL PRODUCERS (Route Items) ---")
        client_items = scanner.get_client_items()
        stats = scanner.scan_history_producers(client_items)
        if not stats.empty:
            print(stats.head(15).to_string(index=False))
        else:
            print("No historical data for client items.")

def handle_sales(args):
    data_dir = get_data_dir()
    tracker = SalesTracker(data_dir)
    

    # 0. Identification
    if args.identify:
        # Args identify format is just Title? No, we need Item and Price
        # argparse nargs='+' can capture
        # But we defined identify separately in parser. Let's check parser.
        pass

    # 1. Check if ID exists (unless we are identifying)
    if not tracker.seller_id and not args.identify:
        print("Error: Seller ID not found. Run 'python src/advisor.py sales --identify \"Item\" PRICE' first.")
        return

    if args.identify:
        item_name = args.identify[0]
        try:
            price = float(args.identify[1])
        except IndexError:
            print("Error: Price required. Usage: --identify \"Item Name\" PRICE")
            return
        except ValueError:
            print("Error: Price must be a number.")
            return
            
        print(f"Identifying Seller for '{item_name}' at {price}g...")
        res = tracker.identify_seller(item_name, price)
        if "success" in res:
            print(f"Success! SellerHash Found and Saved: {res['seller_id']}")
        else:
            print(f"Identification Failed: {res.get('error')}")
            if "candidates" in res:
                print(f"Candidates: {res['candidates']}")
        return

    print(f"Tracking Sales for Seller: {tracker.seller_id}...")
    summary = tracker.track_sales(args.item)
    
    if "error" in summary:
        print(f"Error: {summary['error']}")
        return
        
    print("\n=== SALES & PROFIT REPORT ===")
    print(f"Total Revenue: {summary['total_revenue']:,.2f}g")
    print(f"Listing Fees: -{summary['total_fees']:,.2f}g")
    print(f"NET PROFIT: {summary['net_profit']:,.2f}g")
    print("-" * 40)
    
    if args.item:
        # Detailed view for single item
        if args.item in summary['items']:
            data = summary['items'][args.item]
            zone = data.get('zone', 'N/A')
            print(f"Item: {args.item}")
            print(f"  Sold (Since Last): {data['sold']}")
            print(f"  Revenue: {data['revenue']:,.2f}g")
            print(f"  Profit: {data['profit']:,.2f}g")
            print("-" * 20)
            print("  CURRENT LISTING STATUS:")
            print(f"  Stock Listed: {data['stock']}")
            print(f"  Zone: {zone}")
            print(f"  Unit Price: {data.get('unit_price', 0):.2f}g")
            print(f"  Lot Price: {data.get('lot_price', 0):.2f}g")
        else:
            print(f"No sales data found for item: {args.item}")
    else:
        # Overview of all items
        print(f"{'Item':<25} | {'Sold':<5} | {'Profit (Net)':>12} | {'Stock':>5} | {'Unit $':>7} | {'Lot $':>7} | {'Zone':<35}")
        print("-" * 110)
        for item, data in summary['items'].items():
            u_price = data.get('unit_price', 0)
            l_price = data.get('lot_price', 0)
            zone = data.get('zone', 'Multiple')
            # Truncate zone if too long
            if len(zone) > 35: zone = zone[:32] + ".."
            
            print(f"{item:<25} | {data['sold']:<5} | {data['profit']:>12.1f}g | {data['stock']:>5} | {u_price:>7.1f} | {l_price:>7.0f} | {zone:<35}")

def handle_shopping(args):
    data_dir = get_data_dir()
    analyzer = MarketAnalyzer(data_dir)
    
    # 1. Parse List File
    list_file = args.list
    # Try resolving relative to root or data
    if not os.path.exists(list_file):
        # Try relative to d:\PaxDei_Tool
        root_dir = os.path.dirname(data_dir)
        list_file = os.path.join(root_dir, args.list)
        
    if not os.path.exists(list_file):
         print(f"Error: Shopping list file not found: {args.list}")
         return
         
    items = []
    print(f"Loading shopping list from: {list_file}")
    with open(list_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Simple markdown list parser
            if line.startswith("- ") or line.startswith("* "):
                # Extract item name
                # Remove bullet
                item = line[2:].strip()
                # Remove bold marks if any (**Item**)
                item = item.replace("**", "").replace("*", "")
                # Remove trailing comments or quantities (e.g. "Item (Info)")
                # Just keep it simple for now, maybe split by '('
                if "(" in item:
                    item = item.split("(")[0].strip()
                if item:
                    items.append(item)
                    
    print(f"Found {len(items)} items in list.")
    
    # 2. Scan Market
    print(f"Scanning market in {args.zone} for deals...")
    if args.target:
        print(f"Comparing against prices in {args.target}...")
    else:
        print("Comparing against Global Median...")
        
    df = analyzer.scan_shopping_list(items, args.zone, args.target)
    
    if df.empty:
        print("No deals found matching your criteria.")
        return
        
    print("\n=== SHOPPING OPPORTUNITIES ===")
    print(f"{'Item':<25} | {'Price':<8} | {'Ref Price':<9} | {'Margin %':<8} | {'Stock':<5} | {'Zone':<15} | {'Check'}")
    print("-" * 100)
    
    # Group by Item to show best deal per item? Or all listings?
    # Let's show all valid deals but maybe limit if too many.
    # Group by Item and pick best price
    best_deals = df.sort_values('Buy_Price').groupby(['Item', 'Zone']).first().reset_index().sort_values('Margin_%', ascending=False)
    
    for _, row in best_deals.iterrows():
        check_mark = "[OK]" if row['Margin_%'] > 30 else "[?]"
        print(f"{row['Item']:<25} | {row['Buy_Price']:<8.2f} | {row['Ref_Price']:<9.2f} | {row['Margin_%']:<8.1f} | {row['Stock']:<5} | {row['Zone']:<15} | {check_mark}")
        
    print("\n(Ref Price = Target Zone Median or Global Median)")


def main():
    parser = argparse.ArgumentParser(description="Pax Dei Advisor - Unified Intelligence Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    
    # Market
    market_parser = subparsers.add_parser("market", help="Market Intelligence")
    market_parser.add_argument("--history", "-i", type=str, help="Get price history for an item")
    market_parser.add_argument("--liquidity", "-l", action="store_true", help="Check liquidity (churn)")
    market_parser.add_argument("--sellers", "-s", type=str, help="Analyze unique producers/sellers for an item")
    market_parser.add_argument("--analyze-stacks", type=str, help="Analyze deal loss by stack size for an item")
    market_parser.add_argument("--min-stack", type=int, default=1, help="Minimum stack size for analysis (default: 1)")
    
    # Crafting
    crafting_parser = subparsers.add_parser("crafting", help="Crafting Analysis")
    crafting_parser.add_argument("--top", "-n", type=int, default=5, help="Number of top recipes to show")

    # Recipe (New)
    recipe_parser = subparsers.add_parser("recipe", help="Deep Recipe Analysis")
    recipe_parser.add_argument("item", type=str, help="Item name to analyze")
    recipe_parser.add_argument("--recursive", "-r", action="store_true", help="Recursively break down ingredients")
    
    # Logistics
    logistics_parser = subparsers.add_parser("logistics", help="Logistics & Arbitrage")
    logistics_parser.add_argument("--route", nargs=2, metavar=('START', 'END'), help="Calculate route between two locations")
    logistics_parser.add_argument("--arbitrage", "-a", action="store_true", help="Find buy/sell arbitrage opportunities")
    logistics_parser.add_argument("--scan", "-s", action="store_true", help="Scan trade route for discounts and historical producers")

    # Sales (New)
    sales_parser = subparsers.add_parser("sales", help="Sales & Profit Tracking")
    sales_parser.add_argument("--item", "-i", type=str, help="Filter by specific item name")
    sales_parser.add_argument("--identify", nargs=2, metavar=('ITEM', 'PRICE'), help="Identify your seller ID using a unique item price")
    
    # Shopping (New)
    shopping_parser = subparsers.add_parser("shopping", help="Shopping List Scanner")
    shopping_parser.add_argument("--list", "-l", type=str, required=True, help="Path to markdown list file")
    shopping_parser.add_argument("--zone", "-z", type=str, default="Langres", help="Zone to buy in (default: Langres)")
    shopping_parser.add_argument("--target", "-t", type=str, help="Target zone to sell in (optional)")

    args = parser.parse_args()
    
    if args.command == "market":
        handle_market(args)
    elif args.command == "crafting":
        handle_crafting(args)
    elif args.command == "recipe":
        handle_recipe(args)
    elif args.command == "logistics":
        handle_logistics(args)
    elif args.command == "sales":
        handle_sales(args)
    elif args.command == "shopping":
        handle_shopping(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
