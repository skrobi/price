"""
Routes związane ze sklepami - POPRAWIONA WERSJA
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from utils.data_utils import load_links
from shop_config import shop_config
from utils.data_utils import load_products, load_links

shop_bp = Blueprint('shops', __name__)

@shop_bp.route('/shops')
def shops():
    # Auto-stwórz konfiguracje dla wszystkich istniejących shop_id z linków
    existing_links = load_links()
    existing_shop_ids = set()
    
    for link in existing_links:
        existing_shop_ids.add(link['shop_id'])
    
    # Upewnij się, że każdy shop_id ma konfigurację
    for shop_id in existing_shop_ids:
        config = shop_config.get_shop_config(shop_id)
        if shop_id not in shop_config.load_shop_configs():
            shop_config.save_shop_config(config)
    
    shops_list = shop_config.get_all_shops()
    
    # NOWE: Dodaj liczbę produktów dla każdego sklepu
    for shop in shops_list:
        shop_id = shop['shop_id']
        
        # Policz produkty w tym sklepie
        products_count = len([link for link in existing_links if link['shop_id'] == shop_id])
        shop['products_count'] = products_count
        
        # Dodaj informację czy ma wyszukiwanie
        shop['has_search'] = bool(shop.get('search_config', {}).get('search_url'))
    
    # Sortuj domyślnie według nazwy
    shops_list.sort(key=lambda x: x['name'].lower())
    
    return render_template('shops.html', shops=shops_list)

@shop_bp.route('/shop/<shop_id>')
def shop_detail(shop_id):
    """Szczegóły i edycja konfiguracji sklepu - POPRAWIONA WERSJA"""
    from utils.data_utils import load_links, load_products, load_prices
    
    shop = shop_config.get_shop_config(shop_id)
    
    # Pobierz produkty dla tego sklepu
    all_links = load_links()
    all_products = load_products()
    all_prices = load_prices()
    
    # Znajdź linki dla tego sklepu
    shop_links = [link for link in all_links if link['shop_id'] == shop_id]
    
    # Stwórz mapę produktów (id -> nazwa)
    products_map = {p['id']: p['name'] for p in all_products}
    
    # POPRAWKA: Znajdź najnowsze ceny dla każdego KONKRETNEGO LINKU (product_id + URL)
    latest_prices = {}
    for price in all_prices:
        if price['shop_id'] == shop_id:
            # KLUCZ: kombinacja product_id + URL zamiast tylko product_id
            key = f"{price['product_id']}|{price.get('url', '')}"
            if key not in latest_prices or price['created'] > latest_prices[key]['created']:
                latest_prices[key] = price
    
    # Połącz dane
    shop_products = []
    for link in shop_links:
        product_data = {
            'product_id': link['product_id'],
            'product_name': products_map.get(link['product_id'], 'Nieznany produkt'),
            'url': link['url'],
            'created': link['created'],
            'latest_price': None,
            'currency': None,
            'price_updated': None
        }
        
        # POPRAWKA: Szukaj ceny po kluczu product_id + URL
        price_key = f"{link['product_id']}|{link['url']}"
        if price_key in latest_prices:
            price_data = latest_prices[price_key]
            product_data['latest_price'] = price_data.get('price')
            product_data['currency'] = price_data.get('currency', 'PLN')
            product_data['price_updated'] = price_data.get('created')
        
        shop_products.append(product_data)
    
    # Sortuj według nazwy produktu
    shop_products.sort(key=lambda x: x['product_name'])
    
    # Dodaj liczbę produktów do shop
    shop['products_count'] = len(shop_products)
    
    return render_template('shop_detail.html', shop=shop, shop_products=shop_products)

@shop_bp.route('/shop/<shop_id>/edit', methods=['GET', 'POST'])
def edit_shop(shop_id):
    """Edycja konfiguracji sklepu"""
    if request.method == 'POST':
        # Pobierz selektory z formularza (jeden na linię)
        selectors_text = request.form['selectors'].strip()
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
        config['name'] = request.form['name'] or shop_id
        config['price_selectors'] = selectors
        config['delivery_free_from'] = float(request.form['delivery_free_from']) if request.form['delivery_free_from'] else None
        config['delivery_cost'] = float(request.form['delivery_cost']) if request.form['delivery_cost'] else None
        config['currency'] = request.form['currency'] or 'PLN'
        
        # Zapisz konfigurację wyszukiwania tylko jeśli jest URL
        if search_config.get('search_url'):
            config['search_config'] = search_config
        elif 'search_config' in config:
            # Zachowaj istniejącą konfigurację jeśli nie ma nowej
            pass
        
        shop_config.save_shop_config(config)
        flash(f'Zaktualizowano konfigurację sklepu {shop_id}')
        return redirect(url_for('shops.shop_detail', shop_id=shop_id))
    
    shop = shop_config.get_shop_config(shop_id)
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
            if link['shop_id'] == shop_id:
                products_in_shop.add(link['product_id'])
        
        # Znajdź produkty które NIE są w tym sklepie
        available_products = [p for p in all_products if p['id'] not in products_in_shop]
        
        return jsonify({
            'success': True,
            'shop_id': shop_id,
            'products': available_products,
            'total_available': len(available_products),
            'total_products': len(all_products)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@shop_bp.route('/shops/stats')
def shops_stats():
    """API endpoint - zwraca statystyki sklepów"""
    try:
        existing_links = load_links()
        shops_list = shop_config.get_all_shops()
        
        stats = {
            'total_shops': len(shops_list),
            'shops_with_products': 0,
            'shops_with_selectors': 0,
            'shops_with_search': 0,
            'total_products': len(existing_links),
            'shops_breakdown': []
        }
        
        for shop in shops_list:
            shop_id = shop['shop_id']
            products_count = len([link for link in existing_links if link['shop_id'] == shop_id])
            selectors_count = len(shop.get('price_selectors', []))
            has_search = bool(shop.get('search_config', {}).get('search_url'))
            
            if products_count > 0:
                stats['shops_with_products'] += 1
            if selectors_count > 0:
                stats['shops_with_selectors'] += 1
            if has_search:
                stats['shops_with_search'] += 1
            
            stats['shops_breakdown'].append({
                'shop_id': shop_id,
                'name': shop['name'],
                'products_count': products_count,
                'selectors_count': selectors_count,
                'has_search': has_search,
                'currency': shop.get('currency', 'PLN'),
                'delivery_configured': bool(shop.get('delivery_free_from') or shop.get('delivery_cost'))
            })
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})