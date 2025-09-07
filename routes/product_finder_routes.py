"""
Routes dla wyszukiwania produktów
"""
from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from utils.data_utils import load_products, load_links, save_link
from shop_config import shop_config
from product_finder import product_finder

finder_bp = Blueprint('finder', __name__)

@finder_bp.route('/find_products')
def find_products_page():
    """Strona główna wyszukiwania produktów"""
    # Pobierz tylko sklepy które mają skonfigurowane wyszukiwanie
    all_shops = shop_config.get_all_shops()
    shops_with_search = []
    
    for shop in all_shops:
        if shop.get('search_config') and shop['search_config'].get('search_url'):
            shops_with_search.append(shop)
    
    return render_template('find_products.html', shops_with_search=shops_with_search)

@finder_bp.route('/find_products/<shop_id>')
def get_missing_products(shop_id):
    """API - zwraca produkty których brakuje w sklepie"""
    try:
        products = load_products()
        links = load_links()
        
        # Znajdź produkty które nie mają linku w tym sklepie
        products_with_shop = set()
        for link in links:
            if link['shop_id'] == shop_id:
                products_with_shop.add(link['product_id'])
        
        missing_products = [p for p in products if p['id'] not in products_with_shop]
        
        return jsonify({
            'success': True,
            'missing_products': missing_products,
            'total_products': len(products),
            'missing_count': len(missing_products)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@finder_bp.route('/search_product', methods=['POST'])
def search_product():
    """API - wyszukuje konkretny produkt w sklepie"""
    try:
        data = request.get_json()
        shop_id = data.get('shop_id')
        product_name = data.get('product_name')
        ean = data.get('ean')
        
        if not shop_id or not product_name:
            return jsonify({'success': False, 'error': 'Brakuje parametrów'})
        
        # Pobierz konfigurację sklepu
        shop = shop_config.get_shop_config(shop_id)
        search_config = shop.get('search_config')
        
        if not search_config or not search_config.get('search_url'):
            return jsonify({'success': False, 'error': 'Sklep nie ma skonfigurowanego wyszukiwania'})
        
        # Wykonaj wyszukiwanie
        debug_info = []
        result = product_finder.search_product(
            search_config, 
            product_name, 
            ean, 
            debug_info
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@finder_bp.route('/test_shop_search', methods=['POST'])
def test_shop_search():
    """API - testuje wyszukiwanie w sklepie"""
    try:
        data = request.get_json()
        shop_id = data.get('shop_id')
        query = data.get('query', 'test')
        
        if not shop_id:
            return jsonify({'success': False, 'error': 'Brakuje shop_id'})
        
        # Pobierz konfigurację sklepu
        shop = shop_config.get_shop_config(shop_id)
        search_config = shop.get('search_config')
        
        if not search_config or not search_config.get('search_url'):
            return jsonify({'success': False, 'error': 'Sklep nie ma skonfigurowanego wyszukiwania'})
        
        # Wykonaj testowe wyszukiwanie
        debug_info = []
        result = product_finder.search_product(
            search_config, 
            query, 
            None,  # bez EAN
            debug_info
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@finder_bp.route('/add_found_link', methods=['POST'])
def add_found_link():
    """API - dodaje znaleziony link do produktu"""
    try:
        data = request.get_json()
        product_id = int(data.get('product_id'))
        shop_id = data.get('shop_id')
        url = data.get('url')
        title = data.get('title', '')
        
        if not all([product_id, shop_id, url]):
            return jsonify({'success': False, 'error': 'Brakuje parametrów'})
        
        # Sprawdź czy link już nie istnieje
        existing_links = load_links()
        for link in existing_links:
            if link['product_id'] == product_id and link['shop_id'] == shop_id:
                return jsonify({'success': False, 'error': 'Link już istnieje'})
            if link['url'] == url:
                return jsonify({'success': False, 'error': 'Ten URL jest już przypisany do innego produktu'})
        
        # Dodaj nowy link
        link_data = {
            'product_id': product_id,
            'shop_id': shop_id,
            'url': url,
            'created': datetime.now().isoformat(),
            'found_by_search': True,
            'original_title': title
        }
        
        save_link(link_data)
        
        return jsonify({
            'success': True,
            'message': f'Dodano link do sklepu {shop_id}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@finder_bp.route('/product/<int:product_id>/find_missing')
def find_missing_for_product(product_id):
    """Znajdź konkretny produkt w sklepach gdzie go nie ma"""
    try:
        products = load_products()
        product = next((p for p in products if p['id'] == product_id), None)
        
        if not product:
            return jsonify({'success': False, 'error': 'Produkt nie znaleziony'})
        
        links = load_links()
        all_shops = shop_config.get_all_shops()
        
        # Znajdź sklepy które mają wyszukiwanie ale nie mają tego produktu
        shops_with_product = set()
        for link in links:
            if link['product_id'] == product_id:
                shops_with_product.add(link['shop_id'])
        
        available_shops = []
        for shop in all_shops:
            if (shop['shop_id'] not in shops_with_product and 
                shop.get('search_config') and 
                shop['search_config'].get('search_url')):
                available_shops.append(shop)
        
        return jsonify({
            'success': True,
            'product': product,
            'available_shops': available_shops,
            'existing_shops': list(shops_with_product)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@finder_bp.route('/search_product_in_shop', methods=['POST'])
def search_product_in_shop():
    """Wyszukaj konkretny produkt w konkretnym sklepie"""
    try:
        data = request.get_json()
        product_id = int(data.get('product_id'))
        shop_id = data.get('shop_id')
        
        # Pobierz dane produktu
        products = load_products()
        product = next((p for p in products if p['id'] == product_id), None)
        
        if not product:
            return jsonify({'success': False, 'error': 'Produkt nie znaleziony'})
        
        # Pobierz konfigurację sklepu
        shop = shop_config.get_shop_config(shop_id)
        search_config = shop.get('search_config')
        
        if not search_config or not search_config.get('search_url'):
            return jsonify({'success': False, 'error': 'Sklep nie ma skonfigurowanego wyszukiwania'})
        
        # Wykonaj wyszukiwanie
        debug_info = []
        result = product_finder.search_product(
            search_config, 
            product['name'], 
            product.get('ean'),
            debug_info
        )
        
        # Dodaj informacje o produkcie i sklepie
        if result['success']:
            result['product'] = product
            result['shop'] = shop
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@finder_bp.route('/bulk_search/<shop_id>')
def bulk_search_missing_products(shop_id):
    """Masowe wyszukiwanie wszystkich brakujących produktów w sklepie"""
    try:
        # Pobierz konfigurację sklepu
        shop = shop_config.get_shop_config(shop_id)
        search_config = shop.get('search_config')
        
        if not search_config or not search_config.get('search_url'):
            return jsonify({'success': False, 'error': 'Sklep nie ma skonfigurowanego wyszukiwania'})
        
        # Znajdź brakujące produkty
        products = load_products()
        links = load_links()
        
        products_with_shop = set()
        for link in links:
            if link['shop_id'] == shop_id:
                products_with_shop.add(link['product_id'])
        
        missing_products = [p for p in products if p['id'] not in products_with_shop]
        
        if not missing_products:
            return jsonify({
                'success': True,
                'message': 'Wszystkie produkty są już dodane w tym sklepie',
                'results': []
            })
        
        # Wyszukaj każdy brakujący produkt
        results = []
        for product in missing_products:
            debug_info = []
            search_result = product_finder.search_product(
                search_config,
                product['name'],
                product.get('ean'),
                debug_info
            )
            
            results.append({
                'product': product,
                'search_result': search_result,
                'debug': debug_info
            })
        
        return jsonify({
            'success': True,
            'shop': shop,
            'total_searched': len(missing_products),
            'results': results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})