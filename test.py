# Sprawdź strukturę danych
from utils.data_utils import load_links, get_latest_prices

# 1. Sprawdź linki
links = load_links()
print("Pierwsze 3 linki:")
for i, link in enumerate(links[:3]):
    print(f"Link {i}: {type(link)} = {link}")

print("\n" + "="*50 + "\n")

# 2. Sprawdź ceny
latest_prices = get_latest_prices()
print("Pierwsze 3 ceny:")
for i, (key, price_data) in enumerate(list(latest_prices.items())[:3]):
    print(f"Price {i}: key={key}, type={type(price_data)}, data={price_data}")
    if hasattr(price_data, 'created'):
        print(f"  Ma atrybut 'created': {price_data.created}")
    if isinstance(price_data, dict):
        print(f"  Klucze w słowniku: {list(price_data.keys())}")

print("\n" + "="*50 + "\n")

# 3. Sprawdź czy gdzieś nie ma odwołania do .created zamiast ['created']
import traceback
try:
    from routes.product_management import ProductManager
    pm = ProductManager()
    pm.product_detail(6)  # użyj ID produktu z twojego pliku
except Exception as e:
    print("PEŁNY TRACEBACK:")
    traceback.print_exc()