import sys
import os
import pandas as pd
import traceback

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(base_dir, "src"))

from modules.market import MarketAnalyzer
from modules.crafting import CraftingAnalyzer
from modules.logistics import ArbitrageFinder

data_dir = os.path.join(base_dir, "data")

def test_all():
    print("Testing MarketAnalyzer...")
    ma = MarketAnalyzer(data_dir)
    
    try:
        print("1. check_liquidity")
        df1 = ma.check_liquidity()
        print("Success, shape:", df1.shape if df1 is not None else None)
    except Exception as e:
        print("Error in check_liquidity:")
        traceback.print_exc()

    try:
        print("2. check_demand_intensity")
        df2 = ma.check_demand_intensity()
        print("Success, shape:", df2.shape if df2 is not None else None)
    except Exception as e:
        print("Error in check_demand_intensity:")
        traceback.print_exc()
        
    try:
        print("3. check_regional_liquidity")
        df3 = ma.check_regional_liquidity()
        print("Success, shape:", df3.shape if df3 is not None else None)
    except Exception as e:
        print("Error in check_regional_liquidity:")
        traceback.print_exc()

    try:
        print("4. get_locations")
        locs = ma.get_locations()
        print("Success, keys:", len(locs.keys()) if locs else None)
    except Exception as e:
        print("Error in get_locations:")
        traceback.print_exc()
        
    try:
        print("5. get_supply_demand")
        df5 = ma.get_supply_demand()
        print("Success, shape:", df5.shape if df5 is not None else None)
    except Exception as e:
        print("Error in get_supply_demand:")
        traceback.print_exc()

    print("\nTesting CraftingAnalyzer...")
    ca = CraftingAnalyzer(data_dir)
    try:
        df6 = ca.analyze_profitability()
        print("Success, shape:", df6.shape if df6 is not None else None)
    except Exception as e:
        print("Error in analyze_profitability:")
        traceback.print_exc()

    print("\nTesting ArbitrageFinder...")
    af = ArbitrageFinder(data_dir)
    try:
        df7 = af.find_opportunities()
        print("Success, shape:", df7.shape if df7 is not None else None)
    except Exception as e:
        print("Error in find_opportunities:")
        traceback.print_exc()

if __name__ == "__main__":
    test_all()
