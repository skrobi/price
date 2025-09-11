"""
Utilities do obsługi danych - ładowanie, zapisywanie, konwersje z obsługą zamienników
"""
import json
import os
import hashlib
from datetime import datetime

def load_products():
    """Ładuje produkty z pliku"""
    try:
        with open('data/products.txt', 'r', encoding='utf-8') as f:
            products = []
            for line in f:
                if line.strip():
                    product = json.loads(line)
                    # Migracja starych produktów - dodaj nowe pola jeśli nie istnieją
                    if 'substitute_group' not in product:
                        product['substitute_group'] = None
                    if 'substitute_settings' not in product:
                        product['substitute_settings'] = {
                            'allow_substitutes': True,
                            'max_price_increase_percent': 20.0,
                            'max_quantity_multiplier': 1.5
                        }
                    products.append(product)
            return products
    except FileNotFoundError:
        return []

def save_product(product_data):
    """Zapisuje produkt do pliku"""
    # Upewnij się że nowy produkt ma wszystkie wymagane pola
    if 'substitute_group' not in product_data:
        product_data['substitute_group'] = None
    if 'substitute_settings' not in product_data:
        product_data['substitute_settings'] = {
            'allow_substitutes': True,
            'max_price_increase_percent': 20.0,
            'max_quantity_multiplier': 1.5
        }
    
    with open('data/products.txt', 'a', encoding='utf-8') as f:
        f.write(json.dumps(product_data, ensure_ascii=False) + '\n')

def update_product(product_data):
    """Aktualizuje istniejący produkt"""
    products = load_products()
    print(f"DEBUG: update_product called with: {product_data}")
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"DATA_UTILS UPDATE_PRODUCT: {product_data}")
    
    for i, product in enumerate(products):
        if product['id'] == product_data['id']:
            products[i] = product_data
            break
    
    # Przepisz cały plik
    with open('data/products.txt', 'w', encoding='utf-8') as f:
        for product in products:
            f.write(json.dumps(product, ensure_ascii=False) + '\n')

def load_links():
    """Ładuje linki produktów"""
    try:
        with open('data/product_links.txt', 'r', encoding='utf-8') as f:
            links = []
            for line in f:
                if line.strip():
                    links.append(json.loads(line))
            return links
    except FileNotFoundError:
        return []

def save_link(link_data):
    """Zapisuje link produktu"""
    with open('data/product_links.txt', 'a', encoding='utf-8') as f:
        f.write(json.dumps(link_data, ensure_ascii=False) + '\n')

def load_prices():
    """Ładuje ceny z pliku"""
    try:
        with open('data/prices.txt', 'r', encoding='utf-8') as f:
            prices = []
            for line in f:
                if line.strip():
                    prices.append(json.loads(line))
            return prices
    except FileNotFoundError:
        return []

def save_price(price_data):
    """Zapisuje cenę do pliku"""
    with open('data/prices.txt', 'a', encoding='utf-8') as f:
        f.write(json.dumps(price_data, ensure_ascii=False) + '\n')

def get_latest_prices(include_url_in_key=False):
    """
    Zwraca najnowsze ceny dla każdego produktu w każdym sklepie
    
    Args:
        include_url_in_key: Jeśli True, klucz będzie zawierać URL (product_id-shop_id-url_hash)
                           Jeśli False, tradycyjny klucz (product_id-shop_id)
    
    Returns:
        dict: {key: price_data}
    """
    all_prices = load_prices()
    latest_prices = {}
    
    for price in all_prices:
        if include_url_in_key:
            # Nowy format klucza z URL
            url_hash = hashlib.md5(price.get('url', '').encode()).hexdigest()[:8]
            key = f"{price['product_id']}-{price['shop_id']}-{url_hash}"
        else:
            # Tradycyjny format klucza
            key = f"{price['product_id']}-{price['shop_id']}"
        
        if key not in latest_prices or price['created'] > latest_prices[key]['created']:
            latest_prices[key] = price
    
    return latest_prices

def get_latest_prices_by_url():
    """
    Zwraca najnowsze ceny rozróżnione po konkretnym URL
    
    Returns:
        dict: {product_id|url: price_data}
    """
    all_prices = load_prices()
    latest_prices = {}
    
    for price in all_prices:
        # Klucz: product_id + URL (oddzielone "|")
        key = f"{price['product_id']}|{price.get('url', '')}"
        
        if key not in latest_prices or price['created'] > latest_prices[key]['created']:
            latest_prices[key] = price
    
    return latest_prices

def convert_to_pln(price_value, currency='PLN'):
    """Konwertuje cenę na PLN - POPRAWIONA WERSJA"""
    try:
        # Bezpieczna konwersja na float
        if isinstance(price_value, str):
            # Usuń spacje i zamień przecinek na kropkę
            price_clean = price_value.strip().replace(',', '.')
            price_float = float(price_clean)
        elif isinstance(price_value, (int, float)):
            price_float = float(price_value)
        else:
            print(f"BŁĄD: Nieznany typ ceny: {type(price_value)} = {price_value}")
            return 0.0
        
        # Sprawdź czy cena jest sensowna
        if price_float <= 0:
            print(f"BŁĄD: Nieprawidłowa cena: {price_float}")
            return 0.0
        
        # Kursy walut
        exchange_rates = {
            'PLN': 1.0,
            'EUR': 4.30,
            'USD': 4.00,
            'GBP': 5.00
        }
        
        rate = exchange_rates.get(currency, 1.0)
        result = price_float * rate
        
        return result
        
    except (ValueError, TypeError) as e:
        print(f"BŁĄD konwersji ceny: {e}, wartość: '{price_value}', typ: {type(price_value)}")
        return 0.0

def get_product_price_range(product_id, latest_prices):
    """Zwraca zakres cen dla produktu (min-max)"""
    product_prices = []
    
    for key, price_data in latest_prices.items():
        if price_data['product_id'] == product_id and price_data['price']:
            price_pln = convert_to_pln(price_data['price'], price_data.get('currency', 'PLN'))
            product_prices.append(price_pln)
    
    if not product_prices:
        return None, None
    
    return min(product_prices), max(product_prices)

def get_product_price_range_with_substitutes(product_id, latest_prices):
    """
    Zwraca zakres cen dla produktu włączając zamienniki
    
    Returns:
        dict: {
            'original': {'min': float, 'max': float},
            'substitutes': {'min': float, 'max': float},
            'combined': {'min': float, 'max': float}
        }
    """
    try:
        from substitute_manager import substitute_manager
        
        # Ceny oryginału
        original_min, original_max = get_product_price_range(product_id, latest_prices)
        
        # Ceny zamienników
        substitute_info = substitute_manager.get_substitutes_for_product(product_id)
        substitute_prices = []
        
        for substitute in substitute_info['substitutes']:
            sub_min, sub_max = get_product_price_range(substitute['id'], latest_prices)
            if sub_min and sub_max:
                substitute_prices.extend([sub_min, sub_max])
        
        substitute_min = min(substitute_prices) if substitute_prices else None
        substitute_max = max(substitute_prices) if substitute_prices else None
        
        # Łączone ceny (oryginał + zamienniki)
        all_prices = []
        if original_min and original_max:
            all_prices.extend([original_min, original_max])
        if substitute_prices:
            all_prices.extend(substitute_prices)
        
        combined_min = min(all_prices) if all_prices else None
        combined_max = max(all_prices) if all_prices else None
        
        return {
            'original': {'min': original_min, 'max': original_max},
            'substitutes': {'min': substitute_min, 'max': substitute_max},
            'combined': {'min': combined_min, 'max': combined_max}
        }
        
    except ImportError:
        # Fallback jeśli substitute_manager nie jest dostępny
        original_min, original_max = get_product_price_range(product_id, latest_prices)
        return {
            'original': {'min': original_min, 'max': original_max},
            'substitutes': {'min': None, 'max': None},
            'combined': {'min': original_min, 'max': original_max}
        }

def get_products_with_substitute_info():
    """Zwraca produkty z informacjami o zamiennikach"""
    products = load_products()
    latest_prices = get_latest_prices()
    
    try:
        from substitute_manager import substitute_manager
        
        for product in products:
            # Dodaj informacje o cenach z zamiennikmi
            price_info = get_product_price_range_with_substitutes(product['id'], latest_prices)
            product['price_range'] = price_info
            
            # Dodaj informacje o grupie zamienników
            substitute_info = substitute_manager.get_substitutes_for_product(product['id'])
            product['substitute_count'] = len(substitute_info['substitutes'])
            product['has_substitutes'] = product['substitute_count'] > 0
            
            # Zachowaj kompatybilność wsteczną
            if price_info['original']['min'] and price_info['original']['max']:
                product['min_price'] = price_info['original']['min']
                product['max_price'] = price_info['original']['max']
            else:
                product['min_price'] = None
                product['max_price'] = None
                
    except ImportError:
        # Fallback bez obsługi zamienników
        for product in products:
            min_price, max_price = get_product_price_range(product['id'], latest_prices)
            product['min_price'] = min_price
            product['max_price'] = max_price
            product['substitute_count'] = 0
            product['has_substitutes'] = False
    
    return products

def find_products_by_name_similarity(search_term, threshold=0.6):
    """
    Znajduje produkty o podobnych nazwach (przydatne do tworzenia grup zamienników)
    
    Args:
        search_term: szukana fraza
        threshold: próg podobieństwa (0-1)
        
    Returns:
        list: produkty posortowane według podobieństwa
    """
    import re
    from difflib import SequenceMatcher
    
    products = load_products()
    results = []
    
    search_term_clean = re.sub(r'[^\w\s]', '', search_term.lower().strip())
    
    for product in products:
        product_name_clean = re.sub(r'[^\w\s]', '', product['name'].lower())
        
        # Oblicz podobieństwo
        similarity = SequenceMatcher(None, search_term_clean, product_name_clean).ratio()
        
        if similarity >= threshold:
            results.append({
                'product': product,
                'similarity': similarity,
                'match_reason': 'name_similarity'
            })
    
    # Sortuj według podobieństwa (malejąco)
    results.sort(key=lambda x: x['similarity'], reverse=True)
    
    return results

def migrate_old_basket_data():
    """Migruje stare koszyki do nowego formatu z obsługą zamienników"""
    try:
        from basket_manager import basket_manager
        
        baskets = basket_manager.load_baskets()
        modified = False
        
        for basket_id, basket in baskets.items():
            # Dodaj nowe ustawienia zamienników jeśli nie istnieją
            if 'substitute_settings' not in basket.get('optimization_settings', {}):
                if 'optimization_settings' not in basket:
                    basket['optimization_settings'] = {}
                
                basket['optimization_settings']['substitute_settings'] = {
                    'allow_substitutes': True,
                    'max_price_increase_percent': 20.0,
                    'prefer_original': True,
                    'max_substitutes_per_product': 3
                }
                
                basket['updated'] = datetime.now().isoformat()
                modified = True
            
            # Migruj pozycje koszyka
            if 'basket_items' in basket:
                for item_key, item in basket['basket_items'].items():
                    if 'substitute_settings' not in item:
                        item['substitute_settings'] = {
                            'allow_substitutes': True,
                            'max_price_increase_percent': 20.0
                        }
                        modified = True
        
        if modified:
            # Zapisz zmigrowane koszyki
            for basket_id, basket in baskets.items():
                basket_manager.save_basket(basket)
            
        return True
        
    except Exception as e:
        print(f"Błąd podczas migracji koszyków: {e}")
        return False

def cleanup_orphaned_data():
    """Czyści osierocone dane (ceny bez produktów, linki bez produktów itp.)"""
    products = load_products()
    product_ids = set(p['id'] for p in products)
    
    # Wyczyść ceny
    prices = load_prices()
    valid_prices = [p for p in prices if p['product_id'] in product_ids]
    
    if len(valid_prices) != len(prices):
        with open('data/prices.txt', 'w', encoding='utf-8') as f:
            for price in valid_prices:
                f.write(json.dumps(price, ensure_ascii=False) + '\n')
        print(f"Usunięto {len(prices) - len(valid_prices)} osieroconych cen")
    
    # Wyczyść linki
    links = load_links()
    valid_links = [l for l in links if l['product_id'] in product_ids]
    
    if len(valid_links) != len(links):
        with open('data/product_links.txt', 'w', encoding='utf-8') as f:
            for link in valid_links:
                f.write(json.dumps(link, ensure_ascii=False) + '\n')
        print(f"Usunięto {len(links) - len(valid_links)} osieroconych linków")
    
    # Wyczyść grupy zamienników
    try:
        from substitute_manager import substitute_manager
        
        groups = substitute_manager.load_substitute_groups()
        valid_groups = {}
        
        for group_id, group in groups.items():
            # Sprawdź czy produkty w grupie nadal istnieją
            valid_product_ids = [pid for pid in group['product_ids'] if pid in product_ids]
            
            if len(valid_product_ids) >= 2:  # Grupa musi mieć co najmniej 2 produkty
                group['product_ids'] = valid_product_ids
                # Usuń nieistniejące produkty z priority_map
                group['priority_map'] = {
                    pid: priority for pid, priority in group['priority_map'].items() 
                    if pid in valid_product_ids
                }
                valid_groups[group_id] = group
        
        if len(valid_groups) != len(groups):
            with open('data/substitutes.txt', 'w', encoding='utf-8') as f:
                for group in valid_groups.values():
                    f.write(json.dumps(group, ensure_ascii=False) + '\n')
            print(f"Usunięto {len(groups) - len(valid_groups)} nieprawidłowych grup zamienników")
            
    except ImportError:
        pass  # substitute_manager nie dostępny
    
    return True