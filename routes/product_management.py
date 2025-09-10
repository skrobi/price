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
        """Dodaj produkt z URL - NAPRAWIONA IMPLEMENTACJA"""
        if request.method == 'GET':
            return render_template('add_product_url.html')
        
        try:
            url = request.form.get('url', '').strip()
            
            if not url:
                flash('URL jest wymagany')
                return render_template('add_product_url.html')
            
            # Walidacja URL
            if not (url.startswith('http://') or url.startswith('https://')):
                flash('URL musi zaczynać się od http:// lub https://')
                return render_template('add_product_url.html')
            
            # Identyfikuj sklep z URL
            from urllib.parse import urlparse
            import requests
            from bs4 import BeautifulSoup
            
            parsed = urlparse(url.lower())
            domain = parsed.netloc.replace('www.', '')
            
            # Mapowanie domen na sklepy
            shop_mappings = {
                'allegro.pl': 'Allegro',
                'amazon.pl': 'Amazon',
                'amazon.com': 'Amazon',
                'ceneo.pl': 'Ceneo',
                'morele.net': 'Morele',
                'x-kom.pl': 'x-kom',
                'mediamarkt.pl': 'MediaMarkt',
                'saturn.pl': 'Saturn',
                'empik.com': 'Empik',
                'euro.com.pl': 'Euro',
                'doz.pl': 'DOZ',
                'rosa24.pl': 'Rosa24',
                'gemini.pl': 'Gemini'
            }
            
            shop_name = None
            shop_id = None
            
            for pattern, name in shop_mappings.items():
                if pattern in domain:
                    shop_name = name
                    shop_id = pattern.replace('.', '_').replace('_pl', '').replace('_com', '').replace('_net', '')
                    break
            
            if not shop_name:
                shop_name = domain.title()
                shop_id = domain.replace('.', '_')
            
            # Próbuj wyciągnąć nazwę produktu ze strony
            product_name = None
            product_ean = None
            
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Różne selektory dla nazwy produktu w zależności od sklepu
                    title_selectors = [
                        'h1',  # Ogólny selektor
                        '[data-testid="product-name"]',  # Allegro
                        '.product-title',  # Ogólny
                        '.product-name',   # Ogólny
                        '#productTitle',   # Amazon
                        '.a-size-large',   # Amazon
                        '.offer-title h1', # Ceneo
                        '.prod-name',      # x-kom
                        '.product-header h1'  # Różne sklepy
                    ]
                    
                    for selector in title_selectors:
                        title_elem = soup.select_one(selector)
                        if title_elem:
                            product_name = title_elem.get_text().strip()
                            if len(product_name) > 10:  # Sprawdź czy to sensowna nazwa
                                break
                    
                    # Próbuj znaleźć EAN
                    ean_selectors = [
                        '[data-testid="ean"]',
                        '.ean',
                        '.product-ean',
                        '[title*="EAN"]',
                        '[alt*="EAN"]'
                    ]
                    
                    for selector in ean_selectors:
                        ean_elem = soup.select_one(selector)
                        if ean_elem:
                            ean_text = ean_elem.get_text().strip()
                            # Sprawdź czy to wygląda jak EAN (8 lub 13 cyfr)
                            if ean_text.isdigit() and len(ean_text) in [8, 13]:
                                product_ean = ean_text
                                break
                            
            except Exception as e:
                logger.warning(f"Failed to scrape product details: {e}")
                flash(f'Ostrzeżenie: Nie udało się pobrać szczegółów ze strony: {str(e)}')
            
            # Jeśli nie udało się wyciągnąć nazwy, użyj domyślnej
            if not product_name:
                product_name = f"Produkt z {shop_name}"
            
            # Czyść nazwę produktu
            product_name = product_name.replace('\n', ' ').replace('\t', ' ')
            product_name = ' '.join(product_name.split())  # Usuń wielokrotne spacje
            
            # Skróć jeśli za długa
            if len(product_name) > 200:
                product_name = product_name[:200] + "..."
            
            # Sprawdź czy produkt już istnieje
            products = load_products()
            for product in products:
                if isinstance(product, dict) and product.get('name', '').lower() == product_name.lower():
                    flash(f'Produkt "{product_name}" już istnieje w bazie')
                    return redirect(url_for('products.product_detail', product_id=product['id']))
            
            # Utwórz nowy produkt
            new_id = max([p.get('id', 0) for p in products if isinstance(p, dict)], default=0) + 1
            
            product_data = {
                'id': new_id,
                'name': product_name,
                'ean': product_ean or '',
                'created': datetime.now().isoformat(),
                'source': 'url_import',
                'origin_url': url,
                'origin_shop': shop_name
            }
            
            # Zapisz produkt
            try:
                try:
                    from sync.sync_integration import save_product_sync
                    result = save_product_sync(product_data)
                    
                    if result.get('success'):
                        synced_msg = " (zsynchronizowany)" if result.get('synced') else " (lokalnie)"
                        flash(f'Produkt "{product_name}" został dodany{synced_msg}')
                    else:
                        raise Exception(result.get('error', 'Błąd zapisu'))
                        
                except (ImportError, AttributeError):
                    save_product(product_data)
                    flash(f'Produkt "{product_name}" został dodany')
                
            except Exception as e:
                logger.error(f"Error saving product from URL: {e}")
                save_product(product_data)
                flash(f'Produkt "{product_name}" został dodany (bez synchronizacji)')
            
            # Dodaj też link do sklepu
            try:
                from utils.data_utils import save_link
                
                link_data = {
                    'id': int(datetime.now().timestamp()),
                    'product_id': new_id,
                    'shop_id': shop_id,
                    'url': url,
                    'created': datetime.now().isoformat(),
                    'source': 'url_import'
                }
                
                try:
                    from sync.sync_integration import save_link_sync
                    save_link_sync(link_data)
                    flash(f'Link do {shop_name} został dodany')
                except (ImportError, AttributeError):
                    save_link(link_data)
                    flash(f'Link do {shop_name} został dodany')
                    
            except Exception as e:
                logger.error(f"Error saving link: {e}")
                flash(f'Ostrzeżenie: Nie udało się dodać linku: {str(e)}')
            
            # Przekieruj do szczegółów produktu
            return redirect(url_for('products.product_detail', product_id=new_id))
            
        except Exception as e:
            logger.error(f"Error in add_product_url: {e}")
            flash(f'Błąd podczas dodawania produktu: {str(e)}')
            return render_template('add_product_url.html')
    
    def product_detail(self, product_id):
        """Szczegóły produktu - Z PEŁNYM DEBUGOWANIEM"""
        print(f"\n🔍 DEBUG PRODUCT_DETAIL START - product_id: {product_id}")
        
        try:
            # KROK 1: Załaduj produkty
            print("📦 KROK 1: Ładowanie produktów...")
            products = load_products()
            print(f"   ✅ Załadowano {len(products)} produktów")
            print(f"   📋 Typy produktów: {[type(p) for p in products[:3]]}")
            
            # KROK 2: Znajdź konkretny produkt
            print(f"🔎 KROK 2: Szukanie produktu ID {product_id}...")
            product = None
            for i, p in enumerate(products):
                print(f"   Produkt {i}: typ={type(p)}, dict={isinstance(p, dict)}")
                if isinstance(p, dict):
                    p_id = p.get('id')
                    print(f"     ID: {p_id} (typ: {type(p_id)})")
                    if p_id == product_id:
                        product = p
                        print(f"   ✅ ZNALEZIONO! {p.get('name', 'Bez nazwy')}")
                        break
            
            if not product:
                print("   ❌ PRODUKT NIE ZNALEZIONY!")
                available_ids = [p.get('id') for p in products if isinstance(p, dict)]
                print(f"   📋 Dostępne ID: {available_ids}")
                flash('Produkt nie został znaleziony')
                return redirect(url_for('products.products'))
            
            # KROK 3: Załaduj linki
            print("🔗 KROK 3: Ładowanie linków...")
            links = load_links()
            print(f"   ✅ Załadowano {len(links)} linków")
            
            product_links = []
            for link in links:
                if isinstance(link, dict) and link.get('product_id') == product_id:
                    product_links.append(link)
                    print(f"   🔗 Link: {link.get('shop_id')} -> {link.get('url', '')[:50]}...")
            
            print(f"   📊 Znaleziono {len(product_links)} linków dla produktu")
            
            # KROK 4: Załaduj ceny
            print("💰 KROK 4: Ładowanie cen...")
            latest_prices = get_latest_prices()
            print(f"   ✅ Załadowano {len(latest_prices)} cen")
            print(f"   📋 Przykładowe klucze cen: {list(latest_prices.keys())[:5]}")
            
            # KROK 5: Dodaj ceny do linków
            print("🔄 KROK 5: Łączenie cen z linkami...")
            for i, link in enumerate(product_links):
                print(f"   🔗 Link {i+1}: {link.get('shop_id')}")
                
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
                        print(f"     ✅ ZNALEZIONO CENĘ! {price_data.get('price')} {price_data.get('currency', 'PLN')}")
                        found_price = True
                        
                        try:
                            # Ustaw ceny
                            link['price'] = float(price_data.get('price', 0))
                            link['price_pln'] = float(price_data.get('price_pln', price_data.get('price', 0)))
                            link['currency'] = price_data.get('currency', 'PLN')
                            
                            # BEZPIECZNE formatowanie daty
                            created_date = price_data.get('created', '')
                            print(f"     📅 Data: '{created_date}' (typ: {type(created_date)})")
                            
                            if created_date and isinstance(created_date, str):
                                try:
                                    if 'T' in created_date:
                                        # Format ISO: 2024-01-15T10:30:45
                                        date_part = created_date.split('T')[0]
                                        time_part = created_date.split('T')[1][:8]
                                        link['price_updated'] = f"{date_part} {time_part}"
                                        print(f"     📅 Sformatowana data: {link['price_updated']}")
                                    elif len(created_date) >= 16:
                                        link['price_updated'] = created_date[:16]
                                        print(f"     📅 Obcięta data: {link['price_updated']}")
                                    else:
                                        link['price_updated'] = created_date
                                        print(f"     📅 Oryginalna data: {link['price_updated']}")
                                except Exception as date_error:
                                    print(f"     ❌ BŁĄD formatowania daty: {date_error}")
                                    link['price_updated'] = str(created_date) or 'Błąd daty'
                            else:
                                link['price_updated'] = 'Brak daty'
                                print(f"     📅 Brak daty lub nieprawidłowy typ")
                                
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
    
    def update_product(self):
        """API - aktualizuje dane produktu"""
        try:
            data = request.get_json()
            product_id = data.get('product_id')
            name = data.get('name', '').strip()
            ean = data.get('ean', '').strip()
            
            if not product_id or not name:
                return jsonify({'success': False, 'error': 'Brak wymaganych danych'})
            
            # Załaduj produkty
            products = load_products()
            product_index = None
            
            for i, product in enumerate(products):
                if isinstance(product, dict) and product.get('id') == product_id:
                    product_index = i
                    break
            
            if product_index is None:
                return jsonify({'success': False, 'error': 'Produkt nie został znaleziony'})
            
            # Aktualizuj dane
            products[product_index]['name'] = name
            products[product_index]['ean'] = ean
            products[product_index]['updated'] = datetime.now().isoformat()
            
            # Zapisz
            import json
            with open('data/products.txt', 'w', encoding='utf-8') as f:
                for product in products:
                    if isinstance(product, dict):
                        f.write(json.dumps(product, ensure_ascii=False) + '\n')
            
            return jsonify({'success': True, 'message': 'Produkt został zaktualizowany'})
            
        except Exception as e:
            logger.error(f"Error in update_product: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
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
        """API - wyszukuje produkt w sklepach"""
        try:
            data = request.get_json()
            product_id = data.get('product_id')
            
            if not product_id:
                return jsonify({'success': False, 'error': 'Brak product_id'})
            
            # Znajdź produkt
            products = load_products()
            product = next((p for p in products if isinstance(p, dict) and p.get('id') == product_id), None)
            
            if not product:
                return jsonify({'success': False, 'error': 'Produkt nie został znaleziony'})
            
            # Tu może być implementacja wyszukiwania
            # Na razie zwróć placeholder
            return jsonify({
                'success': True,
                'message': f'Wyszukiwanie "{product["name"]}" w sklepach...',
                'results': []
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
        """API - wyszukuje produkt w konkretnym sklepie"""
        try:
            data = request.get_json()
            shop_id = data.get('shop_id')
            product_id = data.get('product_id')
            product_name = data.get('product_name')
            ean = data.get('ean', '')
            
            if not all([shop_id, product_name]):
                return jsonify({
                    'success': False,
                    'error': 'Brak shop_id lub product_name'
                })
            
            # Import product finder
            try:
                from product_finder import product_finder
                from shop_config import shop_config
                
                # Pobierz konfigurację wyszukiwania dla sklepu
                shop_config_data = shop_config.get_shop_config(shop_id)
                search_config = shop_config_data.get('search_config', {})
                
                if not search_config.get('search_url'):
                    return jsonify({
                        'success': False,
                        'error': f'Brak konfiguracji wyszukiwania dla sklepu {shop_id}'
                    })
                
                # Wykonaj wyszukiwanie
                debug_info = []
                search_result = product_finder.search_product(
                    search_config, product_name, ean, debug_info
                )
                
                # Dodaj debug info do wyniku
                search_result['debug'] = debug_info
                
                return jsonify(search_result)
                
            except ImportError as e:
                return jsonify({
                    'success': False,
                    'error': f'Brak modułu product_finder: {str(e)}'
                })
                
        except Exception as e:
            logger.error(f"Error in search_product_in_shop: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })