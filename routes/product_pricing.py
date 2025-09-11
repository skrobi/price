"""
Moduł obsługujący pobieranie i zarządzanie cenami produktów - API-FIRST VERSION
"""
from flask import jsonify, request
from datetime import datetime
from utils.data_utils import save_price

# Importuj scraper bezpiecznie
try:
    from price_scraper import scraper
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False
    print("WARNING: price_scraper not available - some features will be disabled")

class ProductPricingManager:
    """Klasa zarządzająca pobieraniem i zapisywaniem cen - API-FIRST"""
    
    def fetch_price_for_link(self):
        """API - pobiera cenę dla konkretnego linku - API-FIRST"""
        if not SCRAPER_AVAILABLE:
            return jsonify({'success': False, 'error': 'Scraper nie jest dostępny'})
        
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            shop_id = data.get('shop_id')
            url = data.get('url')
            
            print(f"🔥 FETCH_PRICE_FOR_LINK: product_id={product_id}, shop_id={shop_id}")
            
            # Pobierz cenę
            page_info = scraper.scrape_page(url, shop_id)
            
            if page_info.get('success') and page_info.get('price'):
                currency = page_info.get('currency', 'PLN')
                price_type = page_info.get('price_type', 'manual_fetch')
                
                price_data = {
                    'product_id': product_id,
                    'shop_id': shop_id,
                    'price': page_info['price'],
                    'price_type': price_type,
                    'currency': currency,
                    'url': url,
                    'created': datetime.now().isoformat(),
                    'source': 'manual_fetch'
                }
                
                # Sprawdź czy user_manager jest dostępny
                try:
                    from user_manager import user_manager
                    price_data['user_id'] = user_manager.get_user_id()
                    user_manager.increment_prices_scraped()
                except ImportError:
                    price_data['user_id'] = 'unknown'
                
                print(f"🔥 SCRAPED PRICE_DATA: {price_data}")
                
                # API-FIRST SYNCHRONIZACJA
                try:
                    from sync.sync_integration import save_price_api_first
                    print(f"🔥 Import save_price_api_first: OK")
                    
                    result = save_price_api_first(price_data)
                    print(f"🔥 API-FIRST RESULT: {result}")
                    
                    return jsonify({
                        'success': True,
                        'price': page_info['price'],
                        'currency': currency,
                        'price_type': price_type,
                        'synced': result.get('synced', False),
                        'api_id': result.get('api_id'),
                        'temp_id': result.get('temp_id'),
                        'queued': result.get('queued', False),
                        'sync_message': result.get('message', ''),
                        'debug_result': result
                    })
                except ImportError as e:
                    print(f"🔥 IMPORT ERROR: {e}")
                    save_price(price_data)
                    return jsonify({
                        'success': True,
                        'price': page_info['price'],
                        'currency': currency,
                        'price_type': price_type,
                        'synced': False,
                        'sync_message': f'Saved locally only (import error: {e})'
                    })
                except Exception as e:
                    print(f"🔥 SYNC ERROR: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    save_price(price_data)
                    return jsonify({
                        'success': True,
                        'price': page_info['price'],
                        'currency': currency,
                        'price_type': price_type,
                        'synced': False,
                        'sync_message': f'Saved locally only (sync error: {e})'
                    })
            else:
                return jsonify({
                    'success': False,
                    'error': page_info.get('error', 'Nie udało się pobrać ceny'),
                    'show_manual_modal': True  # Sygnał do pokazania modala
                })
            
        except Exception as e:
            print(f"🔥 GENERAL ERROR in fetch_price_for_link: {e}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                'success': False, 
                'error': str(e),
                'show_manual_modal': True
            })
    
    def add_manual_price_for_link(self):
        """API - dodaje ręczną cenę dla linku - API-FIRST"""
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            shop_id = data.get('shop_id')
            url = data.get('url')
            price = float(data.get('price'))
            currency = data.get('currency', 'PLN')
            
            print(f"🔥 ADD_MANUAL_PRICE: product_id={product_id}, price={price} {currency}")
            
            if price <= 0:
                return jsonify({'success': False, 'error': 'Cena musi być większa od 0'})
            
            price_data = {
                'product_id': product_id,
                'shop_id': shop_id,
                'price': price,
                'price_type': 'manual',
                'currency': currency,
                'url': url,
                'created': datetime.now().isoformat(),
                'source': 'manual_entry'
            }
            
            # Sprawdź czy user_manager jest dostępny
            try:
                from user_manager import user_manager
                price_data['user_id'] = user_manager.get_user_id()
                print(f"🔥 USER_ID: {price_data['user_id']}")
            except ImportError:
                price_data['user_id'] = 'unknown'
                print(f"🔥 USER_ID: unknown (no user_manager)")
            
            print(f"🔥 MANUAL PRICE_DATA: {price_data}")
            
            # API-FIRST SYNCHRONIZACJA
            print(f"🔥 PRÓBA API-FIRST SYNCHRONIZACJI...")
            try:
                from sync.sync_integration import save_price_api_first
                print(f"🔥 Import save_price_api_first: OK")
                
                result = save_price_api_first(price_data)
                print(f"🔥 API-FIRST RESULT: {result}")
                
                success_message = 'Cena została dodana'
                if result.get('synced'):
                    success_message += ' i zsynchronizowana z API'
                elif result.get('queued'):
                    success_message += ' i dodana do kolejki synchronizacji'
                else:
                    success_message += ' lokalnie'
                
                return jsonify({
                    'success': True,
                    'message': success_message,
                    'price': price,
                    'currency': currency,
                    'synced': result.get('synced', False),
                    'api_id': result.get('api_id'),
                    'temp_id': result.get('temp_id'),
                    'queued': result.get('queued', False),
                    'sync_message': result.get('message', ''),
                    'debug_result': result
                })
            except ImportError as e:
                print(f"🔥 IMPORT ERROR: {e}")
                save_price(price_data)
                return jsonify({
                    'success': True,
                    'message': 'Cena została dodana lokalnie',
                    'price': price,
                    'currency': currency,
                    'synced': False,
                    'sync_message': f'Import error: {e}'
                })
            except Exception as e:
                print(f"🔥 SYNC ERROR: {e}")
                import traceback
                traceback.print_exc()
                
                save_price(price_data)
                return jsonify({
                    'success': True,
                    'message': 'Cena została dodana lokalnie (błąd sync)',
                    'price': price,
                    'currency': currency,
                    'synced': False,
                    'sync_message': f'Sync error: {e}'
                })
            
        except ValueError:
            return jsonify({'success': False, 'error': 'Nieprawidłowa wartość ceny'})
        except Exception as e:
            print(f"🔥 GENERAL ERROR in add_manual_price_for_link: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)})