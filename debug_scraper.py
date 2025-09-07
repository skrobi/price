"""
Skrypt do debugowania problemu z importem price_scraper
"""
import sys
import traceback

print("🔍 DEBUGOWANIE PRICE_SCRAPER")
print("=" * 50)

try:
    print("1. Próba importu price_scraper...")
    import price_scraper
    print("   ✅ Import udany!")
    
    print("2. Sprawdzam czy scraper istnieje...")
    if hasattr(price_scraper, 'scraper'):
        print("   ✅ Obiekt scraper znaleziony!")
        print(f"   Typ: {type(price_scraper.scraper)}")
    else:
        print("   ❌ Brak obiektu scraper!")
    
    print("3. Próba wywołania metody scrape_page...")
    if hasattr(price_scraper, 'scraper') and price_scraper.scraper:
        result = price_scraper.scraper.scrape_page("https://www.example.com")
        print("   ✅ Metoda działa!")
    else:
        print("   ❌ Nie można wywołać metody!")
        
except ImportError as e:
    print(f"❌ BŁĄD IMPORTU: {e}")
    print("\nPełny traceback:")
    traceback.print_exc()
    
except Exception as e:
    print(f"❌ INNY BŁĄD: {e}")
    print("\nPełny traceback:")
    traceback.print_exc()

print("\n" + "=" * 50)
print("🔍 SPRAWDZAM STRUKTURA PLIKÓW:")

import os
current_files = [f for f in os.listdir('.') if f.endswith('.py')]
print("Pliki .py w katalogu głównym:")
for file in sorted(current_files):
    print(f"   📄 {file}")

if os.path.exists('data'):
    print("\n📁 Folder data istnieje")
else:
    print("\n❌ Folder data nie istnieje")