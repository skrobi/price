"""
Routes związane z koszykami
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from utils.data_utils import load_products, get_latest_prices
from basket_manager import basket_manager
from shop_config import shop_config

basket_bp = Blueprint('baskets', __name__)

@basket_bp.route('/basket')
def basket():
    """Główna strona koszyków"""
    baskets = basket_manager.load_baskets()
    return render_template('basket.html', baskets=baskets)

@basket_bp.route('/basket/new', methods=['POST'])
def create_basket():
    """Tworzy nowy koszyk"""
    name = request.form.get('name', 'Nowy koszyk')
    
    optimization_settings = {
        'priority': request.form.get('priority', 'lowest_total_cost'),
        'max_shops': int(request.form.get('max_shops', 5)),
        'suggest_quantities': request.form.get('suggest_quantities') == 'on',
        'min_savings_threshold': float(request.form.get('min_savings_threshold', 5.0)),
        'max_quantity_multiplier': int(request.form.get('max_quantity_multiplier', 3)),
        'consider_free_shipping': request.form.get('consider_free_shipping') == 'on',
        'show_logs': request.form.get('show_logs') == 'on',
        # NOWE: Ustawienia zamienników
        'substitute_settings': {
            'allow_substitutes': request.form.get('allow_substitutes') == 'on',
            'max_price_increase_percent': float(request.form.get('max_price_increase_percent', 20.0)),
            'prefer_original': request.form.get('prefer_original') == 'on',
            'max_substitutes_per_product': int(request.form.get('max_substitutes_per_product', 3)),
            'show_substitute_reasons': request.form.get('show_substitute_reasons') == 'on'
        }
    }
    
    basket_id = basket_manager.create_new_basket(name, optimization_settings)
    flash(f'Utworzono nowy koszyk: {name}')
    return redirect(url_for('baskets.basket_detail', basket_id=basket_id))

@basket_bp.route('/basket/<basket_id>')
def basket_detail(basket_id):
    """Szczegóły konkretnego koszyka z najlepszymi cenami - NAPRAWIONA WERSJA"""
    print(f"\n=== DEBUG BASKET_DETAIL START ===")
    
    basket = basket_manager.get_basket(basket_id)
    if not basket:
        flash('Koszyk nie został znaleziony!')
        return redirect(url_for('baskets.basket'))
    
    products = load_products()
    latest_prices = get_latest_prices()
    print("DEBUG LATEST_PRICES:")
    for key, price_data in latest_prices.items():
        print(f"  {key}: price={repr(price_data.get('price'))}, type={type(price_data.get('price'))}")
    
    
    # Upewnij się że basket_items istnieje
    if 'basket_items' not in basket:
        basket['basket_items'] = {}
    
    # Import funkcji konwersji
    from utils.data_utils import convert_to_pln
    
    # Oblicz najlepsze ceny dla każdego produktu
    best_prices_data = {}
    total_estimated_cost = 0  # INICJALIZACJA SUMY
    
    print("--- ANALIZA PRODUKTÓW ---")
    for item in basket['basket_items'].values():
        product_id = item['product_id']
        quantity = item['requested_quantity']
        
        # Znajdź nazwę produktu
        for p in products:
            if p['id'] == product_id:
                item['product_name'] = p['name']
                break
        else:
            item['product_name'] = f'Produkt {product_id}'
        
        # Znajdź najlepszą cenę dla tego produktu
        product_prices = []
        for price_key, price_data in latest_prices.items():
            if price_data['product_id'] == product_id and price_data.get('price'):
                try:
                    price_pln = convert_to_pln(price_data['price'], price_data.get('currency', 'PLN'))
                    product_prices.append({
                        'price_pln': price_pln,
                        'price_original': price_data['price'],
                        'currency': price_data.get('currency', 'PLN'),
                        'shop_id': price_data['shop_id']
                    })
                except Exception as e:
                    print(f"BŁĄD konwersji dla produktu {product_id}: {e}")
                    continue
        
        if product_prices:
            # Sortuj po cenie PLN i weź najlepszą
            product_prices.sort(key=lambda x: x['price_pln'])
            best_price_info = product_prices[0]
            
            # WAŻNE: Upewnij się że price_pln to float
            price_pln = float(best_price_info['price_pln'])
            quantity = int(quantity)
            item_cost = price_pln * quantity
            
            best_prices_data[product_id] = {
                'price_pln': price_pln,
                'price_original': best_price_info['price_original'],
                'currency': best_price_info['currency'],
                'shop_id': best_price_info['shop_id']
            }
            
            # DODAJ DO SUMY
            total_estimated_cost += item_cost
            
            print(f"Produkt {product_id}: {price_pln} PLN × {quantity} = {item_cost} PLN (suma: {total_estimated_cost})")
            
        else:
            print(f"Produkt {product_id}: BRAK CEN")
            best_prices_data[product_id] = None
    
    print(f"FINALNA SUMA: {total_estimated_cost} PLN")
    print(f"=== DEBUG BASKET_DETAIL END ===\n")
    
    return render_template('basket_detail.html', 
                         basket=basket, 
                         latest_prices=latest_prices,
                         products=products,
                         best_prices_data=best_prices_data,
                         total_estimated_cost=total_estimated_cost)

@basket_bp.route('/basket/<basket_id>/settings', methods=['GET', 'POST'])
def basket_settings(basket_id):
    """Edycja ustawień koszyka - POPRAWIONA WERSJA Z WSZYSTKIMI USTAWIENIAMI"""
    basket = basket_manager.get_basket(basket_id)
    if not basket:
        flash('Koszyk nie został znaleziony!')
        return redirect(url_for('baskets.basket'))
    
    if request.method == 'POST':
        print(f"🔍 DEBUG BASKET_SETTINGS POST:")
        print(f"   basket_id: {basket_id}")
        print(f"   request.form: {dict(request.form)}")
        
        # WSZYSTKIE USTAWIENIA Z FORMULARZA
        optimization_settings = {
            'priority': request.form.get('priority', 'lowest_total_cost'),
            'max_shops': int(request.form.get('max_shops', 5)),
            'suggest_quantities': request.form.get('suggest_quantities') == 'on',
            'min_savings_threshold': float(request.form.get('min_savings_threshold', 5.0)),
            'max_quantity_multiplier': int(request.form.get('max_quantity_multiplier', 3)),
            'consider_free_shipping': request.form.get('consider_free_shipping') == 'on',
            'show_logs': request.form.get('show_logs') == 'on',
            
            # NOWE: max_combinations
            'max_combinations': int(request.form.get('max_combinations', 200000)),
            
            # NOWE: WSZYSTKIE USTAWIENIA ZAMIENNIKÓW
            'substitute_settings': {
                'allow_substitutes': request.form.get('allow_substitutes') == 'on',
                'max_price_increase_percent': float(request.form.get('max_price_increase_percent', 20.0)),
                'prefer_original': request.form.get('prefer_original') == 'on',
                'max_substitutes_per_product': int(request.form.get('max_substitutes_per_product', 3)),
                'show_substitute_reasons': request.form.get('show_substitute_reasons') == 'on'
            }
        }
        
        print(f"   optimization_settings utworzone: {optimization_settings}")
        
        name = request.form.get('name', basket['name'])
        print(f"   name: {name}")
        
        success = basket_manager.update_basket_settings(basket_id, optimization_settings, name)
        print(f"   success: {success}")
        
        if success:
            flash('Ustawienia koszyka zostały zapisane!')
        else:
            flash('Błąd podczas zapisywania ustawień.')
        
        return redirect(url_for('baskets.basket_detail', basket_id=basket_id))
    
    return render_template('basket_settings.html', basket=basket)

@basket_bp.route('/basket/<basket_id>/delete', methods=['POST'])
def delete_basket(basket_id):
    """Usuwa koszyk"""
    basket = basket_manager.get_basket(basket_id)
    if not basket:
        flash('Koszyk nie został znaleziony!')
        return redirect(url_for('baskets.basket'))
    
    success = basket_manager.delete_basket(basket_id)
    
    if success:
        flash(f'Koszyk "{basket["name"]}" został usunięty.')
    else:
        flash('Błąd podczas usuwania koszyka.')
    
    return redirect(url_for('baskets.basket'))

@basket_bp.route('/basket/<basket_id>/remove/<int:product_id>', methods=['POST'])
def remove_from_basket(basket_id, product_id):
    """Usuwa produkt z koszyka"""
    success = basket_manager.remove_item_from_basket(basket_id, product_id)
    
    if success:
        flash('Produkt został usunięty z koszyka.')
    else:
        flash('Błąd podczas usuwania produktu.')
    
    return redirect(url_for('baskets.basket_detail', basket_id=basket_id))

@basket_bp.route('/basket/<basket_id>/add/<int:product_id>', methods=['POST'])
def add_to_basket(basket_id, product_id):
    """Dodaje produkt do koszyka - Z DEBUGOWANIEM"""
    try:
        print(f"🔍 DEBUG ADD TO BASKET:")
        print(f"   basket_id: {basket_id}")
        print(f"   product_id: {product_id}")
        print(f"   request.form: {dict(request.form)}")
        
        quantity = int(request.form.get('quantity', 1))
        print(f"   quantity: {quantity}")
        
        # Sprawdź czy koszyk istnieje
        basket = basket_manager.get_basket(basket_id)
        if not basket:
            print(f"   ❌ BŁĄD: Koszyk nie istnieje!")
            flash('Koszyk nie został znaleziony!')
            return redirect(url_for('baskets.basket'))
        
        print(f"   ✅ Koszyk znaleziony: {basket['name']}")
        
        # Sprawdź produkty
        products = load_products()
        print(f"   📦 Załadowano {len(products)} produktów")
        
        product_name = 'Nieznany produkt'
        product_found = False
        for p in products:
            if p['id'] == product_id:
                product_name = p['name']
                product_found = True
                break
        
        print(f"   🔍 Produkt {product_id}: {'✅ znaleziony' if product_found else '❌ nie znaleziony'} - {product_name}")
        
        if not product_found:
            flash(f'Produkt o ID {product_id} nie został znaleziony!')
            return redirect(url_for('baskets.basket_detail', basket_id=basket_id))
        
        print(f"   🚀 Próba dodania do koszyka...")
        success = basket_manager.add_item_to_basket(basket_id, product_id, quantity, product_name)
        print(f"   📊 Wynik dodawania: {'✅ sukces' if success else '❌ błąd'}")
        
        if success:
            flash(f'Dodano {product_name} do koszyka ({quantity} szt.)')
            print(f"   ✅ Flash message ustawiony")
        else:
            flash('Błąd podczas dodawania do koszyka')
            print(f"   ❌ Flash error message ustawiony")
        
        print(f"   🔄 Przekierowanie do basket_detail...")
        return redirect(request.referrer or url_for('baskets.basket_detail', basket_id=basket_id))
        
    except Exception as e:
        print(f"💥 KRYTYCZNY BŁĄD w add_to_basket: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Błąd krytyczny: {str(e)}')
        return redirect(url_for('baskets.basket_detail', basket_id=basket_id))

@basket_bp.route('/basket/<basket_id>/update_quantity/<int:product_id>', methods=['POST'])
def update_quantity(basket_id, product_id):
    """Aktualizuje ilość produktu w koszyku"""
    try:
        print(f"🔍 DEBUG UPDATE QUANTITY:")
        print(f"   basket_id: {basket_id}")
        print(f"   product_id: {product_id}")
        
        data = request.get_json() if request.is_json else request.form
        action = data.get('action')  # 'increase', 'decrease', 'set'
        set_quantity = data.get('quantity')
        
        print(f"   action: {action}")
        print(f"   set_quantity: {set_quantity}")
        
        basket = basket_manager.get_basket(basket_id)
        if not basket:
            print(f"   ❌ Koszyk nie znaleziony")
            return jsonify({'success': False, 'error': 'Koszyk nie został znaleziony'})
        
        product_key = str(product_id)
        if product_key not in basket.get('basket_items', {}):
            print(f"   ❌ Produkt nie w koszyku")
            return jsonify({'success': False, 'error': 'Produkt nie znajduje się w koszyku'})
        
        current_quantity = basket['basket_items'][product_key]['requested_quantity']
        print(f"   current_quantity: {current_quantity}")
        
        # Oblicz nową ilość
        if action == 'increase':
            final_quantity = current_quantity + 1
        elif action == 'decrease':
            final_quantity = max(1, current_quantity - 1)  # Minimalna ilość to 1
        elif action == 'set' and set_quantity:
            final_quantity = max(1, int(set_quantity))
        else:
            print(f"   ❌ Nieprawidłowa akcja: {action}")
            return jsonify({'success': False, 'error': 'Nieprawidłowa akcja'})
        
        print(f"   final_quantity: {final_quantity}")
        
        # Aktualizuj ilość
        basket['basket_items'][product_key]['requested_quantity'] = final_quantity
        basket['basket_items'][product_key]['suggested_quantity'] = final_quantity
        basket['updated'] = datetime.now().isoformat()
        
        basket_manager.save_basket(basket)
        print(f"   ✅ Zapisano nową ilość")
        
        # WAŻNE: Zwróć poprawny JSON
        response_data = {
            'success': True,
            'new_quantity': final_quantity,
            'product_id': product_id,
            'action': action
        }
        
        print(f"   📤 Zwracam JSON: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"💥 BŁĄD w update_quantity: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@basket_bp.route('/basket/<basket_id>/optimize', methods=['POST'])
def optimize_basket(basket_id):
    """Uruchamia optymalizację koszyka"""
    products = load_products()
    latest_prices = get_latest_prices()
    shop_configs_data = shop_config.load_shop_configs()
    
    result = basket_manager.optimize_basket(
        basket_id, 
        products, 
        latest_prices, 
        shop_configs_data
    )
    
    if result['success']:
        flash('Koszyk został zoptymalizowany!')
        return render_template('optimization_results.html', result=result)
    else:
        flash(f'Błąd optymalizacji: {result["error"]}')
        return redirect(url_for('baskets.basket_detail', basket_id=basket_id))

@basket_bp.route('/add_to_basket_ajax', methods=['POST'])
def add_to_basket_ajax():
    """AJAX endpoint do dodawania produktów - Z DEBUGOWANIEM"""
    try:
        print(f"🔍 DEBUG AJAX ADD TO BASKET:")
        data = request.get_json()
        print(f"   data: {data}")
        
        basket_id = data.get('basket_id')
        product_id = int(data.get('product_id'))
        quantity = int(data.get('quantity', 1))
        
        print(f"   basket_id: {basket_id}")
        print(f"   product_id: {product_id}")
        print(f"   quantity: {quantity}")
        
        # Sprawdź czy koszyk istnieje
        basket = basket_manager.get_basket(basket_id)
        if not basket:
            print(f"   ❌ Koszyk nie istnieje")
            return jsonify({'success': False, 'error': 'Koszyk nie został znaleziony'})
        
        # Znajdź produkt
        products = load_products()
        product_name = 'Nieznany produkt'
        product_found = False
        for p in products:
            if p['id'] == product_id:
                product_name = p['name']
                product_found = True
                break
        
        if not product_found:
            print(f"   ❌ Produkt {product_id} nie znaleziony")
            return jsonify({'success': False, 'error': f'Produkt o ID {product_id} nie został znaleziony'})
        
        print(f"   📦 Nazwa produktu: {product_name}")
        
        success = basket_manager.add_item_to_basket(basket_id, product_id, quantity, product_name)
        print(f"   📊 Wynik: {'✅ sukces' if success else '❌ błąd'}")
        
        if success:
            basket = basket_manager.get_basket(basket_id)
            total_items = sum(item['requested_quantity'] for item in basket['basket_items'].values())
            
            print(f"   ✅ Zwracam sukces, total_items: {total_items}")
            
            return jsonify({
                'success': True,
                'basket_id': basket_id,
                'message': f'Dodano {product_name} do koszyka',
                'total_items': total_items
            })
        else:
            print(f"   ❌ Zwracam błąd")
            return jsonify({'success': False, 'error': 'Błąd podczas dodawania'})
            
    except Exception as e:
        print(f"💥 KRYTYCZNY BŁĄD w add_to_basket_ajax: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@basket_bp.route('/api/baskets', methods=['GET'])
def api_get_baskets():
    """API endpoint do pobierania listy koszyków"""
    try:
        baskets = basket_manager.load_baskets()
        baskets_list = list(baskets.values())
        return jsonify({
            'success': True,
            'baskets': baskets_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@basket_bp.route('/api/products', methods=['GET'])
def api_get_products_for_basket():
    """API endpoint do pobierania listy produktów dla koszyka"""
    try:
        from utils.data_utils import load_products
        products = load_products()
        return jsonify({
            'success': True,
            'products': products
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
        
# DODAJ TE FUNKCJE DO basket_routes.py

@basket_bp.route('/basket/<basket_id>/substitute_settings', methods=['POST'])
def update_substitute_settings(basket_id):
    """Aktualizuje ustawienia zamienników dla konkretnej pozycji w koszyku"""
    try:
        data = request.get_json()
        product_id = int(data.get('product_id'))
        allow_substitutes = data.get('allow_substitutes', True)
        max_price_increase = float(data.get('max_price_increase_percent', 20.0))
        
        success = basket_manager.update_item_substitute_settings(
            basket_id, 
            product_id, 
            allow_substitutes, 
            max_price_increase
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Ustawienia zamienników zostały zaktualizowane'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Nie udało się zaktualizować ustawień'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@basket_bp.route('/api/basket/<basket_id>/substitute_preview', methods=['POST'])
def preview_substitutes_for_basket(basket_id):
    """Podgląd potencjalnych zamienników dla wszystkich produktów w koszyku"""
    try:
        from substitute_manager import substitute_manager
        
        basket = basket_manager.get_basket(basket_id)
        if not basket:
            return jsonify({'success': False, 'error': 'Koszyk nie został znaleziony'})
        
        latest_prices = get_latest_prices()
        preview_results = {}
        
        for product_key, item in basket['basket_items'].items():
            product_id = item['product_id']
            allow_substitutes = item.get('substitute_settings', {}).get('allow_substitutes', True)
            max_price_increase = item.get('substitute_settings', {}).get('max_price_increase_percent', 20.0)
            
            if allow_substitutes:
                substitute_offers = substitute_manager.find_best_substitute_offers(
                    product_id, 
                    item['requested_quantity'], 
                    max_price_increase
                )
                preview_results[product_id] = substitute_offers
            else:
                preview_results[product_id] = []
        
        return jsonify({
            'success': True,
            'preview': preview_results
        })
        
    except ImportError:
        return jsonify({'success': False, 'error': 'Moduł zamienników niedostępny'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})