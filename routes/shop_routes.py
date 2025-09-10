"""
Routes związane ze sklepami - API-FIRST VERSION
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from utils.data_utils import load_links
from shop_config import shop_config
from utils.data_utils import load_products, load_links
import logging

logger = logging.getLogger(__name__)

shop_bp = Blueprint('shops', __name__)

@shop_bp.route('/shops')
def shops():
    # Auto-stwórz konfiguracje dla wszystkich istniejących shop_id z linków
    try:
        existing_links = load_links()
        existing_shop_ids = set()
        
        for link in existing_links:
            if isinstance(link, dict) and 'shop_id' in link:
                existing_shop_ids.add(link['shop_id'])
        
        # Upewnij się, że każdy shop_id ma konfigurację
        for shop_id in existing_shop_ids:
            config = shop_config.get_shop_config(shop_id)
            if shop_id not in shop_config.load_shop_configs():
                # API-FIRST: Najpierw spróbuj zapisać w API
                try:
                    from sync.sync_integration import save_shop_config_api_first
                    save_shop_config_api_first(config)
                except ImportError:
                    shop_config.save_shop_config(config)
        
        shops_list = shop_config.get_all_shops()
        
        # POPRAWKA: Sprawdź czy shops_list jest listą słowników
        if not isinstance(shops_list, list):
            logger.error(f"shops_list is not a list: {type(shops_list)}")
            shops_list = []
        
        # NOWE: Dodaj liczbę produktów dla każdego sklepu
        for shop in shops_list:
            if isinstance(shop, dict):  # POPRAWKA: Sprawdź typ
                shop_id = shop.get('shop_id', '')
                
                # Policz produkty w tym sklepie
                products_count = len([link for link in existing_links 
                                    if isinstance(link, dict) and link.get('shop_id') == shop_id])
                shop['products_count'] = products_count
                
                # POPRAWKA: Bezpieczne sprawdzenie search_config
                search_config = shop.get('search_config', {})
                if isinstance(search_config, dict):
                    shop['has_search'] = bool(search_config.get('search_url'))
                else:
                    shop['has_search'] = False
                
                # POPRAWKA: Bezpieczne sprawdzenie price_selectors
                price_selectors = shop.get('price_selectors', [])
                if isinstance(price_selectors, list):
                    shop['has_selectors'] = len(price_selectors) > 0
                    shop['total_selectors'] = len(price_selectors)
                elif isinstance(price_selectors, dict):
                    shop['has_selectors'] = any(isinstance(v, list) and len(v) > 0 for v in price_selectors.values())
                    shop['total_selectors'] = sum(len(v) if isinstance(v, list) else 0 for v in price_selectors.values())
                else:
                    shop['has_selectors'] = False
                    shop['total_selectors'] = 0
                
                # Dodaj informacje o sync
                if shop.get('synced'):
                    shop['sync_status'] = 'synced'
                elif shop.get('temp_id'):
                    shop['sync_status'] = 'pending'
                elif shop.get('needs_sync'):
                    shop['sync_status'] = 'queued'
                else:
                    shop['sync_status'] = 'local'
            else:
                logger.warning(f"Shop data is not dict: {type(shop)} = {shop}")
                # Usuń nieprawidłowe elementy
                continue
        
        # POPRAWKA: Filtruj tylko słowniki
        shops_list = [shop for shop in shops_list if isinstance(shop, dict)]
        
        # Sortuj domyślnie według nazwy
        shops_list.sort(key=lambda x: x.get('name', '').lower())
        
    except Exception as e:
        logger.error(f"Error in shops route: {e}")
        shops_list = []
        flash(f'Błąd ładowania sklepów: {str(e)}')
    
    return render_template('shops.html', shops=shops_list)

@shop_bp.route('/shop/<shop_id>')
def shop_detail(shop_id):
    """Szczegóły i edycja konfiguracji sklepu - POPRAWIONA WERSJA"""
    try:
        from utils.data_utils import load_links, load_products, load_prices
        
        shop = shop_config.get_shop_config(shop_id)
        
        # Pobierz produkty dla tego sklepu
        all_links = load_links()
        all_products = load_products()
        all_prices = load_prices()
        
        # Znajdź linki dla tego sklepu
        shop_links = [link for link in all_links 
                     if isinstance(link, dict) and link.get('shop_id') == shop_id]
        
        # Stwórz mapę produktów (id -> nazwa)
        products_map = {p['id']: p['name'] for p in all_products if isinstance(p, dict)}
        
        # POPRAWKA: Znajdź najnowsze ceny dla każdego KONKRETNEGO LINKU (product_id + URL)
        latest_prices = {}
        for price in all_prices:
            if isinstance(price, dict) and price.get('shop_id') == shop_id:
                # KLUCZ: kombinacja product_id + URL zamiast tylko product_id
                key = f"{price.get('product_id', '')}|{price.get('url', '')}"
                if key not in latest_prices or price.get('created', '') > latest_prices[key].get('created', ''):
                    latest_prices[key] = price
        
        # Połącz dane
        shop_products = []
        for link in shop_links:
            if isinstance(link, dict):
                product_data = {
                    'product_id': link.get('product_id'),
                    'product_name': products_map.get(link.get('product_id'), 'Nieznany produkt'),
                    'url': link.get('url', ''),
                    'created': link.get('created', ''),
                    'latest_price': None,
                    'currency': None,
                    'price_updated': None
                }
                
                # Dodaj informacje o sync linku
                if link.get('synced'):
                    product_data['link_sync_status'] = 'synced'
                elif link.get('temp_id'):
                    product_data['link_sync_status'] = 'pending'
                elif link.get('needs_sync'):
                    product_data['link_sync_status'] = 'queued'
                else:
                    product_data['link_sync_status'] = 'local'
                
                # POPRAWKA: Szukaj ceny po kluczu product_id + URL
                price_key = f"{link.get('product_id', '')}|{link.get('url', '')}"
                if price_key in latest_prices:
                    price_data = latest_prices[price_key]
                    product_data['latest_price'] = price_data.get('price')
                    product_data['currency'] = price_data.get('currency', 'PLN')
                    product_data['price_updated'] = price_data.get('created')
                    
                    # Dodaj informacje o sync ceny
                    if price_data.get('synced'):
                        product_data['price_sync_status'] = 'synced'
                    elif price_data.get('temp_id'):
                        product_data['price_sync_status'] = 'pending'
                    elif price_data.get('needs_sync'):
                        product_data['price_sync_status'] = 'queued'
                    else:
                        product_data['price_sync_status'] = 'local'
                
                shop_products.append(product_data)
        
        # Sortuj według nazwy produktu
        shop_products.sort(key=lambda x: x.get('product_name', ''))
        
        # Dodaj liczbę produktów do shop
        if isinstance(shop, dict):
            shop['products_count'] = len(shop_products)
        
    except Exception as e:
        logger.error(f"Error in shop_detail for {shop_id}: {e}")
        shop = shop_config.get_shop_config(shop_id)
        shop_products = []
        flash(f'Błąd ładowania danych sklepu: {str(e)}')
    
    return render_template('shop_detail.html', shop=shop, shop_products=shop_products)

@shop_bp.route('/shop/<shop_id>/edit', methods=['GET', 'POST'])
def edit_shop(shop_id):
    """Edycja konfiguracji sklepu - API-FIRST VERSION"""
    try:
        if request.method == 'POST':
            print(f"🔥 EDIT_SHOP POST for {shop_id}")
            
            # Pobierz selektory z formularza (jeden na linię)
            selectors_text = request.form.get('selectors', '').strip()
            selectors = [s.strip() for s in selectors_text.split('\n') if s.strip()]
            
            # Pobierz konfigurację wyszukiwania
            search_config = {}
            
            if request.form.get('search_url'):
                search_config['search_url'] = request.form['search_url'].strip()
                
                # Selektory wyników
                result_selectors_text = request.form.get('result_selectors', '').strip()
                search_config['result_selectors'] = [s.strip() for s in result_selectors_text.split('\n') if s.strip()]
                
                # Selektory tytułów
                title_selectors_text = request.form.get('title_selectors', '').strip()
                search_config['title_selectors'] = [s.strip() for s in title_selectors_text.split('\n') if s.strip()]
                
                # Metody wyszukiwania
                search_methods = request.form.getlist('search_methods')
                search_config['search_methods'] = search_methods if search_methods else ['name']
            
            # Aktualizuj konfigurację
            config = shop_config.get_shop_config(shop_id)
            config['name'] = request.form.get('name', '') or shop_id
            config['price_selectors'] = selectors
            config['delivery_free_from'] = float(request.form['delivery_free_from']) if request.form.get('delivery_free_from') else None
            config['delivery_cost'] = float(request.form['delivery_cost']) if request.form.get('delivery_cost') else None
            config['currency'] = request.form.get('currency', '') or 'PLN'
            
            # Zapisz konfigurację wyszukiwania tylko jeśli jest URL
            if search_config.get('search_url'):
                config['search_config'] = search_config
            elif 'search_config' in config:
                # Zachowaj istniejącą konfigurację jeśli nie ma nowej
                pass
            
            print(f"🔥 CONFIG to save: {config}")
            
            # API-FIRST SYNCHRONIZACJA
            print(f"🔥 PRÓBA API-FIRST SYNCHRONIZACJI...")
            try:
                from sync.sync_integration import save_shop_config_api_first
                print(f"🔥 Import save_shop_config_api_first: OK")
                
                result = save_shop_config_api_first(config)
                print(f"🔥 API-FIRST RESULT: {result}")
                
                if result.get('synced'):
                    flash(f'Zaktualizowano i zsynchronizowano konfigurację sklepu {shop_id}')
                elif result.get('queued'):
                    flash(f'Zaktualizowano konfigurację sklepu {shop_id} (w kolejce do synchronizacji)')
                else:
                    flash(f'Zaktualizowano konfigurację sklepu {shop_id} (lokalnie)')
                    
            except ImportError as e:
                print(f"🔥 IMPORT ERROR: {e}")
                shop_config.save_shop_config(config)
                flash(f'Zaktualizowano konfigurację sklepu {shop_id}')
            except Exception as e:
                print(f"🔥 SYNC ERROR: {e}")
                import traceback
                traceback.print_exc()
                
                shop_config.save_shop_config(config)
                flash(f'Zaktualizowano konfigurację sklepu {shop_id} (błąd synchronizacji)')
            
            return redirect(url_for('shops.shop_detail', shop_id=shop_id))
        
        shop = shop_config.get_shop_config(shop_id)
        
    except Exception as e:
        logger.error(f"Error in edit_shop for {shop_id}: {e}")
        shop = shop_config.get_shop_config(shop_id)
        flash(f'Błąd edycji sklepu: {str(e)}')
    
    return render_template('edit_shop.html', shop=shop)

@shop_bp.route('/get_products_not_in_shop/<shop_id>')
def get_products_not_in_shop(shop_id):
    """Zwraca produkty które nie są jeszcze w danym sklepie"""
    try:
        from utils.data_utils import load_products, load_links
        
        all_products = load_products()
        all_links = load_links()
        
        # Znajdź produkty które są już w tym sklepie
        products_in_shop = set()
        for link in all_links:
            if isinstance(link, dict) and link.get('shop_id') == shop_id:
                products_in_shop.add(link.get('product_id'))
        
        # Znajdź produkty które NIE są w tym sklepie
        available_products = [p for p in all_products 
                            if isinstance(p, dict) and p.get('id') not in products_in_shop]
        
        return jsonify({
            'success': True,
            'shop_id': shop_id,
            'products': available_products,
            'total_available': len(available_products),
            'total_products': len(all_products)
        })
        
    except Exception as e:
        logger.error(f"Error in get_products_not_in_shop: {e}")
        return jsonify({'success': False, 'error': str(e)})

@shop_bp.route('/shops/stats')
def shops_stats():
    """API endpoint - zwraca statystyki sklepów"""
    try:
        existing_links = load_links()
        shops_list = shop_config.get_all_shops()
        
        # POPRAWKA: Filtruj tylko słowniki
        shops_list = [shop for shop in shops_list if isinstance(shop, dict)]
        
        stats = {
            'total_shops': len(shops_list),
            'shops_with_products': 0,
            'shops_with_selectors': 0,
            'shops_with_search': 0,
            'total_products': len([link for link in existing_links if isinstance(link, dict)]),
            'shops_breakdown': []
        }
        
        for shop in shops_list:
            if isinstance(shop, dict):
                shop_id = shop.get('shop_id', '')
                products_count = len([link for link in existing_links 
                                    if isinstance(link, dict) and link.get('shop_id') == shop_id])
                
                price_selectors = shop.get('price_selectors', [])
                if isinstance(price_selectors, list):
                    selectors_count = len(price_selectors)
                elif isinstance(price_selectors, dict):
                    selectors_count = sum(len(v) if isinstance(v, list) else 0 for v in price_selectors.values())
                else:
                    selectors_count = 0
                
                search_config = shop.get('search_config', {})
                has_search = isinstance(search_config, dict) and bool(search_config.get('search_url'))
                
                if products_count > 0:
                    stats['shops_with_products'] += 1
                if selectors_count > 0:
                    stats['shops_with_selectors'] += 1
                if has_search:
                    stats['shops_with_search'] += 1
                
                # Dodaj informacje o sync
                sync_status = 'local'
                if shop.get('synced'):
                    sync_status = 'synced'
                elif shop.get('temp_id'):
                    sync_status = 'pending'
                elif shop.get('needs_sync'):
                    sync_status = 'queued'
                
                stats['shops_breakdown'].append({
                    'shop_id': shop_id,
                    'name': shop.get('name', shop_id),
                    'products_count': products_count,
                    'selectors_count': selectors_count,
                    'has_search': has_search,
                    'currency': shop.get('currency', 'PLN'),
                    'delivery_configured': bool(shop.get('delivery_free_from') or shop.get('delivery_cost')),
                    'sync_status': sync_status
                })
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error in shops_stats: {e}")
        return jsonify({'success': False, 'error': str(e)})