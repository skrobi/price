"""
Product Management - zarządzanie produktami - NAPRAWIONY
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from utils.data_utils import load_products, save_product, load_links, get_latest_prices
import logging

logger = logging.getLogger(__name__)

class ProductManager:
    """Manager dla operacji na produktach"""
    
    def list_products(self):
        """Lista wszystkich produktów z cenami - NAPRAWIONA"""
        try:
            products = load_products()
            links = load_links()
            latest_prices = get_latest_prices()
            
            # POPRAWKA: Filtruj tylko prawidłowe produkty
            products = [p for p in products if isinstance(p, dict) and 'id' in p]
            
            # Dodaj informacje o cenach do produktów
            for product in products:
                product_prices = []
                for price_key, price_data in latest_prices.items():
                    if isinstance(price_data, dict) and price_data.get('product_id') == product['id']:
                        try:
                            # POPRAWKA: Bezpieczna konwersja ceny
                            price_val = float(price_data.get('price', 0))
                            if price_val > 0:  # Tylko dodatnie ceny
                                product_prices.append(price_val)
                        except (ValueError, TypeError):
                            continue
                
                # POPRAWKA: Bezpieczne obliczenie min/max cen
                if product_prices:
                    product['min_price'] = min(product_prices)
                    product['max_price'] = max(product_prices)
                    product['price_count'] = len(product_prices)
                else:
                    product['min_price'] = None
                    product['max_price'] = None
                    product['price_count'] = 0
                
                # Dodaj informacje o linkach
                product_links = [l for l in links 
                               if isinstance(l, dict) and l.get('product_id') == product['id']]
                product['link_count'] = len(product_links)
            
            return render_template('products.html', products=products, links=links)
            
        except Exception as e:
            logger.error(f"Error in list_products: {e}")
            flash(f'Błąd ładowania produktów: {str(e)}')
            return render_template('products.html', products=[], links=[])
    
    def add_product(self):
        """Formularz dodawania produktu ręcznie"""
        if request.method == 'GET':
            return render_template('add_product.html')
        
        try:
            name = request.form.get('name', '').strip()
            ean = request.form.get('ean', '').strip()
            
            if not name:
                flash('Nazwa produktu jest wymagana')
                return render_template('add_product.html')
            
            # Sprawdź czy produkt już istnieje
            products = load_products()
            for product in products:
                if isinstance(product, dict) and product.get('name', '').lower() == name.lower():
                    flash('Produkt o tej nazwie już istnieje')
                    return render_template('add_product.html')
            
            # Utwórz nowy produkt
            new_id = max([p.get('id', 0) for p in products if isinstance(p, dict)], default=0) + 1
            
            product_data = {
                'id': new_id,
                'name': name,
                'ean': ean,
                'created': datetime.now().isoformat(),
                'source': 'manual'
            }
            
            # Zapisz produkt
            try:
                # POPRAWKA: Sprawdź czy sync jest dostępny
                try:
                    from sync.sync_integration import save_product_sync
                    result = save_product_sync(product_data)
                    
                    if result.get('success'):
                        synced_msg = " (zsynchronizowany)" if result.get('synced') else " (lokalnie)"
                        flash(f'Produkt "{name}" został dodany{synced_msg}')
                    else:
                        raise Exception(result.get('error', 'Błąd zapisu'))
                        
                except (ImportError, AttributeError):
                    # Fallback do standardowego zapisu
                    save_product(product_data)
                    flash(f'Produkt "{name}" został dodany')
                
                return redirect(url_for('products.product_detail', product_id=new_id))
                
            except Exception as e:
                logger.error(f"Error saving product: {e}")
                # Spróbuj zapisać standardowo
                save_product(product_data)
                flash(f'Produkt "{name}" został dodany (bez synchronizacji)')
                return redirect(url_for('products.product_detail', product_id=new_id))
            
        except Exception as e:
            logger.error(f"Error in add_product: {e}")
            flash(f'Błąd podczas dodawania produktu: {str(e)}')
            return render_template('add_product.html')
    
    def add_product_url(self):
        """Dodaj produkt z URL - UPROSZCZONA WERSJA"""
        if request.method == 'GET':
            return render_template('add_product_url.html')
        
        try:
            name = request.form.get('name', '').strip()
            url = request.form.get('url', '').strip()
            
            # Walidacja - nazwa jest wymagana
            if not name:
                flash('Nazwa produktu jest wymagana')
                return render_template('add_product_url.html')
            
            if not url:
                flash('URL jest wymagany')
                return render_template('add_product_url.html')
            
            # Walidacja URL
            if not (url.startswith('http://') or url.startswith('https://')):
                flash('URL musi zaczynać się od http:// lub https://')
                return render_template('add_product_url.html')
            
            # Identyfikuj sklep z URL (bez scrapingu)
            from urllib.parse import urlparse
            
            parsed = urlparse(url.lower())
            domain = parsed.netloc.replace('www.', '')
            
            # Mapowanie domen na sklepy
            shop_mappings = {
                'allegro.pl': ('Allegro', 'allegro'),
                'amazon.pl': ('Amazon', 'amazon'),
                'amazon.com': ('Amazon', 'amazon'),
                'ceneo.pl': ('Ceneo', 'ceneo'),
                'morele.net': ('Morele', 'morele'),
                'x-kom.pl': ('X-kom', 'xkom'),
                'mediamarkt.pl': ('MediaMarkt', 'mediamarkt'),
                'doz.pl': ('DOZ', 'doz'),
                'rosa24.pl': ('Rosa24', 'rosa24')
            }
            
            shop_name = None
            shop_id = None
            
            for pattern, (name_val, id_val) in shop_mappings.items():
                if pattern in domain:
                    shop_name = name_val
                    shop_id = id_val
                    break
            
            if not shop_name:
                shop_name = domain.title()
                shop_id = domain.replace('.', '_')
            
            # Sprawdź czy produkt już istnieje
            products = load_products()
            for product in products:
                if isinstance(product, dict) and product.get('name', '').lower() == name.lower():
                    flash(f'Produkt "{name}" już istnieje w bazie')
                    return redirect(url_for('products.product_detail', product_id=product['id']))
            
            # Utwórz nowy produkt
            new_id = max([p.get('id', 0) for p in products if isinstance(p, dict)], default=0) + 1
            
            product_data = {
                'id': new_id,
                'name': name,  # Używamy nazwy z formularza
                'ean': '',
                'created': datetime.now().isoformat(),
                'user_id': 'user',
                'source': 'manual_url'
            }
            
            # Zapisz produkt
            try:
                from sync.sync_integration import save_product_api_first
                result = save_product_api_first(product_data)
                
                if result.get('synced'):
                    flash(f'Produkt "{name}" został dodany i zsynchronizowany')
                else:
                    flash(f'Produkt "{name}" został dodany lokalnie')
                    
            except ImportError:
                save_product(product_data)
                flash(f'Produkt "{name}" został dodany')
            
            # Dodaj link do sklepu
            link_data = {
                'product_id': new_id,
                'shop_id': shop_id,
                'url': url,
                'created': datetime.now().isoformat()
            }
            
            try:
                from sync.sync_integration import save_link_api_first
                save_link_api_first(link_data)
            except ImportError:
                from utils.data_utils import save_link
                save_link(link_data)
            
            flash(f'Link do {shop_name} został dodany')
            return redirect(url_for('products.product_detail', product_id=new_id))
            
        except Exception as e:
            logger.error(f"Error in add_product_url: {e}")
            flash(f'Błąd podczas dodawania produktu: {str(e)}')
            return render_template('add_product_url.html')
    
    def product_detail(self, product_id):
        """Szczegóły produktu - Z PEŁNYM DEBUGOWANIEM"""
        #print(f"\n🔍 DEBUG PRODUCT_DETAIL START - product_id: {product_id}")
        
        try:
            # KROK 1: Załaduj produkty
            #print("📦 KROK 1: Ładowanie produktów...")
            products = load_products()
            #print(f"   ✅ Załadowano {len(products)} produktów")
            #print(f"   📋 Typy produktów: {[type(p) for p in products[:3]]}")
            
            # KROK 2: Znajdź konkretny produkt
            #print(f"🔎 KROK 2: Szukanie produktu ID {product_id}...")
            product = None
            for i, p in enumerate(products):
                #print(f"   Produkt {i}: typ={type(p)}, dict={isinstance(p, dict)}")
                if isinstance(p, dict):
                    p_id = p.get('id')
                    #print(f"     ID: {p_id} (typ: {type(p_id)})")
                    if p_id == product_id:
                        product = p
                        #print(f"   ✅ ZNALEZIONO! {p.get('name', 'Bez nazwy')}")
                        break
            
            if not product:
                print("   ❌ PRODUKT NIE ZNALEZIONY!")
                available_ids = [p.get('id') for p in products if isinstance(p, dict)]
                #print(f"   📋 Dostępne ID: {available_ids}")
                flash('Produkt nie został znaleziony')
                return redirect(url_for('products.products'))
            
            # KROK 3: Załaduj linki
            print("🔗 KROK 3: Ładowanie linków...")
            links = load_links()
            #print(f"   ✅ Załadowano {len(links)} linków")
            
            product_links = []
            for link in links:
                if isinstance(link, dict) and link.get('product_id') == product_id:
                    product_links.append(link)
                    #print(f"   🔗 Link: {link.get('shop_id')} -> {link.get('url', '')[:50]}...")
            
            #print(f"   📊 Znaleziono {len(product_links)} linków dla produktu")
            
            # KROK 4: Załaduj ceny
            print("💰 KROK 4: Ładowanie cen...")
            latest_prices = get_latest_prices()
            #print(f"   ✅ Załadowano {len(latest_prices)} cen")
            #print(f"   📋 Przykładowe klucze cen: {list(latest_prices.keys())[:5]}")
            
            # KROK 5: Dodaj ceny do linków
            print("🔄 KROK 5: Łączenie cen z linkami...")
            for i, link in enumerate(product_links):
                #print(f"   🔗 Link {i+1}: {link.get('shop_id')}")
                
                # Resetuj ceny
                link['price'] = None
                link['price_pln'] = None
                link['currency'] = None
                link['price_updated'] = None
                
                # Szukaj ceny dla tego linku
                found_price = False
                for price_key, price_data in latest_prices.items():
                    if not isinstance(price_data, dict):
                        continue
                        
                    price_product_id = price_data.get('product_id')
                    price_shop_id = price_data.get('shop_id')
                    
                    if price_product_id == product_id and price_shop_id == link.get('shop_id'):
                        #print(f"     ✅ ZNALEZIONO CENĘ! {price_data.get('price')} {price_data.get('currency', 'PLN')}")
                        found_price = True
                        
                        try:
                            # Ustaw ceny
                            link['price'] = float(price_data.get('price', 0))
                            link['price_pln'] = float(price_data.get('price_pln', price_data.get('price', 0)))
                            link['currency'] = price_data.get('currency', 'PLN')
                            
                            # BEZPIECZNE formatowanie daty
                            created_date = price_data.get('created', '')
                            #print(f"     📅 Data: '{created_date}' (typ: {type(created_date)})")
                            
                            if created_date and isinstance(created_date, str):
                                try:
                                    if 'T' in created_date:
                                        # Format ISO: 2024-01-15T10:30:45
                                        date_part = created_date.split('T')[0]
                                        time_part = created_date.split('T')[1][:8]
                                        link['price_updated'] = f"{date_part} {time_part}"
                                        #print(f"     📅 Sformatowana data: {link['price_updated']}")
                                    elif len(created_date) >= 16:
                                        link['price_updated'] = created_date[:16]
                                        #print(f"     📅 Obcięta data: {link['price_updated']}")
                                    else:
                                        link['price_updated'] = created_date
                                        #print(f"     📅 Oryginalna data: {link['price_updated']}")
                                except Exception as date_error:
                                    #print(f"     ❌ BŁĄD formatowania daty: {date_error}")
                                    link['price_updated'] = str(created_date) or 'Błąd daty'
                            else:
                                link['price_updated'] = 'Brak daty'
                                #print(f"     📅 Brak daty lub nieprawidłowy typ")
                                
                        except (ValueError, TypeError) as e:
                            print(f"     ❌ BŁĄD przetwarzania ceny: {e}")
                            pass
                        break
                
                if not found_price:
                    print(f"     ❌ Brak ceny dla {link.get('shop_id')}")
            
            # KROK 6: Renderuj template
            print("🎨 KROK 6: Renderowanie template...")
            print(f"   📦 Produkt: {product.get('name', 'Bez nazwy')}")
            print(f"   🔗 Linki: {len(product_links)}")
            
            # SPRAWDŹ czy template istnieje
            try:
                return render_template('product_detail.html', product=product, links=product_links)
            except Exception as template_error:
                print(f"❌ BŁĄD TEMPLATE: {template_error}")
                # Fallback - pokaż surowe dane
                return f"""
                <h1>DEBUG: Produkt {product_id}</h1>
                <p>Nazwa: {product.get('name', 'Brak')}</p>
                <p>EAN: {product.get('ean', 'Brak')}</p>
                <p>Linków: {len(product_links)}</p>
                <pre>{product_links}</pre>
                """
            
        except Exception as e:
            print(f"💥 KRYTYCZNY BŁĄD w product_detail: {str(e)}")
            import traceback
            traceback.print_exc()
            
            flash(f'Błąd ładowania produktu: {str(e)}')
            return redirect(url_for('products.products'))
    
    def update_product(self, data):
        """Aktualizuje dane produktu - POPRAWIONA WERSJA"""
        try:
            product_id = data.get('product_id')
            name = data.get('name', '').strip()
            ean = data.get('ean', '').strip()
            
            if not product_id or not name:
                return {'success': False, 'error': 'Brak wymaganych danych'}
            
            # Użyj sync wrapper
            from sync.sync_integration import _sync_wrapper
            if _sync_wrapper:
                logger.info(f"ProductManager using sync wrapper: {product_id}")
                return _sync_wrapper.update_product(product_id, data)
            else:
                # Fallback lokalny (jeśli sync nie działa)
                return self._update_product_local(data)
                
        except Exception as e:
            logger.error(f"Error in ProductManager.update_product: {e}")
            return {'success': False, 'error': str(e)}
    
    def delete_product(self):
        """API - usuwa produkt"""
        try:
            data = request.get_json()
            product_id = data.get('product_id')
            
            if not product_id:
                return jsonify({'success': False, 'error': 'Brak product_id'})
            
            # Załaduj produkty
            products = load_products()
            products = [p for p in products if not (isinstance(p, dict) and p.get('id') == product_id)]
            
            # Zapisz
            import json
            with open('data/products.txt', 'w', encoding='utf-8') as f:
                for product in products:
                    if isinstance(product, dict):
                        f.write(json.dumps(product, ensure_ascii=False) + '\n')
            
            # Usuń też linki tego produktu
            try:
                links = load_links()
                links = [l for l in links if not (isinstance(l, dict) and l.get('product_id') == product_id)]
                
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in links:
                        if isinstance(link, dict):
                            f.write(json.dumps(link, ensure_ascii=False) + '\n')
            except:
                pass  # Nie blokuj jeśli nie ma linków
            
            return jsonify({'success': True, 'message': 'Produkt został usunięty'})
            
        except Exception as e:
            logger.error(f"Error in delete_product: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    def find_in_shops(self):
        """API - wyszukuje produkt we wszystkich skonfigurowanych sklepach"""
        try:
            data = request.get_json()
            product_id = data.get('product_id')
            
            if not product_id:
                return jsonify({'success': False, 'error': 'Brak product_id'})
            
            # Użyj istniejącej funkcji z finder_bp
            from utils.data_utils import load_products, load_links
            from shop_config import shop_config
            from product_finder import product_finder
            
            # Pobierz produkt
            products = load_products()
            product = next((p for p in products if p.get('id') == product_id), None)
            if not product:
                return jsonify({'success': False, 'error': 'Produkt nie został znaleziony'})
            
            # Pobierz sklepy ze skonfigurowanym wyszukiwaniem
            all_shops = shop_config.get_all_shops()
            shops_with_search = [s for s in all_shops 
                            if s.get('search_config') and s['search_config'].get('search_url')]
            
            # Sprawdź gdzie produkt już istnieje
            existing_links = load_links()
            existing_shops = {link['shop_id'] for link in existing_links 
                            if link.get('product_id') == product_id}
            
            # Sklepy do przeszukania
            shops_to_search = [s for s in shops_with_search 
                            if s['shop_id'] not in existing_shops]
            
            if not shops_to_search:
                return jsonify({
                    'success': True,
                    'message': f'Produkt już dostępny we wszystkich sklepach',
                    'summary': {
                        'shops_searched': 0,
                        'successful_searches': 0,
                        'failed_searches': 0,
                        'total_found_products': 0,
                        'existing_shops': len(existing_shops),
                        'total_configured_shops': len(shops_with_search)
                    },
                    'results': []
                })
            
            # Wyszukaj w każdym sklepie używając istniejącej logiki
            results = []
            successful = 0
            failed = 0
            total_found = 0
            
            for shop in shops_to_search:
                try:
                    search_config = shop['search_config']
                    debug_info = []
                    
                    # Użyj tej samej logiki co search_product_in_shop
                    search_result = product_finder.search_product(
                        search_config,
                        product['name'],
                        product.get('ean'),
                        debug_info
                    )
                    
                    shop_result = {
                        'shop_id': shop['shop_id'],
                        'shop_name': shop.get('name', shop['shop_id']),
                        'search_success': search_result.get('success', False),
                        'debug_info': debug_info
                    }
                    
                    if search_result.get('success'):
                        found_products = search_result.get('results', [])
                        shop_result['found_products'] = found_products
                        shop_result['total_found'] = len(found_products)
                        total_found += len(found_products)
                        successful += 1
                    else:
                        shop_result['error'] = search_result.get('error', 'Nieznany błąd')
                        shop_result['total_found'] = 0
                        failed += 1
                    
                    results.append(shop_result)
                    
                except Exception as e:
                    failed += 1
                    results.append({
                        'shop_id': shop['shop_id'],
                        'shop_name': shop.get('name', shop['shop_id']),
                        'search_success': False,
                        'error': str(e),
                        'total_found': 0,
                        'debug_info': [f'Exception: {str(e)}']
                    })
            
            return jsonify({
                'success': True,
                'message': f'Przeszukano {len(shops_to_search)} sklepów',
                'product': {'id': product_id, 'name': product['name']},
                'summary': {
                    'shops_searched': len(shops_to_search),
                    'successful_searches': successful,
                    'failed_searches': failed,
                    'total_found_products': total_found,
                    'existing_shops': len(existing_shops),
                    'total_configured_shops': len(shops_with_search)
                },
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error in find_in_shops: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    def get_available_shops(self):
        """API - zwraca dostępne sklepy"""
        try:
            from shop_config import shop_config
            shops = shop_config.get_all_shops()
            
            # POPRAWKA: Filtruj tylko słowniki
            shops = [shop for shop in shops if isinstance(shop, dict)]
            
            return jsonify({
                'success': True,
                'shops': shops
            })
            
        except Exception as e:
            logger.error(f"Error in get_available_shops: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    def search_in_single_shop(self):
        """API - wyszukuje w pojedynczym sklepie"""
        try:
            data = request.get_json()
            shop_id = data.get('shop_id')
            product_name = data.get('product_name')
            
            if not shop_id or not product_name:
                return jsonify({'success': False, 'error': 'Brak wymaganych danych'})
            
            # Tu może być implementacja wyszukiwania w sklepie
            return jsonify({
                'success': True,
                'shop_id': shop_id,
                'query': product_name,
                'results': []
            })
            
        except Exception as e:
            logger.error(f"Error in search_in_single_shop: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    def find_missing_for_product(self, product_id):
        """API - znajduje sklepy gdzie nie ma tego produktu"""
        try:
            # Znajdź produkt
            products = load_products()
            product = next((p for p in products if isinstance(p, dict) and p.get('id') == product_id), None)
            
            if not product:
                return jsonify({'success': False, 'error': 'Produkt nie został znaleziony'})
            
            # Znajdź sklepy gdzie już jest
            links = load_links()
            existing_shops = set()
            for link in links:
                if isinstance(link, dict) and link.get('product_id') == product_id:
                    existing_shops.add(link.get('shop_id'))
            
            # Lista wszystkich dostępnych sklepów
            from shop_config import shop_config
            all_shops = shop_config.get_all_shops()
            all_shops = [shop for shop in all_shops if isinstance(shop, dict)]
            
            # Sklepy gdzie nie ma produktu
            missing_shops = []
            for shop in all_shops:
                if shop.get('shop_id') not in existing_shops:
                    missing_shops.append(shop)
            
            return jsonify({
                'success': True,
                'product': product,
                'existing_shops': list(existing_shops),
                'missing_shops': missing_shops
            })
            
        except Exception as e:
            logger.error(f"Error in find_missing_for_product: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    def search_product_in_shop(self):
        """API - wyszukuje produkt w konkretnym sklepie - KOMPLETNA WERSJA"""
        try:
            # DEBUG na początku
            logger.info("=== SEARCH PRODUCT IN SHOP START ===")
            
            data = request.get_json()
            logger.info(f"Received data: {data}")
            
            if not data:
                logger.error("No JSON data received")
                return jsonify({
                    'success': False,
                    'error': 'Brak danych JSON',
                    'debug': 'No JSON data received'
                })
            
            shop_id = data.get('shop_id')
            product_id = data.get('product_id')
            
            logger.info(f"Extracted - shop_id: {shop_id}, product_id: {product_id}")
            
            # Walidacja z szczegółowymi błędami
            if not shop_id:
                logger.error(f"Missing shop_id. Available keys: {list(data.keys())}")
                return jsonify({
                    'success': False,
                    'error': 'Brak shop_id',
                    'debug': f'Available keys: {list(data.keys())}'
                })
            
            if not product_id:
                logger.error(f"Missing product_id. Available keys: {list(data.keys())}")
                return jsonify({
                    'success': False,
                    'error': 'Brak product_id',
                    'debug': f'Available keys: {list(data.keys())}'
                })
            
            # Pobierz dane produktu na podstawie product_id
            from utils.data_utils import load_products
            products = load_products()
            
            product = None
            for p in products:
                if p.get('id') == product_id:
                    product = p
                    break
            
            if not product:
                logger.error(f"Product {product_id} not found in {len(products)} products")
                return jsonify({
                    'success': False,
                    'error': f'Nie znaleziono produktu o ID {product_id}',
                    'debug': f'Searched in {len(products)} products'
                })
            
            logger.info(f"Found product: {product.get('name')}")
            
            product_name = product.get('name', '')
            ean = product.get('ean', '')
            
            if not product_name:
                logger.error("Product has no name")
                return jsonify({
                    'success': False,
                    'error': 'Produkt nie ma nazwy',
                    'debug': f'Product data: {product}'
                })
            
            # Import product finder
            try:
                from product_finder import product_finder
                from shop_config import shop_config
                
                logger.info(f"Importing modules successful")
                
                # Pobierz konfigurację wyszukiwania dla sklepu
                shop_config_data = shop_config.get_shop_config(shop_id)
                search_config = shop_config_data.get('search_config', {})
                
                logger.info(f"Shop config for {shop_id}: {search_config}")
                
                if not search_config.get('search_url'):
                    logger.error(f"No search URL for shop {shop_id}")
                    return jsonify({
                        'success': False,
                        'error': f'Brak konfiguracji wyszukiwania dla sklepu {shop_id}',
                        'debug': f'Shop config: {shop_config_data}'
                    })
                
                # Wykonaj wyszukiwanie
                logger.info(f"Starting search for '{product_name}' in {shop_id}")
                debug_info = []
                
                search_result = product_finder.search_product(
                    search_config, product_name, ean, debug_info
                )
                
                logger.info(f"Search completed. Result: {search_result}")
                
                # Dodaj informacje o produkcie do wyniku
                search_result['product_id'] = product_id
                search_result['product_name'] = product_name
                search_result['shop_id'] = shop_id
                search_result['debug'] = debug_info
                
                logger.info("=== SEARCH PRODUCT IN SHOP SUCCESS ===")
                return jsonify(search_result)
                
            except ImportError as e:
                logger.error(f"Import error: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Brak modułu product_finder: {str(e)}',
                    'debug': f'Import error: {type(e).__name__}'
                })
                
        except Exception as e:
            logger.error(f"Exception in search_product_in_shop: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': f'Błąd wewnętrzny: {str(e)}',
                'debug': f'Exception: {type(e).__name__}'
            })