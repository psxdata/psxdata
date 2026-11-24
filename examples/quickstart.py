"""psxdata quickstart -- run this script to see psxdata in action.

Requires: pip install psxdata
"""
import psxdata

print("=" * 50)
print("psxdata quickstart")
print("=" * 50)

# 1. Historical prices
print("\n1. ENGRO historical prices (last 5 rows)")
df = psxdata.stocks("ENGRO", start="2025-01-01", end="2025-12-31")
print(df.tail())

# 2. Live quote
print("\n2. ENGRO live quote")
q = psxdata.quote("ENGRO")
print(q.T)

# 3. KSE-100 tickers
print("\n3. KSE-100 tickers (first 10)")
kse100 = psxdata.tickers(index="KSE100")
print(f"Total: {len(kse100)} stocks")
print(kse100[:10])

# 4. Sector summary
print("\n4. Top 5 sectors by market cap")
sectors = psxdata.sectors()
print(sectors.sort_values("market_cap_b", ascending=False)[["sector_name", "market_cap_b"]].head())

# 5. Index constituents
print("\n5. KSE-100 top 5 by index weight")
idx = psxdata.indices("KSE100")
print(idx.nlargest(5, "idx_weight")[["symbol", "idx_weight"]])

print("\nDone. See https://docs.psxdata.org for full documentation.")
