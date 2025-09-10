"""
Routes związane z cenami - API-FIRST VERSION
"""
from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import math
import logging
from utils.data_utils import load_prices, save_price, load_links, load_products

logger = logging.getLogger(__name__)

# Importuj scraper bezpiecznie
try:
   from price_scraper import scraper
   SCRAPER_AVAILABLE = True
except ImportError:
   SCRAPER_AVAILABLE = False
   logger.warning("price_scraper not available - some features will be disabled")

# Importuj user_manager bezpiecznie
try:
   from user_manager import user_manager
   USER_MANAGER_AVAILABLE = True
except ImportError:
   USER_MANAGER_AVAILABLE = False
   logger.warning("user_manager not available - some features will be disabled")

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

def safe_convert_to_pln(price_value, currency='PLN'):
   """Bezpieczna konwersja ceny na PLN z obsługą stringów"""
   try:
       if isinstance(price_value, str):
           price_clean = price_value.strip().replace(',', '.')
           import re
           numbers = re.findall(r'\d+\.?\d*', price_clean)
           if numbers:
               price_value = float(numbers[-1])
           else:
               logger.warning(f"Cannot parse price from string: {price_value}")
               return 0.0
       elif not isinstance(price_value, (int, float)):
           logger.warning(f"Price is not a number: {type(price_value)} = {price_value}")
           return 0.0
       
       # Proste kursy walut
       rates = {'PLN': 1.0, 'EUR': 4.30, 'USD': 4.00, 'GBP': 5.00}
       rate = rates.get(currency, 1.0)
       return float(price_value) * rate
       
   except Exception as e:
       logger.error(f"Error converting price to PLN: {e}, price={price_value}, currency={currency}")
       return 0.0

@price_bp.route('/prices')
def prices():
   try:
       # Pobierz parametry z URL
       page = request.args.get('page', 1, type=int)
       shop_filter = request.args.get('shop', '', type=str)
       product_filter = request.args.get('product', '', type=str)
       
       # Załaduj wszystkie dane
       all_prices = load_prices()
       
       # Filtruj tylko prawidłowe ceny
       valid_prices = []
       for price in all_prices:
           if isinstance(price, dict) and 'created' in price:
               valid_prices.append(price)
           else:
               logger.warning(f"Invalid price data: {price}")
       
       valid_prices.sort(key=lambda x: x.get('created', ''), reverse=True)
       
       products = load_products()
       product_names = {p['id']: p['name'] for p in products if isinstance(p, dict)}
       
       # Ładuj linki żeby mieć URL-e
       links = load_links()
       product_shop_urls = {}
       for link in links:
           if isinstance(link, dict):
               key = f"{link.get('product_id', '')}-{link.get('shop_id', '')}"
               product_shop_urls[key] = link.get('url', '#')
       
       # Wzbogać dane o nazwy produktów i ceny PLN z bezpieczną konwersją
       for price in valid_prices:
           if isinstance(price, dict):
               price['product_name'] = product_names.get(price.get('product_id'), 'Nieznany produkt')
               
               # Użyj bezpiecznej konwersji
               price['price_pln'] = safe_convert_to_pln(
                   price.get('price', 0), 
                   price.get('currency', 'PLN')
               )
               
               # Dodaj URL jeśli go nie ma
               if 'url' not in price:
                   key = f"{price.get('product_id', '')}-{price.get('shop_id', '')}"
                   price['url'] = product_shop_urls.get(key, '#')
               
               # Dodaj informacje o sync
               if price.get('synced'):
                   price['sync_status'] = 'synced'
               elif price.get('temp_id'):
                   price['sync_status'] = 'pending'
               elif price.get('needs_sync'):
                   price['sync_status'] = 'queued'
               else:
                   price['sync_status'] = 'local'
       
       # Filtrowanie
       filtered_prices = valid_prices
       
       if shop_filter:
           filtered_prices = [p for p in filtered_prices 
                            if isinstance(p, dict) and shop_filter.lower() in p.get('shop_id', '').lower()]
       
       if product_filter:
           filtered_prices = [p for p in filtered_prices 
                            if isinstance(p, dict) and product_filter.lower() in p.get('product_name', '').lower()]
       
       # Obliczenia paginacji
       total_items = len(filtered_prices)
       total_pages = math.ceil(total_items / ITEMS_PER_PAGE) if total_items > 0 else 1
       
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
       unique_shops = sorted(set(p.get('shop_id', '') for p in valid_prices if isinstance(p, dict) and p.get('shop_id')))
       
       return render_template('prices.html', 
                            prices=page_prices,
                            pagination=pagination_data,
                            unique_shops=unique_shops,
                            current_shop_filter=shop_filter,
                            current_product_filter=product_filter)
                            
   except Exception as e:
       logger.error(f"Error in prices route: {e}")
       return render_template('prices.html', 
                            prices=[],
                            pagination={'page': 1, 'total_pages': 1, 'total_items': 0, 'has_prev': False, 'has_next': False},
                            unique_shops=[],
                            current_shop_filter='',
                            current_product_filter='',
                            error_message=f'Błąd ładowania cen: {str(e)}')

@price_bp.route('/fetch_prices_ajax', methods=['POST'])
def fetch_prices_ajax():
   """AJAX endpoint - pobiera ceny po jednej - API-FIRST VERSION"""
   if not SCRAPER_AVAILABLE:
       return jsonify({
           'status': 'error',
           'error': 'Price scraper is not available'
       })
       
   try:
       data = request.get_json()
       link_index = data.get('link_index', 0)
       
       links = load_links()
       valid_links = [link for link in links if isinstance(link, dict)]
       
       if link_index >= len(valid_links):
           return jsonify({'status': 'complete'})
       
       link = valid_links[link_index]
       
       # Pobierz nazwę produktu
       products = load_products()
       product_name = 'Nieznany produkt'
       for product in products:
           if isinstance(product, dict) and product.get('id') == link.get('product_id'):
               product_name = product.get('name', 'Nieznany produkt')
               break
       
       # Pobierz cenę dla tego linku
       page_info = scraper.scrape_page(link.get('url', ''), link.get('shop_id', ''))
       
       result = {
           'status': 'processed',
           'link_index': link_index,
           'shop_id': link.get('shop_id', ''),
           'product_name': product_name,
           'product_id': link.get('product_id'),
           'url': link.get('url', '')[:50] + '...',
           'full_url': link.get('url', ''),
           'debug': page_info.get('debug', [])
       }
       
       if page_info.get('success') and page_info.get('price'):
           currency = page_info.get('currency', 'PLN')
           price_type = page_info.get('price_type', 'unknown')
           
           # Upewnij się że price to liczba
           price_value = page_info['price']
           if isinstance(price_value, str):
               try:
                   price_value = float(price_value.replace(',', '.'))
               except ValueError:
                   result.update({
                       'success': False,
                       'error': f'Nieprawidłowy format ceny: {price_value}'
                   })
                   return jsonify(result)
           
           price_data = {
               'product_id': link.get('product_id'),
               'shop_id': link.get('shop_id', ''),
               'price': price_value,
               'price_type': price_type,
               'currency': currency,
               'url': link.get('url', ''),
               'user_id': get_current_user_id(),
               'source': 'ajax_scraping',
               'created': datetime.now().isoformat()
           }
           
           # API-FIRST SYNCHRONIZACJA
           try:
               from sync.sync_integration import save_price_api_first
               save_result = save_price_api_first(price_data)
               
               # Increment counter jeśli user_manager dostępny
               if USER_MANAGER_AVAILABLE:
                   try:
                       user_manager.increment_prices_scraped()
                   except:
                       pass
               
               result.update({
                   'success': True,
                   'price': price_value,
                   'currency': currency,
                   'price_type': price_type,
                   'synced': save_result.get('synced', False),
                   'api_id': save_result.get('api_id'),
                   'temp_id': save_result.get('temp_id'),
                   'queued': save_result.get('queued', False),
                   'sync_message': save_result.get('message', '')
               })
               
               # Loguj rezultat
               if save_result.get('synced'):
                   logger.info(f"Price {price_value} {currency} synced to API (ID: {save_result.get('api_id')})")
               elif save_result.get('queued'):
                   logger.info(f"Price {price_value} {currency} queued for sync (temp_id: {save_result.get('temp_id')})")
               else:
                   logger.warning(f"Price {price_value} {currency} saved locally only: {save_result.get('error')}")
                   
           except ImportError as e:
               logger.error(f"Import error in fetch_prices_ajax: {e}")
               save_price(price_data)
               result.update({
                   'success': True,
                   'price': price_value,
                   'currency': currency,
                   'price_type': price_type,
                   'synced': False,
                   'sync_message': f'Import error: {e}'
               })
           except Exception as e:
               logger.error(f"Sync error in fetch_prices_ajax: {e}")
               save_price(price_data)
               result.update({
                   'success': True,
                   'price': price_value,
                   'currency': currency,
                   'price_type': price_type,
                   'synced': False,
                   'sync_message': f'Sync error: {e}'
               })
               
       else:
           result.update({
               'success': False,
               'error': page_info.get('error', 'Nie udało się pobrać ceny')
           })
       
       return jsonify(result)
       
   except Exception as e:
       logger.error(f"Error in fetch_prices_ajax: {e}")
       return jsonify({
           'status': 'error',
           'error': str(e)
       })

@price_bp.route('/add_manual_price', methods=['POST'])
def add_manual_price():
   """Endpoint do ręcznego dodawania ceny - API-FIRST VERSION"""
   try:
       data = request.get_json()
       
       # Walidacja i konwersja ceny
       price_value = data.get('price')
       if isinstance(price_value, str):
           price_value = float(price_value.replace(',', '.'))
       else:
           price_value = float(price_value)
       
       price_data = {
           'product_id': data.get('product_id'),
           'shop_id': data.get('shop_id', ''),
           'price': price_value,
           'price_type': 'manual',
           'currency': data.get('currency', 'PLN'),
           'url': data.get('url', ''),
           'user_id': get_current_user_id(),
           'source': 'manual_entry',
           'created': datetime.now().isoformat()
       }
       
       # API-FIRST SYNCHRONIZACJA
       try:
           from sync.sync_integration import save_price_api_first
           save_result = save_price_api_first(price_data)
           
           # Increment counter
           if USER_MANAGER_AVAILABLE:
               try:
                   user_manager.increment_prices_scraped()
               except:
                   pass
           
           success_message = 'Cena została dodana'
           if save_result.get('synced'):
               success_message += ' i zsynchronizowana z API'
           elif save_result.get('queued'):
               success_message += ' i dodana do kolejki synchronizacji'
           else:
               success_message += ' lokalnie'
           
           response = {
               'status': 'success',
               'message': success_message,
               'synced': save_result.get('synced', False),
               'api_id': save_result.get('api_id'),
               'temp_id': save_result.get('temp_id'),
               'queued': save_result.get('queued', False),
               'sync_message': save_result.get('message', '')
           }
           
           # Loguj rezultat
           if save_result.get('synced'):
               logger.info(f"Manual price {price_value} {data.get('currency', 'PLN')} synced to API")
           elif save_result.get('queued'):
               logger.info(f"Manual price {price_value} {data.get('currency', 'PLN')} queued for sync")
           else:
               logger.warning(f"Manual price {price_value} {data.get('currency', 'PLN')} saved locally only")
           
           return jsonify(response)
           
       except ImportError as e:
           logger.error(f"Import error in add_manual_price: {e}")
           save_price(price_data)
           if USER_MANAGER_AVAILABLE:
               try:
                   user_manager.increment_prices_scraped()
               except:
                   pass
           return jsonify({
               'status': 'success',
               'message': 'Cena została dodana lokalnie',
               'synced': False,
               'sync_message': f'Import error: {e}'
           })
       except Exception as e:
           logger.error(f"Sync error in add_manual_price: {e}")
           save_price(price_data)
           if USER_MANAGER_AVAILABLE:
               try:
                   user_manager.increment_prices_scraped()
               except:
                   pass
           return jsonify({
               'status': 'success',
               'message': 'Cena została dodana lokalnie (błąd sync)',
               'synced': False,
               'sync_message': f'Sync error: {e}'
           })
       
   except Exception as e:
       logger.error(f"Error adding manual price: {e}")
       return jsonify({
           'status': 'error',
           'error': str(e)
       })

# Pozostałe endpointy bez zmian
@price_bp.route('/api/user_info')
def get_user_info():
   if not USER_MANAGER_AVAILABLE:
       return jsonify({'user_id': 'unknown', 'mode': 'local_only', 'stats': {'prices_scraped': 0}})
   
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
       return jsonify({'user_id': 'error', 'mode': 'error', 'error': str(e)})

@price_bp.route('/get_links_count')
def get_links_count():
   try:
       links = load_links()
       valid_links = [link for link in links if isinstance(link, dict)]
       return jsonify({'count': len(valid_links)})
   except Exception as e:
       return jsonify({'count': 0, 'error': str(e)})

@price_bp.route('/fetch_prices', methods=['POST'])
def fetch_prices():
   """Stara metoda synchroniczna - API-FIRST VERSION"""
   if not SCRAPER_AVAILABLE:
       return render_template('fetch_prices_result.html', 
                            results=['Price scraper is not available'], 
                            success_count=0, error_count=1)
   
   try:
       links = load_links()
       valid_links = [link for link in links if isinstance(link, dict)]
       
       success_count = 0
       error_count = 0
       synced_count = 0
       queued_count = 0
       results = []
       
       for link in valid_links:
           shop_id = link.get('shop_id', 'unknown')
           url = link.get('url', '')
           results.append(f"Rozpoczynam: {shop_id} - {url[:50]}...")
           
           try:
               page_info = scraper.scrape_page(url, shop_id)
               
               if 'debug' in page_info:
                   for debug_line in page_info['debug']:
                       results.append(f"    {debug_line}")
               
               if not page_info.get('success'):
                   results.append(f"Parsowanie nieudane - {page_info.get('error', 'Unknown error')}")
                   error_count += 1
                   continue
               
               if page_info.get('price'):
                   currency = page_info.get('currency', 'PLN')
                   price_type = page_info.get('price_type', 'unknown')
                   
                   price_value = page_info['price']
                   if isinstance(price_value, str):
                       try:
                           price_value = float(price_value.replace(',', '.'))
                       except ValueError:
                           results.append(f"Nieprawidłowy format ceny: {price_value}")
                           error_count += 1
                           continue
                   
                   price_data = {
                       'product_id': link.get('product_id'),
                       'shop_id': shop_id,
                       'price': price_value,
                       'price_type': price_type,
                       'currency': currency,
                       'url': url,
                       'user_id': get_current_user_id(),
                       'source': 'bulk_scraping',
                       'created': datetime.now().isoformat()
                   }
                   
                   # API-FIRST SYNCHRONIZACJA
                   try:
                       from sync.sync_integration import save_price_api_first
                       save_result = save_price_api_first(price_data)
                       
                       success_count += 1
                       
                       if save_result.get('synced'):
                           synced_count += 1
                       elif save_result.get('queued'):
                           queued_count += 1
                       
                       if USER_MANAGER_AVAILABLE:
                           try:
                               user_manager.increment_prices_scraped()
                           except:
                               pass
                       
                       if save_result.get('synced'):
                           sync_status = "API"
                       elif save_result.get('queued'):
                           sync_status = "QUEUE"
                       else:
                           sync_status = "LOCAL"
                       
                       results.append(f"CENA: {price_value} {currency} ({sync_status})")
                       
                   except ImportError as e:
                       save_price(price_data)
                       success_count += 1
                       results.append(f"CENA: {price_value} {currency} (LOCAL - import error)")
                   except Exception as e:
                       save_price(price_data)
                       success_count += 1
                       results.append(f"CENA: {price_value} {currency} (LOCAL - sync error)")
                   
               else:
                   error_count += 1
                   results.append(f"Cena nie została znaleziona")
                   
           except Exception as e:
               error_count += 1
               results.append(f"Błąd - {str(e)[:100]}")
           
           results.append("─" * 80)
       
       results.append(f"\nPODSUMOWANIE:")
       results.append(f"Sukces: {success_count}")
       results.append(f"Zsynchronizowane z API: {synced_count}")
       results.append(f"Dodane do kolejki: {queued_count}")
       results.append(f"Tylko lokalnie: {success_count - synced_count - queued_count}")
       results.append(f"Błędy: {error_count}")
       
       return render_template('fetch_prices_result.html', results=results, 
                            success_count=success_count, error_count=error_count)
                            
   except Exception as e:
       return render_template('fetch_prices_result.html', 
                            results=[f'Błąd krytyczny: {str(e)}'], 
                            success_count=0, error_count=1)