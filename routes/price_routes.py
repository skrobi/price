"""
Routes związane z cenami - z paginacją i user_id
"""
from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import math
from utils.data_utils import load_prices, save_price, load_links, load_products, convert_to_pln

# Importuj scraper bezpiecznie
try:
    from price_scraper import scraper
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False
    print("WARNING: price_scraper not available - some features will be disabled")

# Importuj user_manager bezpiecznie
try:
    from user_manager import user_manager
    USER_MANAGER_AVAILABLE = True
except ImportError:
    USER_MANAGER_AVAILABLE = False
    print("WARNING: user_manager not available - some features will be disabled")

price_bp = Blueprint('prices', __name__)

# Konfiguracja paginacji
ITEMS_PER_PAGE = 50

def get_current_user_id():
    """Pobiera ID aktualnego użytkownika"""
    if USER_MANAGER_AVAILABLE:
        try:
            return user_manager.get_user_id()
        except:
            return 'unknown'
    return 'unknown'

@price_bp.route('/prices')
def prices():
    # Pobierz parametry z URL
    page = request.args.get('page', 1, type=int)
    shop_filter = request.args.get('shop', '', type=str)
    product_filter = request.args.get('product', '', type=str)
    
    # Załaduj wszystkie dane
    all_prices = load_prices()
    all_prices.sort(key=lambda x: x['created'], reverse=True)
    
    products = load_products()
    product_names = {p['id']: p['name'] for p in products}
    
    # Ładuj linki żeby mieć URL-e
    links = load_links()
    product_shop_urls = {}
    for link in links:
        key = f"{link['product_id']}-{link['shop_id']}"
        product_shop_urls[key] = link['url']
    
    # Wzbogać dane o nazwy produktów i ceny PLN
    for price in all_prices:
        price['product_name'] = product_names.get(price['product_id'], 'Nieznany produkt')
        price['price_pln'] = convert_to_pln(price['price'], price.get('currency', 'PLN'))
        
        # Dodaj URL jeśli go nie ma
        if 'url' not in price:
            key = f"{price['product_id']}-{price['shop_id']}"
            price['url'] = product_shop_urls.get(key, '#')
    
    # Filtrowanie
    filtered_prices = all_prices
    
    if shop_filter:
        filtered_prices = [p for p in filtered_prices if shop_filter.lower() in p['shop_id'].lower()]
    
    if product_filter:
        filtered_prices = [p for p in filtered_prices if product_filter.lower() in p['product_name'].lower()]
    
    # Obliczenia paginacji
    total_items = len(filtered_prices)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    
    # Sprawdź czy strona nie jest za wysoka
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    # Wyciągnij dane dla aktualnej strony
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_prices = filtered_prices[start:end]
    
    # Przygotuj dane dla szablonu
    pagination_data = {
        'page': page,
        'total_pages': total_pages,
        'total_items': total_items,
        'items_per_page': ITEMS_PER_PAGE,
        'start_item': start + 1 if total_items > 0 else 0,
        'end_item': min(end, total_items),
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None
    }
    
    # Przygotuj listę unikalnych sklepów dla filtra
    unique_shops = sorted(set(p['shop_id'] for p in all_prices))
    
    return render_template('prices.html', 
                         prices=page_prices,
                         pagination=pagination_data,
                         unique_shops=unique_shops,
                         current_shop_filter=shop_filter,
                         current_product_filter=product_filter)

@price_bp.route('/fetch_prices_ajax', methods=['POST'])
def fetch_prices_ajax():
    """AJAX endpoint - pobiera ceny po jednej Z USER_ID"""
    if not SCRAPER_AVAILABLE:
        return jsonify({
            'status': 'error',
            'error': 'Price scraper is not available'
        })
        
    try:
        data = request.get_json()
        link_index = data.get('link_index', 0)
        
        links = load_links()
        if link_index >= len(links):
            return jsonify({'status': 'complete'})
        
        link = links[link_index]
        
        # Pobierz nazwę produktu
        products = load_products()
        product_name = 'Nieznany produkt'
        for product in products:
            if product['id'] == link['product_id']:
                product_name = product['name']
                break
        
        # Pobierz cenę dla tego linku
        page_info = scraper.scrape_page(link['url'], link['shop_id'])
        
        result = {
            'status': 'processed',
            'link_index': link_index,
            'shop_id': link['shop_id'],
            'product_name': product_name,
            'product_id': link['product_id'],
            'url': link['url'][:50] + '...',
            'full_url': link['url'],
            'debug': page_info.get('debug', [])
        }
        
        if page_info.get('success') and page_info.get('price'):
            currency = page_info.get('currency', 'PLN')
            price_type = page_info.get('price_type', 'unknown')
            
            price_data = {
                'product_id': link['product_id'],
                'shop_id': link['shop_id'],
                'price': page_info['price'],
                'price_type': price_type,
                'currency': currency,
                'url': link['url'],
                'user_id': get_current_user_id(),  # DODANE
                'source': 'ajax_scraping',         # DODANE
                'created': datetime.now().isoformat()
            }
            
            save_price(price_data)
            
            # Increment counter jeśli user_manager dostępny
            if USER_MANAGER_AVAILABLE:
                try:
                    user_manager.increment_prices_scraped()
                except:
                    pass
            
            result.update({
                'success': True,
                'price': page_info['price'],
                'currency': currency,
                'price_type': price_type
            })
        else:
            result.update({
                'success': False,
                'error': page_info.get('error', 'Nie udało się pobrać ceny')
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@price_bp.route('/api/user_info')
def get_user_info():
    """API endpoint - zwraca informacje o użytkowniku"""
    if not USER_MANAGER_AVAILABLE:
        return jsonify({
            'user_id': 'unknown',
            'mode': 'local_only',
            'stats': {'prices_scraped': 0}
        })
    
    try:
        user_info = user_manager.get_user_info()
        return jsonify({
            'user_id': user_info.get('user_id', 'unknown'),
            'instance_name': user_info.get('instance_name', 'PriceTracker'),
            'mode': 'local_with_id',
            'stats': user_info.get('stats', {}),
            'settings': user_info.get('settings', {}),
            'created': user_info.get('created')
        })
    except Exception as e:
        return jsonify({
            'user_id': 'error',
            'mode': 'error',
            'error': str(e)
        })

@price_bp.route('/get_links_count')
def get_links_count():
    """Zwraca liczbę linków do przetworzenia"""
    links = load_links()
    return jsonify({'count': len(links)})

@price_bp.route('/fetch_prices', methods=['POST'])
def fetch_prices():
    """Pobiera ceny dla wszystkich linków - stara metoda synchroniczna Z USER_ID"""
    if not SCRAPER_AVAILABLE:
        return render_template('fetch_prices_result.html', 
                             results=['❌ Price scraper is not available'], 
                             success_count=0, 
                             error_count=1)
    
    links = load_links()
    success_count = 0
    error_count = 0
    results = []
    
    user_id = get_current_user_id()  # DODANE
    
    for link in links:
        results.append(f"🔍 Rozpoczynam: {link['shop_id']} - {link['url'][:50]}...")
        
        try:
            # Używamy scrapera
            page_info = scraper.scrape_page(link['url'])
            
            # Debug: pokaż szczegóły parsowania
            if 'debug' in page_info:
                for debug_line in page_info['debug']:
                    results.append(f"    {debug_line}")
            
            # Sprawdź rezultat
            if not page_info['success']:
                results.append(f"❌ {link['shop_id']}: Parsowanie nieudane - {page_info['error']}")
                error_count += 1
                continue
            
            # Sprawdź cenę
            if page_info.get('price'):
                currency = page_info.get('currency', 'PLN')
                price_type = page_info.get('price_type', 'unknown')
                
                price_data = {
                    'product_id': link['product_id'],
                    'shop_id': link['shop_id'],
                    'price': page_info['price'],
                    'price_type': price_type,
                    'currency': currency,
                    'url': link['url'],
                    'user_id': user_id,                        # DODANE
                    'source': 'bulk_scraping',                 # DODANE
                    'created': datetime.now().isoformat()
                }
                
                save_price(price_data)
                success_count += 1
                
                # Increment counter
                if USER_MANAGER_AVAILABLE:
                    try:
                        user_manager.increment_prices_scraped()
                    except:
                        pass
                
                # Emoji dla typu ceny
                type_emoji = {
                    'promo': '🏷️',
                    'regular': '💰', 
                    'regex': '🔍',
                    'allegro_html': '🛒',
                    'unknown': '❓'
                }.get(price_type, '❓')
                
                results.append(f"{type_emoji} {link['shop_id']}: CENA ZNALEZIONA: {page_info['price']} {currency} ({price_type})")
            else:
                error_count += 1
                results.append(f"❌ {link['shop_id']}: Cena nie została znaleziona na stronie")
                
        except Exception as e:
            error_count += 1
            results.append(f"💥 {link['shop_id']}: Błąd krytyczny - {str(e)[:100]}")
        
        results.append("─" * 80)
    
    return render_template('fetch_prices_result.html', results=results, 
                         success_count=success_count, error_count=error_count)

@price_bp.route('/add_manual_price', methods=['POST'])
def add_manual_price():
    """Endpoint do ręcznego dodawania ceny Z USER_ID"""
    try:
        data = request.get_json()
        
        price_data = {
            'product_id': data['product_id'],
            'shop_id': data['shop_id'],
            'price': float(data['price']),
            'price_type': 'manual',
            'currency': data.get('currency', 'PLN'),
            'url': data.get('url', ''),
            'user_id': get_current_user_id(),     # DODANE
            'source': 'manual_entry',            # DODANE
            'created': datetime.now().isoformat()
        }
        
        save_price(price_data)
        
        # Increment counter
        if USER_MANAGER_AVAILABLE:
            try:
                user_manager.increment_prices_scraped()
            except:
                pass
        
        return jsonify({
            'status': 'success',
            'message': 'Cena została dodana ręcznie'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })