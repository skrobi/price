"""
Routes związane z produktami - główny plik
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from utils.data_utils import load_products, save_product, load_links, load_prices, get_latest_prices

# Import modułów pomocniczych
from .product_management import ProductManager
from .product_links import ProductLinksManager
from .product_pricing import ProductPricingManager
import json
import logging
logger = logging.getLogger(__name__)

product_bp = Blueprint('products', __name__)

# Inicjalizacja managerów
product_manager = ProductManager()
links_manager = ProductLinksManager()
pricing_manager = ProductPricingManager()

@product_bp.route('/products')
def products():
    """Lista wszystkich produktów"""
    return product_manager.list_products()

@product_bp.route('/add_product', methods=['GET', 'POST'])
def add_product():
    """Dodaj nowy produkt ręcznie"""
    return product_manager.add_product()

@product_bp.route('/add_product_url', methods=['GET', 'POST'])
def add_product_url():
    """Dodaj produkt z URL"""
    return product_manager.add_product_url()

@product_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    """Szczegóły produktu"""
    return product_manager.product_detail(product_id)

@product_bp.route('/product/<int:product_id>/add_link', methods=['GET', 'POST'])
def add_link_to_product(product_id):
    """Dodaje link do istniejącego produktu"""
    return links_manager.add_link_to_product(product_id)

# =============================================================================
# API Endpoints - Product Management
# =============================================================================

@product_bp.route('/update_product', methods=['POST'])
def update_product():
    """API - aktualizuje dane produktu - ROZSZERZONE"""
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'Brak product_id'})
        
        # NOWE: Użyj sync wrapper
        from sync.sync_integration import _sync_wrapper
        if _sync_wrapper:
            data['id'] = product_id  # Dodaj ID do danych
            result = _sync_wrapper.update_product(product_id, data)
            return jsonify(result)
        else:
            # Fallback do starego kodu
            return product_manager.update_product()
            
    except Exception as e:
        logger.error(f"Error in update_product: {e}")
        return jsonify({'success': False, 'error': str(e)})

@product_bp.route('/delete_product', methods=['POST'])
def delete_product():
    """API - usuwa produkt"""
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'Brak product_id'})
        
        # Użyj sync wrapper jeśli dostępny
        try:
            from sync.sync_integration import _sync_wrapper
            if _sync_wrapper:
                result = _sync_wrapper.delete_product(product_id)
                return jsonify(result)
        except ImportError:
            pass
        
        # Fallback - usuń lokalnie
        from utils.data_utils import load_products
        products = load_products()
        products = [p for p in products if p['id'] != product_id]
        
        with open('data/products.txt', 'w', encoding='utf-8') as f:
            for product in products:
                f.write(json.dumps(product, ensure_ascii=False) + '\n')
        
        return jsonify({'success': True, 'message': 'Product deleted locally'})
        
    except Exception as e:
        logger.error(f"Error in delete_product: {e}")
        return jsonify({'success': False, 'error': str(e)})


@product_bp.route('/find_in_shops', methods=['POST'])
def find_in_shops():
    """API - wyszukuje produkt w sklepach"""
    return product_manager.find_in_shops()

@product_bp.route('/get_available_shops')
def get_available_shops():
    """API - zwraca dostępne sklepy"""
    return product_manager.get_available_shops()

@product_bp.route('/search_in_single_shop', methods=['POST'])
def search_in_single_shop():
    """API - wyszukuje w pojedynczym sklepie"""
    return product_manager.search_in_single_shop()

@product_bp.route('/product/<int:product_id>/find_missing')
def find_missing_for_product(product_id):
    """API - znajduje sklepy gdzie nie ma tego produktu"""
    return product_manager.find_missing_for_product(product_id)

@product_bp.route('/search_product_in_shop', methods=['POST'])
def search_product_in_shop():
    """API - wyszukuje produkt w konkretnym sklepie"""
    return product_manager.search_product_in_shop()

# =============================================================================
# API Endpoints - Links Management
# =============================================================================

@product_bp.route('/update_product_link', methods=['POST'])
def update_product_link():
    """API - aktualizuje link produktu - ROZSZERZONE"""
    try:
        data = request.get_json()
        link_id = data.get('link_id')
        
        if not link_id:
            return jsonify({'success': False, 'error': 'Brak link_id'})
        
        # NOWE: Użyj sync wrapper
        from sync.sync_integration import _sync_wrapper
        if _sync_wrapper:
            result = _sync_wrapper.update_link(link_id, data)
            return jsonify(result)
        else:
            # Fallback do starego kodu
            return links_manager.update_product_link()
            
    except Exception as e:
        logger.error(f"Error in update_product_link: {e}")
        return jsonify({'success': False, 'error': str(e)})

@product_bp.route('/delete_product_link', methods=['POST'])
def delete_product_link():
    """API - usuwa link produktu - ROZSZERZONE"""
    try:
        data = request.get_json()
        link_id = data.get('link_id')
        
        if not link_id:
            return jsonify({'success': False, 'error': 'Brak link_id'})
        
        # NOWE: Użyj sync wrapper
        from sync.sync_integration import _sync_wrapper
        if _sync_wrapper:
            result = _sync_wrapper.delete_link(link_id)
            return jsonify(result)
        else:
            # Fallback do starego kodu
            return links_manager.delete_product_link()
            
    except Exception as e:
        logger.error(f"Error in delete_product_link: {e}")
        return jsonify({'success': False, 'error': str(e)})
    
@product_bp.route('/update_substitute_group', methods=['POST'])
def update_substitute_group():
    """API - aktualizuje grupę zamienników"""
    try:
        data = request.get_json()
        group_id = data.get('group_id')
        
        if not group_id:
            return jsonify({'success': False, 'error': 'Brak group_id'})
        
        from sync.sync_integration import _sync_wrapper
        if _sync_wrapper:
            result = _sync_wrapper.update_substitute_group(group_id, data)
            return jsonify(result)
        else:
            return jsonify({'success': False, 'error': 'Sync not available'})
            
    except Exception as e:
        logger.error(f"Error in update_substitute_group: {e}")
        return jsonify({'success': False, 'error': str(e)})

@product_bp.route('/add_found_link', methods=['POST'])
def add_found_link():
    """API - dodaje link znaleziony przez wyszukiwanie"""
    return links_manager.add_found_link()

# =============================================================================
# API Endpoints - Pricing
# =============================================================================

@product_bp.route('/fetch_price_for_link', methods=['POST'])
def fetch_price_for_link():
    """API - pobiera cenę dla konkretnego linku"""
    return pricing_manager.fetch_price_for_link()

@product_bp.route('/add_manual_price_for_link', methods=['POST'])
def add_manual_price_for_link():
    """API - dodaje ręczną cenę dla linku"""
    return pricing_manager.add_manual_price_for_link()

# =============================================================================
# API Endpoints - URL Parsing & Shop Detection
# =============================================================================

@product_bp.route('/parse_url')
def parse_url():
    """API endpoint - parsowanie URL sklepu"""
    from urllib.parse import urlparse
    
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'Brak URL'})
    
    try:
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        
        # Identyfikacja sklepu po domenie
        shop_mappings = {
            'allegro.pl': 'allegro',
            'amazon.': 'amazon',
            'ceneo.pl': 'ceneo',
            'morele.net': 'morele',
            'x-kom.pl': 'x-kom',
            'mediamarkt.pl': 'mediamarkt',
            'saturn.pl': 'saturn',
            'empik.com': 'empik',
            'euro.com.pl': 'euro',
            'doz.pl': 'doz',
            'rosa24.pl': 'rosa24',
            'gemini.pl': 'gemini'
        }
        
        shop_id = None
        for pattern, shop in shop_mappings.items():
            if pattern in domain:
                shop_id = shop
                break
        
        if not shop_id:
            # Fallback - użyj domeny jako shop_id
            shop_id = domain.replace('www.', '').replace('.', '_')
        
        result = {
            'success': True,
            'shop_id': shop_id,
            'domain': domain,
            'is_allegro': 'allegro' in domain
        }
        
        # Specjalna obsługa Allegro - próba wyciągnięcia sprzedawcy
        if result['is_allegro']:
            try:
                import requests
                from bs4 import BeautifulSoup
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Próbuj znaleźć sprzedawcę
                seller_selectors = [
                    '[data-testid="seller-name"]',
                    '.seller-name',
                    '.offer-seller__name'
                ]
                
                for selector in seller_selectors:
                    seller_elem = soup.select_one(selector)
                    if seller_elem:
                        seller = seller_elem.get_text().strip()
                        if seller:
                            result['seller'] = seller
                            break
                            
            except Exception as e:
                pass  # Nie blokuj jeśli nie można wyciągnąć sprzedawcy
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Błąd parsowania URL: {str(e)}'
        })

@product_bp.route('/scrape_product_info', methods=['POST'])
def scrape_product_info():
    """API endpoint - scrapowanie informacji o produkcie ze strony"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'success': False, 'error': 'Brak URL'})
        
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse
        
        # Przygotuj nagłówki
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pl,en-US;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Pobierz stronę
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return jsonify({'success': False, 'error': f'HTTP {response.status_code}'})
        
        soup = BeautifulSoup(response.content, 'html.parser')
        parsed_url = urlparse(url.lower())
        domain = parsed_url.netloc.replace('www.', '')
        
        result = {
            'success': True,
            'product_name': None,
            'ean': None,
            'price': None,
            'currency': 'PLN',
            'shop_name': None,
            'shop_id': None,
            'seller': None,
            'image_url': None
        }
        
        # Identyfikuj sklep
        shop_mappings = {
            'allegro.pl': {'name': 'Allegro', 'id': 'allegro'},
            'amazon.pl': {'name': 'Amazon', 'id': 'amazon'},
            'amazon.com': {'name': 'Amazon', 'id': 'amazon'},
            'ceneo.pl': {'name': 'Ceneo', 'id': 'ceneo'},
            'morele.net': {'name': 'Morele', 'id': 'morele'},
            'x-kom.pl': {'name': 'x-kom', 'id': 'x-kom'},
            'mediamarkt.pl': {'name': 'MediaMarkt', 'id': 'mediamarkt'},
            'saturn.pl': {'name': 'Saturn', 'id': 'saturn'},
            'empik.com': {'name': 'Empik', 'id': 'empik'},
            'euro.com.pl': {'name': 'Euro', 'id': 'euro'},
            'doz.pl': {'name': 'DOZ', 'id': 'doz'},
            'rosa24.pl': {'name': 'Rosa24', 'id': 'rosa24'},
            'gemini.pl': {'name': 'Gemini', 'id': 'gemini'}
        }
        
        shop_info = None
        for pattern, info in shop_mappings.items():
            if pattern in domain:
                shop_info = info
                break
        
        if shop_info:
            result['shop_name'] = shop_info['name']
            result['shop_id'] = shop_info['id']
        else:
            result['shop_name'] = domain.title()
            result['shop_id'] = domain.replace('.', '_')
        
        # Selektory dla różnych sklepów
        if 'allegro' in domain:
            # Allegro
            title_selectors = [
                '[data-testid="product-name"]',
                'h1[data-testid="product-name"]',
                '.offer-title h1',
                'h1'
            ]
            
            price_selectors = [
                '[data-testid="price-amount"]',
                '.price',
                '.offer-price'
            ]
            
            seller_selectors = [
                '[data-testid="seller-name"]',
                '.seller-name',
                '.offer-seller__name'
            ]
            
            ean_selectors = [
                '[data-testid="ean"]',
                '.product-ean'
            ]
            
        elif 'amazon' in domain:
            # Amazon
            title_selectors = [
                '#productTitle',
                '.a-size-large',
                'h1.a-size-large'
            ]
            
            price_selectors = [
                '.a-price-whole',
                '.a-offscreen',
                '.a-price .a-offscreen'
            ]
            
        elif 'ceneo' in domain:
            # Ceneo
            title_selectors = [
                '.offer-title h1',
                'h1.product-name',
                '.product-title'
            ]
            
            price_selectors = [
                '.price',
                '.offer-price'
            ]
            
        else:
            # Ogólne selektory
            title_selectors = [
                'h1',
                '.product-title',
                '.product-name',
                '.prod-name',
                '.item-title',
                'title'
            ]
            
            price_selectors = [
                '.price',
                '.product-price',
                '.current-price',
                '.sale-price'
            ]
            
            ean_selectors = [
                '.ean',
                '.product-ean',
                '[data-ean]'
            ]
        
        # Wyciągnij nazwę produktu
        for selector in title_selectors:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text().strip()
                if len(title) > 5:  # Sprawdź czy to sensowna nazwa
                    result['product_name'] = title
                    break
        
        # Fallback - jeśli nie znaleziono tytułu, użyj <title>
        if not result['product_name']:
            title_elem = soup.find('title')
            if title_elem:
                title = title_elem.get_text().strip()
                # Usuń zbędne części z tytułu strony
                for remove_part in [' - Allegro.pl', ' - Amazon.pl', ' - Ceneo.pl', ' | ', ' - ']:
                    if remove_part in title:
                        title = title.split(remove_part)[0]
                        break
                result['product_name'] = title
        
        # Wyciągnij cenę
        for selector in price_selectors:
            elem = soup.select_one(selector)
            if elem:
                price_text = elem.get_text().strip()
                # Wyciągnij liczbę z ceny
                import re
                price_match = re.search(r'(\d+(?:[,.]?\d{2})?)', price_text.replace(' ', ''))
                if price_match:
                    price_str = price_match.group(1).replace(',', '.')
                    try:
                        result['price'] = float(price_str)
                        break
                    except ValueError:
                        continue
        
        # Wyciągnij EAN
        for selector in ean_selectors:
            elem = soup.select_one(selector)
            if elem:
                ean_text = elem.get_text().strip()
                # Sprawdź czy to wygląda jak EAN
                if ean_text.isdigit() and len(ean_text) in [8, 13]:
                    result['ean'] = ean_text
                    break
        
        # Specjalna obsługa Allegro - wyciągnij sprzedawcę
        if 'allegro' in domain and seller_selectors:
            for selector in seller_selectors:
                elem = soup.select_one(selector)
                if elem:
                    seller = elem.get_text().strip()
                    if seller and len(seller) > 2:
                        result['seller'] = seller
                        # Ustaw shop_id jako allegro-{seller}
                        seller_clean = seller.lower().replace(' ', '-').replace('.', '')
                        result['shop_id'] = f"allegro-{seller_clean}"
                        break
        
        # Wyciągnij URL obrazka
        img_selectors = [
            '.product-image img',
            '.main-image img',
            '.gallery-image img',
            'img[src*="product"]'
        ]
        
        for selector in img_selectors:
            elem = soup.select_one(selector)
            if elem and elem.get('src'):
                img_url = elem.get('src')
                if img_url.startswith('http'):
                    result['image_url'] = img_url
                    break
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@product_bp.route('/find_products/<shop_id>')
def find_products_in_shop(shop_id):
    """API endpoint - znajdź produkty bez linków w danym sklepie"""
    try:
        all_products = load_products()
        all_links = load_links()
        
        # Znajdź produkty które mają linki w tym sklepie
        products_with_shop = set()
        for link in all_links:
            if link.get('shop_id') == shop_id:
                products_with_shop.add(link['product_id'])
        
        # Produkty bez linków w tym sklepie
        missing_products = [
            p for p in all_products 
            if p['id'] not in products_with_shop
        ]
        
        return jsonify({
            'success': True,
            'shop_id': shop_id,
            'total_products': len(all_products),
            'products_with_shop': len(products_with_shop),
            'missing_products': missing_products[:50]  # Limit 50 na raz
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@product_bp.route('/search_product', methods=['POST'])
def search_product():
    """API endpoint - wyszukaj konkretny produkt w sklepie"""
    try:
        data = request.get_json()
        shop_id = data.get('shop_id')
        product_name = data.get('product_name')
        product_id = data.get('product_id')
        ean = data.get('ean', '')
        
        if not shop_id or not product_name:
            return jsonify({
                'success': False,
                'error': 'Brak shop_id lub product_name'
            })
        
        # Import product finder
        try:
            from product_finder import product_finder
            from shop_config import shop_config
            
            # Pobierz konfigurację wyszukiwania dla sklepu
            shop_config_data = shop_config.get_shop_config(shop_id)
            search_config = shop_config_data.get('search_config', {})
            
            if not search_config.get('search_url'):
                return jsonify({
                    'success': False,
                    'error': f'Brak konfiguracji wyszukiwania dla sklepu {shop_id}'
                })
            
            # Wykonaj wyszukiwanie
            debug_info = []
            search_result = product_finder.search_product(
                search_config, product_name, ean, debug_info
            )
            
            # Dodaj debug info do wyniku
            search_result['debug'] = debug_info
            
            return jsonify(search_result)
            
        except ImportError as e:
            return jsonify({
                'success': False,
                'error': f'Brak modułu product_finder: {str(e)}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@product_bp.route('/test_shop_search', methods=['POST'])
def test_shop_search():
    """API endpoint - test wyszukiwarki sklepu"""
    try:
        data = request.get_json()
        shop_id = data.get('shop_id')
        query = data.get('query')
        
        if not shop_id or not query:
            return jsonify({
                'success': False,
                'error': 'Brak shop_id lub query'
            })
        
        try:
            from product_finder import product_finder
            from shop_config import shop_config
            
            # Pobierz konfigurację wyszukiwania
            shop_config_data = shop_config.get_shop_config(shop_id)
            search_config = shop_config_data.get('search_config', {})
            
            if not search_config.get('search_url'):
                return jsonify({
                    'success': False,
                    'error': f'Brak konfiguracji wyszukiwania dla sklepu {shop_id}'
                })
            
            # Test wyszukiwania
            debug_info = []
            result = product_finder.search_product(
                search_config, query, '', debug_info
            )
            
            result['debug'] = debug_info
            return jsonify(result)
            
        except ImportError as e:
            return jsonify({
                'success': False,
                'error': f'Brak modułu product_finder: {str(e)}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# =============================================================================
# ENDPOINTY DLA ZAMIENNIKÓW
# =============================================================================

@product_bp.route('/api/substitutes/<int:product_id>')
def get_product_substitutes(product_id):
    """API - zwraca zamienniki dla produktu"""
    try:
        from substitute_manager import substitute_manager
        from utils.data_utils import get_latest_prices, get_product_price_range
        
        substitute_info = substitute_manager.get_substitutes_for_product(product_id)
        
        # Dodaj informacje o cenach dla każdego zamiennika
        latest_prices = get_latest_prices()
        for substitute in substitute_info['substitutes']:
            min_price, max_price = get_product_price_range(substitute['id'], latest_prices)
            substitute['min_price'] = min_price
            substitute['max_price'] = max_price
        
        return jsonify({
            'success': True,
            'substitutes': substitute_info['substitutes'],
            'group_id': substitute_info['group_id'],
            'settings': substitute_info['settings']
        })
        
    except ImportError:
        return jsonify({'success': False, 'error': 'Moduł zamienników niedostępny'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@product_bp.route('/api/substitutes/create_group', methods=['POST'])
def create_substitute_group():
    """API - tworzy nową grupę zamienników"""
    try:
        from substitute_manager import substitute_manager
        
        data = request.get_json()
        name = data.get('name', '').strip()
        product_ids = data.get('product_ids', [])
        
        if not name:
            return jsonify({'success': False, 'error': 'Nazwa grupy jest wymagana'})
        
        if len(product_ids) < 2:
            return jsonify({'success': False, 'error': 'Grupa musi zawierać co najmniej 2 produkty'})
        
        # Sprawdź czy produkty istnieją
        products = load_products()
        existing_product_ids = {p['id'] for p in products}
        
        valid_product_ids = [pid for pid in product_ids if pid in existing_product_ids]
        
        if len(valid_product_ids) < 2:
            return jsonify({'success': False, 'error': 'Za mało prawidłowych produktów'})
        
        # Utwórz grupę
        group_id = substitute_manager.create_substitute_group(name, valid_product_ids)
        
        return jsonify({
            'success': True,
            'group_id': group_id,
            'message': f'Utworzono grupę "{name}" z {len(valid_product_ids)} produktami'
        })
        
    except ImportError:
        return jsonify({'success': False, 'error': 'Moduł zamienników niedostępny'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@product_bp.route('/api/substitutes/<int:product_id>/remove', methods=['DELETE'])
def remove_product_from_substitutes(product_id):
    """API - usuwa produkt z grupy zamienników"""
    try:
        from substitute_manager import substitute_manager
        substitute_manager.remove_product_from_group(product_id)
        return jsonify({'success': True, 'message': 'Produkt został usunięty z grupy zamienników'})
        
    except ImportError:
        return jsonify({'success': False, 'error': 'Moduł zamienników niedostępny'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@product_bp.route('/api/substitutes/groups')
def get_all_substitute_groups():
    """API - zwraca wszystkie grupy zamienników"""
    try:
        from substitute_manager import substitute_manager
        groups = substitute_manager.get_all_substitute_groups()
        return jsonify({'success': True, 'groups': groups})
        
    except ImportError:
        return jsonify({'success': False, 'error': 'Moduł zamienników niedostępny'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@product_bp.route('/delete_substitute_group', methods=['POST'])
def delete_substitute_group():
    """API - usuwa grupę zamienników"""
    try:
        data = request.get_json()
        group_id = data.get('group_id')
        
        if not group_id:
            return jsonify({'success': False, 'error': 'Brak group_id'})
        
        from sync.sync_integration import _sync_wrapper
        if _sync_wrapper:
            result = _sync_wrapper.delete_substitute_group(group_id)
            return jsonify(result)
        else:
            return jsonify({'success': False, 'error': 'Sync not available'})
            
    except Exception as e:
        logger.error(f"Error in delete_substitute_group: {e}")
        return jsonify({'success': False, 'error': str(e)})

@product_bp.route('/api/products/search')
def search_products_api():
    """API - wyszukuje produkty po nazwie (dla tworzenia grup zamienników)"""
    try:
        query = request.args.get('q', '').strip()
        
        if len(query) < 2:
            return jsonify({'success': True, 'products': []})
        
        # Proste wyszukiwanie po nazwie
        products = load_products()
        products = [p for p in products if query.lower() in p['name'].lower()][:20]
        
        return jsonify({'success': True, 'products': products})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})