"""
Moduł obsługujący podstawowe zarządzanie produktami
"""
import json
from flask import jsonify, request, render_template, redirect, url_for, flash
from datetime import datetime
from utils.data_utils import load_products, save_product, load_links, load_prices, get_latest_prices, convert_to_pln

# Import modułów wyszukiwania
try:
    from product_finder import ProductFinder
    FINDER_AVAILABLE = True
except ImportError:
    FINDER_AVAILABLE = False

try:
    from shop_config import shop_config
    SHOP_CONFIG_AVAILABLE = True
except ImportError:
    SHOP_CONFIG_AVAILABLE = False

class ProductManager:
    """Klasa zarządzająca podstawowymi operacjami na produktach"""
    
    def list_products(self):
        """Lista wszystkich produktów"""
        products = load_products()
        
        # Dodaj informacje o linkach i cenach
        all_links = load_links()
        latest_prices = get_latest_prices()
        
        for product in products:
            # Liczba linków
            product_links = [link for link in all_links if link['product_id'] == product['id']]
            product['links_count'] = len(product_links)
            
            # Najlepsza cena
            product_prices = []
            for link in product_links:
                key = f"{product['id']}-{link['shop_id']}"
                if key in latest_prices:
                    price_data = latest_prices[key]
                    price_pln = convert_to_pln(price_data['price'], price_data.get('currency', 'PLN'))
                    product_prices.append(price_pln)
            
            if product_prices:
                product['min_price'] = min(product_prices)
                product['max_price'] = max(product_prices)
                product['avg_price'] = sum(product_prices) / len(product_prices)
            else:
                product['min_price'] = None
                product['max_price'] = None
                product['avg_price'] = None
        
        # Sortuj produkty (najnowsze pierwsze)
        products.sort(key=lambda x: x.get('created', ''), reverse=True)
        
        return render_template('products.html', products=products)
    
    def add_product(self):
        """Dodaj nowy produkt"""
        if request.method == 'POST':
            name = request.form['name'].strip()
            ean = request.form.get('ean', '').strip()
            
            if not name:
                flash('Nazwa produktu jest wymagana!')
                return render_template('add_product.html')
            
            # Sprawdź czy produkt już istnieje
            products = load_products()
            for product in products:
                if product['name'].lower() == name.lower():
                    flash('Produkt o takiej nazwie już istnieje!')
                    return render_template('add_product.html')
            
            # Stwórz nowy produkt
            new_id = max([p['id'] for p in products], default=0) + 1
            
            new_product = {
                'id': new_id,
                'name': name,
                'ean': ean,
                'created': datetime.now().isoformat()
            }
            
            save_product(new_product)
            flash(f'Produkt "{name}" został dodany!')
            return redirect(url_for('products.product_detail', product_id=new_id))
        
        return render_template('add_product.html')
    
    def add_product_url(self):
        """Dodaj produkt z URL"""
        if request.method == 'POST':
            url = request.form['url'].strip()
            if not url:
                flash('URL jest wymagany!')
                return render_template('add_product_url.html')
            
            # Wyciągnij shop_id z URL
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc.lower().replace('www.', '')
                shop_id = domain.split('.')[0]
            except:
                shop_id = 'unknown'
            
            flash(f'Funkcja dodawania produktu z URL jest w rozwoju. Sklep: {shop_id}')
            return redirect(url_for('products.products'))
        
        return render_template('add_product_url.html')
    
    def product_detail(self, product_id):
        """Szczegóły produktu - POPRAWIONA WERSJA"""
        products = load_products()
        product = None
        for p in products:
            if p['id'] == product_id:
                product = p
                break
        
        if not product:
            flash('Produkt nie został znaleziony!')
            return redirect(url_for('products.products'))
        
        # Linki dla tego produktu
        all_links = load_links()
        product_links = [link for link in all_links if link['product_id'] == product_id]
        
        # POPRAWKA: Ceny dla każdego konkretnego linku (product_id + URL)
        all_prices = load_prices()
        for link in product_links:
            # Znajdź najnowszą cenę dla konkretnego URL
            link_prices = [p for p in all_prices 
                          if p['product_id'] == product_id 
                          and p['shop_id'] == link['shop_id']
                          and p.get('url', '') == link['url']]  # DODANE: porównanie URL
            
            if link_prices:
                # Sortuj po dacie i weź najnowszą
                link_prices.sort(key=lambda x: x['created'], reverse=True)
                latest_price = link_prices[0]
                
                link['price'] = latest_price['price']
                link['currency'] = latest_price.get('currency', 'PLN')
                link['price_pln'] = convert_to_pln(latest_price['price'], latest_price.get('currency', 'PLN'))
                link['price_updated'] = latest_price['created'][:16]
            else:
                link['price'] = None
        
        return render_template('product_detail.html', product=product, links=product_links)
    
    def update_product(self):
        """API - aktualizuje dane produktu"""
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            name = data.get('name', '').strip()
            ean = data.get('ean', '').strip()
            
            if not name:
                return jsonify({'success': False, 'error': 'Nazwa produktu jest wymagana'})
            
            # Sprawdź czy produkt istnieje
            products = load_products()
            product_found = False
            for i, product in enumerate(products):
                if product['id'] == product_id:
                    products[i]['name'] = name
                    products[i]['ean'] = ean
                    products[i]['updated'] = datetime.now().isoformat()
                    product_found = True
                    break
            
            if not product_found:
                return jsonify({'success': False, 'error': 'Produkt nie został znaleziony'})
            
            # Sprawdź czy nazwa nie jest duplikatem
            for product in products:
                if product['id'] != product_id and product['name'].lower() == name.lower():
                    return jsonify({'success': False, 'error': 'Produkt o takiej nazwie już istnieje'})
            
            # Zapisz zmiany
            with open('data/products.txt', 'w', encoding='utf-8') as f:
                for product in products:
                    f.write(json.dumps(product, ensure_ascii=False) + '\n')
            
            return jsonify({'success': True, 'message': 'Produkt został zaktualizowany'})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    def delete_product(self):
        """API - usuwa produkt"""
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            
            # Usuń produkt
            products = load_products()
            remaining_products = [p for p in products if p['id'] != product_id]
            
            with open('data/products.txt', 'w', encoding='utf-8') as f:
                for product in remaining_products:
                    f.write(json.dumps(product, ensure_ascii=False) + '\n')
            
            # Usuń powiązane linki
            links = load_links()
            remaining_links = [l for l in links if l['product_id'] != product_id]
            
            with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                for link in remaining_links:
                    f.write(json.dumps(link, ensure_ascii=False) + '\n')
            
            # Usuń powiązane ceny
            prices = load_prices()
            remaining_prices = [p for p in prices if p['product_id'] != product_id]
            
            with open('data/prices.txt', 'w', encoding='utf-8') as f:
                for price in remaining_prices:
                    f.write(json.dumps(price, ensure_ascii=False) + '\n')
            
            return jsonify({'success': True, 'message': 'Produkt został usunięty'})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    def find_in_shops(self):
        """API - wyszukuje produkt w sklepach"""
        if not FINDER_AVAILABLE:
            return jsonify({'success': False, 'error': 'Wyszukiwarka nie jest dostępna'})
        
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            
            # Znajdź produkt
            products = load_products()
            product = None
            for p in products:
                if p['id'] == product_id:
                    product = p
                    break
            
            if not product:
                return jsonify({'success': False, 'error': 'Produkt nie został znaleziony'})
            
            # Pobierz wszystkie sklepy z konfiguracją wyszukiwania
            if not SHOP_CONFIG_AVAILABLE:
                return jsonify({'success': False, 'error': 'Konfiguracja sklepów nie jest dostępna'})
            
            from shop_config import shop_config
            all_shops = shop_config.get_all_shops()
            
            results = []
            for shop in all_shops:
                search_config = shop.get('search_config')
                if search_config and search_config.get('search_url'):
                    try:
                        from product_finder import product_finder
                        debug_info = []
                        
                        # Wyszukaj produkt w tym sklepie
                        search_result = product_finder.search_product(
                            search_config,
                            product['name'],
                            product.get('ean'),
                            debug_info
                        )
                        
                        if search_result.get('success') and search_result.get('results'):
                            results.append({
                                'shop': shop,
                                'success': True,
                                'results': search_result['results']
                            })
                        else:
                            results.append({
                                'shop': shop,
                                'success': False,
                                'error': search_result.get('error', 'Nie znaleziono')
                            })
                            
                    except Exception as e:
                        results.append({
                            'shop': shop,
                            'success': False,
                            'error': str(e)
                        })
            
            return jsonify({'success': True, 'results': results})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    def get_available_shops(self):
        """API - zwraca dostępne sklepy"""
        if not SHOP_CONFIG_AVAILABLE:
            return jsonify({'success': False, 'error': 'Konfiguracja sklepów nie jest dostępna'})
        
        try:
            shops = []
            for shop_id, config in shop_config.items():
                if config.get('search_url'):
                    shops.append({
                        'shop_id': shop_id,
                        'name': config.get('name', shop_id),
                        'search_url': config['search_url']
                    })
            
            return jsonify({'success': True, 'shops': shops})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    def search_in_single_shop(self):
        """API - wyszukuje w pojedynczym sklepie"""
        if not FINDER_AVAILABLE:
            return jsonify({'success': False, 'error': 'Wyszukiwarka nie jest dostępna'})
        
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            shop_id = data.get('shop_id')
            
            # Znajdź produkt
            products = load_products()
            product = None
            for p in products:
                if p['id'] == product_id:
                    product = p
                    break
            
            if not product:
                return jsonify({'success': False, 'error': 'Produkt nie został znaleziony'})
            
            # Wyszukaj w konkretnym sklepie
            finder = ProductFinder()
            results = finder.search_in_shop(shop_id, product['name'])
            
            return jsonify({'success': True, 'results': results})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    def find_missing_for_product(self, product_id):
        """API - znajduje sklepy gdzie nie ma tego produktu"""
        if not SHOP_CONFIG_AVAILABLE:
            return jsonify({'success': False, 'error': 'Konfiguracja sklepów nie jest dostępna'})
        
        try:
            products = load_products()
            product = None
            for p in products:
                if p['id'] == product_id:
                    product = p
                    break
            
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
            existing_shops = []
            
            for shop in all_shops:
                if shop.get('search_config') and shop['search_config'].get('search_url'):
                    if shop['shop_id'] not in shops_with_product:
                        available_shops.append(shop)
                    else:
                        existing_shops.append(shop['shop_id'])
            
            return jsonify({
                'success': True,
                'available_shops': available_shops,
                'existing_shops': existing_shops,
                'product_name': product['name']
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    def search_product_in_shop(self):
        """API - wyszukuje produkt w konkretnym sklepie"""
        if not FINDER_AVAILABLE:
            return jsonify({'success': False, 'error': 'Wyszukiwarka nie jest dostępna'})
        
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            shop_id = data.get('shop_id')
            
            # Pobierz dane produktu
            products = load_products()
            product = None
            for p in products:
                if p['id'] == product_id:
                    product = p
                    break
            
            if not product:
                return jsonify({'success': False, 'error': 'Produkt nie znaleziony'})
            
            # Wyszukaj w sklepie
            finder = ProductFinder()
            results = finder.search_product_in_shop(
                shop_id=shop_id,
                product_name=product['name'],
                ean=product.get('ean')
            )
            
            return jsonify({
                'success': True,
                'results': results,
                'shop_id': shop_id,
                'product_name': product['name']
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})