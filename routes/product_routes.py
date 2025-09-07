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
    """Dodaj nowy produkt"""
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

# API Endpoints
@product_bp.route('/update_product', methods=['POST'])
def update_product():
    """API - aktualizuje dane produktu"""
    return product_manager.update_product()

@product_bp.route('/delete_product', methods=['POST'])
def delete_product():
    """API - usuwa produkt"""
    return product_manager.delete_product()

@product_bp.route('/update_product_link', methods=['POST'])
def update_product_link():
    """API - aktualizuje link produktu"""
    return links_manager.update_product_link()

@product_bp.route('/delete_product_link', methods=['POST'])
def delete_product_link():
    """API - usuwa link produktu"""
    return links_manager.delete_product_link()

@product_bp.route('/fetch_price_for_link', methods=['POST'])
def fetch_price_for_link():
    """API - pobiera cenę dla konkretnego linku"""
    return pricing_manager.fetch_price_for_link()

@product_bp.route('/add_manual_price_for_link', methods=['POST'])
def add_manual_price_for_link():
    """API - dodaje ręczną cenę dla linku"""
    return pricing_manager.add_manual_price_for_link()

@product_bp.route('/add_found_link', methods=['POST'])
def add_found_link():
    """API - dodaje link znaleziony przez wyszukiwanie"""
    return links_manager.add_found_link()

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

# ENDPOINTY DLA ZAMIENNIKÓW
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
        from utils.data_utils import load_products
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

@product_bp.route('/api/substitutes/groups/<group_id>', methods=['DELETE'])
def delete_substitute_group(group_id):
    """API - usuwa grupę zamienników"""
    try:
        from substitute_manager import substitute_manager
        success = substitute_manager.delete_substitute_group(group_id)
        if success:
            return jsonify({'success': True, 'message': 'Grupa została usunięta'})
        else:
            return jsonify({'success': False, 'error': 'Grupa nie została znaleziona'})
        
    except ImportError:
        return jsonify({'success': False, 'error': 'Moduł zamienników niedostępny'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@product_bp.route('/api/products/search')
def search_products_api():
    """API - wyszukuje produkty po nazwie (dla tworzenia grup zamienników)"""
    try:
        query = request.args.get('q', '').strip()
        
        if len(query) < 2:
            return jsonify({'success': True, 'products': []})
        
        # Proste wyszukiwanie po nazwie
        from utils.data_utils import load_products
        products = load_products()
        products = [p for p in products if query.lower() in p['name'].lower()][:20]
        
        return jsonify({'success': True, 'products': products})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})