"""
Moduł obsługujący pobieranie i zarządzanie cenami produktów
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
    """Klasa zarządzająca pobieraniem i zapisywaniem cen"""
    
    def fetch_price_for_link(self):
        """API - pobiera cenę dla konkretnego linku"""
        if not SCRAPER_AVAILABLE:
            return jsonify({'success': False, 'error': 'Scraper nie jest dostępny'})
        
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            shop_id = data.get('shop_id')
            url = data.get('url')
            
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
                
                save_price(price_data)
                
                return jsonify({
                    'success': True,
                    'price': page_info['price'],
                    'currency': currency,
                    'price_type': price_type
                })
            else:
                return jsonify({
                    'success': False,
                    'error': page_info.get('error', 'Nie udało się pobrać ceny'),
                    'show_manual_modal': True  # Sygnał do pokazania modala
                })
            
        except Exception as e:
            return jsonify({
                'success': False, 
                'error': str(e),
                'show_manual_modal': True
            })
    
    def add_manual_price_for_link(self):
        """API - dodaje ręczną cenę dla linku"""
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            shop_id = data.get('shop_id')
            url = data.get('url')
            price = float(data.get('price'))
            currency = data.get('currency', 'PLN')
            
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
            except ImportError:
                price_data['user_id'] = 'unknown'
            
            save_price(price_data)
            
            return jsonify({
                'success': True,
                'message': 'Cena została dodana ręcznie',
                'price': price,
                'currency': currency
            })
            
        except ValueError:
            return jsonify({'success': False, 'error': 'Nieprawidłowa wartość ceny'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})