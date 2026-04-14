import sys
import os
import traceback
import datetime

sys.path.append(os.path.abspath('src'))
from modules.market import MarketAnalyzer

data_dir = os.path.abspath('data')
analyzer = MarketAnalyzer(data_dir)

safe_cutoff = datetime.datetime.now() - datetime.timedelta(days=3)
print(f"Testing direct parquet load with generic filter for dates >= {safe_cutoff}...")

try:
    df = analyzer.load_all_history(columns=['SnapshotDate'], filters=[('SnapshotDate', '>=', safe_cutoff)])
    print(f"Loaded {len(df)} rows.")
except Exception as e:
    print("Direct parquet filter failed:")
    traceback.print_exc()

print("\nTesting full supply/demand execution...")
try:
    res = analyzer.get_supply_demand(days=1)
    if res is not None:
        print(f"Success, returned {len(res)} rows.")
    else:
        print("Returned None")
except Exception as e:
    print("Failed with error:")
    traceback.print_exc()
