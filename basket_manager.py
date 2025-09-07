"""
Główny moduł zarządzania koszykami - PRZEPISANY Z MODUŁOWĄ STRUKTURĄ
POPRAWKA: Obsługa grupowania produktów zamiennych w koszyku
"""
import json
import os
from datetime import datetime
from itertools import product as itertools_product

# Import modułów - POPRAWIONE IMPORTY
from substitute_manager import substitute_manager
from quantity_optimizer import QuantityOptimizer
from combination_evaluator import CombinationEvaluator

class SubstituteHandler:
    """Klasa do obsługi zamienników - ULEPSZONA IMPLEMENTACJA"""
    
    def __init__(self, log_func):
        self.log = log_func
    
    def group_substitute_products(self, basket, log_func):
        """
        NOWA FUNKCJA: Grupuje produkty w koszyku według grup zamienników
        
        Returns:
            dict: {
                'groups': [list grup potrzeb],
                'mapping': {original_product_id: group_index}
            }
        """
        log_func("🔗 KROK 2.5: GRUPOWANIE PRODUKTÓW ZAMIENNYCH W KOSZYKU")
        
        groups = substitute_manager.load_substitute_groups()
        basket_items = basket.get('basket_items', {})
        
        # Mapowanie: product_id -> group_id
        product_to_group = {}
        for group_id, group_data in groups.items():
            for product_id in group_data['product_ids']:
                product_to_group[product_id] = group_id
        
        # Znajdź produkty w koszyku które są w grupach zamienników
        grouped_needs = []  # Lista grup potrzeb
        used_groups = set()  # Już przetworzone grupy
        individual_products = []  # Produkty bez grup
        product_mapping = {}  # original_product_id -> group_index lub individual_index
        
        log_func(f"   📋 Analiza {len(basket_items)} produktów w koszyku:")
        
        for product_key, item in basket_items.items():
            product_id = item['product_id']
            quantity = item['requested_quantity']
            
            # Sprawdź czy produkt należy do grupy zamienników
            group_id = product_to_group.get(product_id)
            
            if group_id and group_id not in used_groups:
                # Nowa grupa zamienników - znajdź wszystkie produkty z tej grupy w koszyku
                group_products = []
                total_quantity = 0
                
                for other_key, other_item in basket_items.items():
                    other_product_id = other_item['product_id']
                    if product_to_group.get(other_product_id) == group_id:
                        group_products.append({
                            'product_id': other_product_id,
                            'quantity': other_item['requested_quantity'],
                            'product_name': other_item.get('product_name', f'Produkt {other_product_id}'),
                            'substitute_settings': other_item.get('substitute_settings', {})
                        })
                        total_quantity += other_item['requested_quantity']
                        
                        # Mapuj oryginalny produkt na grupę
                        product_mapping[other_product_id] = len(grouped_needs)
                
                if len(group_products) > 1:
                    # UWAGA: W koszyku są produkty z tej samej grupy zamienników!
                    log_func(f"   ⚠️  GRUPA {group_id}: {len(group_products)} produktów z tej samej grupy!")
                    
                    product_names = [p['product_name'] for p in group_products]
                    quantities = [f"{p['product_id']}({p['quantity']}szt)" for p in group_products]
                    
                    log_func(f"      📦 Produkty: {', '.join(product_names)}")
                    log_func(f"      🔢 Ilości: {', '.join(quantities)} = {total_quantity} szt łącznie")
                    log_func(f"      ⚠️  UWAGA: W koszyku są zarówno oryginał jak i zamiennik - zostaną połączone!")
                    
                    # Wybierz najrestrykcyjniejsze ustawienia zamienników z grupy
                    group_settings = self._merge_substitute_settings([p['substitute_settings'] for p in group_products])
                    
                    grouped_needs.append({
                        'type': 'substitute_group',
                        'group_id': group_id,
                        'products_in_basket': group_products,
                        'total_quantity': total_quantity,
                        'substitute_settings': group_settings,
                        'group_name': f"Grupa zamienników {group_id}"
                    })
                    
                    used_groups.add(group_id)
                    
                else:
                    # Pojedynczy produkt z grupy zamienników
                    individual_products.append({
                        'type': 'individual',
                        'product_id': product_id,
                        'quantity': quantity,
                        'product_name': item.get('product_name', f'Produkt {product_id}'),
                        'substitute_settings': item.get('substitute_settings', {}),
                        'has_substitutes': True,
                        'group_id': group_id
                    })
                    product_mapping[product_id] = len(grouped_needs) + len(individual_products) - 1
                    log_func(f"   ✅ Produkt {product_id}: jednotlivý ze skupiny {group_id} ({quantity} szt)")
                    
            elif not group_id:
                # Produkt bez grupy zamienników
                individual_products.append({
                    'type': 'individual',
                    'product_id': product_id,
                    'quantity': quantity,
                    'product_name': item.get('product_name', f'Produkt {product_id}'),
                    'substitute_settings': item.get('substitute_settings', {}),
                    'has_substitutes': False,
                    'group_id': None
                })
                product_mapping[product_id] = len(grouped_needs) + len(individual_products) - 1
                log_func(f"   📦 Produkt {product_id}: pojedynczy bez zamienników ({quantity} szt)")
        
        # Połącz grupy i produkty indywidualne
        all_needs = grouped_needs + individual_products
        
        log_func(f"   🎯 PODSUMOWANIE GRUPOWANIA:")
        log_func(f"      🔗 Grup zamienników: {len(grouped_needs)}")
        log_func(f"      📦 Produktów indywidualnych: {len(individual_products)}")
        log_func(f"      🎯 Łączna liczba potrzeb: {len(all_needs)}")
        
        return {
            'groups': all_needs,
            'mapping': product_mapping
        }
    
    def _merge_substitute_settings(self, settings_list):
        """Łączy ustawienia zamienników z grupy (wybiera najrestrykcyjniejsze)"""
        if not settings_list:
            return {'allow_substitutes': True, 'max_price_increase_percent': 20.0}
        
        # Wybierz najrestrykcyjniejsze ustawienia
        allow_substitutes = all(s.get('allow_substitutes', True) for s in settings_list)
        max_increases = [s.get('max_price_increase_percent', 20.0) for s in settings_list]
        min_max_increase = min(max_increases)
        
        return {
            'allow_substitutes': allow_substitutes,
            'max_price_increase_percent': min_max_increase
        }
    
    def expand_offers_with_substitutes_for_groups(self, grouped_needs, settings, log_func):
        """
        NOWA FUNKCJA: Rozszerza oferty o zamienniki dla zgrupowanych potrzeb
        """
        log_func("🔄 KROK 3: ROZSZERZANIE OFERT O ZAMIENNIKI (NOWA LOGIKA GRUP)")
        
        substitute_settings = settings.get('substitute_settings', {})
        global_allow_substitutes = substitute_settings.get('allow_substitutes', True)
        
        if not global_allow_substitutes:
            log_func("   ❌ Zamienniki WYŁĄCZONE globalnie")
            return {}
        
        expanded_offers = {}
        
        for need_index, need in enumerate(grouped_needs):
            need_key = f"need_{need_index}"
            expanded_offers[need_key] = []
            
            if need['type'] == 'substitute_group':
                # Grupa zamienników - pobierz oferty dla wszystkich produktów w grupie
                log_func(f"   🔗 GRUPA {need['group_id']}: {need['total_quantity']} szt łącznie")
                
                group_settings = need['substitute_settings']
                group_allow_substitutes = group_settings.get('allow_substitutes', True)
                max_price_increase = group_settings.get('max_price_increase_percent', 20.0)
                
                if not group_allow_substitutes:
                    log_func(f"      ❌ Zamienniki wyłączone dla tej grupy")
                    continue
                
                # Znajdź wszystkie produkty w grupie (nie tylko te w koszyku)
                groups = substitute_manager.load_substitute_groups()
                group_data = groups.get(need['group_id'])
                
                if group_data:
                    all_group_products = group_data['product_ids']
                    log_func(f"      📦 Sprawdzam oferty dla wszystkich {len(all_group_products)} produktów z grupy")
                    
                    # Dla każdego produktu w grupie znajdź oferty
                    for product_id in all_group_products:
                        try:
                            substitute_offers = substitute_manager.find_best_substitute_offers(
                                product_id,
                                need['total_quantity'],
                                max_price_increase
                            )
                            
                            for substitute_data in substitute_offers:
                                for offer in substitute_data['offers']:
                                    # Dodaj informacje o grupie
                                    offer['is_substitute'] = substitute_data['is_substitute']
                                    offer['original_group'] = need['group_id']
                                    offer['substitute_reason'] = substitute_data['substitute_reason']
                                    offer['group_quantity'] = need['total_quantity']
                                    
                                    # Jeśli to produkt z koszyka, oznacz specjalnie
                                    if product_id in [p['product_id'] for p in need['products_in_basket']]:
                                        offer['from_basket'] = True
                                        offer['basket_product_id'] = product_id
                                    else:
                                        offer['from_basket'] = False
                                    
                                    expanded_offers[need_key].append(offer)
                            
                        except Exception as e:
                            log_func(f"      ⚠️ Błąd przy produktie {product_id}: {str(e)}")
                            continue
                
                log_func(f"      ✅ Dodano {len(expanded_offers[need_key])} ofert dla grupy")
                
            else:
                # Produkt indywidualny
                product_id = need['product_id']
                quantity = need['quantity']
                item_settings = need['substitute_settings']
                
                item_allow_substitutes = item_settings.get('allow_substitutes', True)
                max_price_increase = item_settings.get('max_price_increase_percent', 20.0)
                
                log_func(f"   📦 PRODUKT {product_id}: {quantity} szt")
                
                if not item_allow_substitutes:
                    log_func(f"      ❌ Zamienniki wyłączone dla tego produktu")
                    continue
                
                # Znajdź oferty dla produktu i jego zamienników
                try:
                    substitute_offers = substitute_manager.find_best_substitute_offers(
                        product_id,
                        quantity,
                        max_price_increase
                    )
                    
                    for substitute_data in substitute_offers:
                        for offer in substitute_data['offers']:
                            offer['is_substitute'] = substitute_data['is_substitute']
                            offer['original_product_id'] = product_id
                            offer['substitute_reason'] = substitute_data['substitute_reason']
                            offer['individual_quantity'] = quantity
                            
                            expanded_offers[need_key].append(offer)
                    
                    log_func(f"      ✅ Dodano {len(expanded_offers[need_key])} ofert")
                    
                except Exception as e:
                    log_func(f"      ⚠️ Błąd przy wyszukiwaniu zamienników: {str(e)}")
                    continue
        
        # Podsumowanie
        total_offers = sum(len(offers) for offers in expanded_offers.values())
        log_func(f"🎯 ŁĄCZNIE: {total_offers} ofert dla {len(grouped_needs)} potrzeb")
        
        return expanded_offers

class BasketManager:
    """Zarządzanie koszykami z modułową optymalizacją"""
    
    def __init__(self):
        self.baskets_file = 'data/baskets.txt'
        self.ensure_data_dir()
    
    def ensure_data_dir(self):
        """Upewnij się że folder data istnieje"""
        if not os.path.exists('data'):
            os.makedirs('data')
    
    def load_baskets(self):
        """Ładuje wszystkie koszyki użytkownika"""
        try:
            with open(self.baskets_file, 'r', encoding='utf-8') as f:
                baskets = {}
                for line in f:
                    if line.strip():
                        try:
                            basket = json.loads(line)
                            
                            # MIGRUJ stare koszyki
                            if 'items' in basket and not isinstance(basket['items'], dict):
                                basket['basket_items'] = {}
                                del basket['items']
                            elif 'items' in basket and isinstance(basket['items'], dict):
                                basket['basket_items'] = basket['items']
                                del basket['items']
                            elif 'basket_items' not in basket:
                                basket['basket_items'] = {}
                            
                            baskets[basket['basket_id']] = basket
                        except (json.JSONDecodeError, KeyError) as e:
                            print(f"Błąd w linii koszyka: {e}")
                            continue
                            
                return baskets
        except FileNotFoundError:
            return {}
    
    def save_basket(self, basket_data):
        """Zapisuje koszyk do pliku"""
        baskets = self.load_baskets()
        baskets[basket_data['basket_id']] = basket_data
        
        with open(self.baskets_file, 'w', encoding='utf-8') as f:
            for basket in baskets.values():
                f.write(json.dumps(basket, ensure_ascii=False) + '\n')
    
    def create_new_basket(self, name="Nowy koszyk", optimization_settings=None):
        """Tworzy nowy koszyk z domyślnymi ustawieniami"""
        baskets = self.load_baskets()
        basket_id = f"basket_{len(baskets) + 1}_{int(datetime.now().timestamp())}"
        
        if optimization_settings is None:
            optimization_settings = {
                "priority": "lowest_total_cost",
                "max_shops": 5,
                "suggest_quantities": True,
                "min_savings_threshold": 5.0,
                "max_quantity_multiplier": 3,
                "consider_free_shipping": True,
                "show_logs": False,
                "substitute_settings": {
                    "allow_substitutes": True,
                    "max_price_increase_percent": 20.0,
                    "prefer_original": True,
                    "max_substitutes_per_product": 3,
                    "show_substitute_reasons": True
                }
            }
        
        basket = {
            "basket_id": basket_id,
            "name": name,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "optimization_settings": optimization_settings,
            "basket_items": {},
            "last_optimization": None
        }
        
        self.save_basket(basket)
        return basket_id
    
    def add_item_to_basket(self, basket_id, product_id, quantity=1, product_name=""):
        """Dodaje produkt do koszyka"""
        baskets = self.load_baskets()
        if basket_id not in baskets:
            return False
        
        basket = baskets[basket_id]
        product_key = str(product_id)
        
        if 'basket_items' not in basket:
            basket['basket_items'] = {}
        
        if product_key in basket['basket_items']:
            basket['basket_items'][product_key]['requested_quantity'] += quantity
        else:
            basket['basket_items'][product_key] = {
                "product_id": product_id,
                "product_name": product_name,
                "requested_quantity": quantity,
                "suggested_quantity": quantity,
                "reason": "",
                "locked_quantity": False,
                "substitute_settings": {
                    "allow_substitutes": True,
                    "max_price_increase_percent": 20.0
                }
            }
        
        basket['updated'] = datetime.now().isoformat()
        self.save_basket(basket)
        return True
    
    def update_item_substitute_settings(self, basket_id, product_id, allow_substitutes, max_price_increase):
        """Aktualizuje ustawienia zamienników dla konkretnego produktu w koszyku"""
        basket = self.get_basket(basket_id)
        if not basket:
            return False
        
        product_key = str(product_id)
        if product_key in basket.get('basket_items', {}):
            basket['basket_items'][product_key]['substitute_settings'] = {
                'allow_substitutes': allow_substitutes,
                'max_price_increase_percent': max_price_increase
            }
            basket['updated'] = datetime.now().isoformat()
            self.save_basket(basket)
            return True
        
        return False
    
    def get_basket(self, basket_id):
        """Pobiera konkretny koszyk"""
        baskets = self.load_baskets()
        basket = baskets.get(basket_id)
        
        if basket and 'items' in basket and 'basket_items' not in basket:
            basket['basket_items'] = basket['items']
            del basket['items']
            self.save_basket(basket)
        
        if basket and 'basket_items' not in basket:
            basket['basket_items'] = {}
            self.save_basket(basket)
            
        return basket
    
    def delete_basket(self, basket_id):
        """Usuwa koszyk"""
        baskets = self.load_baskets()
        if basket_id in baskets:
            del baskets[basket_id]
            
            with open(self.baskets_file, 'w', encoding='utf-8') as f:
                for basket in baskets.values():
                    f.write(json.dumps(basket, ensure_ascii=False) + '\n')
            return True
        return False
    
    def update_basket_settings(self, basket_id, optimization_settings, name=None):
        """Aktualizuje ustawienia optymalizacji koszyka"""
        basket = self.get_basket(basket_id)
        if not basket:
            return False
        
        basket['optimization_settings'] = optimization_settings
        if name:
            basket['name'] = name
        basket['updated'] = datetime.now().isoformat()
        
        self.save_basket(basket)
        return True
    
    def remove_item_from_basket(self, basket_id, product_id):
        """Usuwa produkt z koszyka"""
        basket = self.get_basket(basket_id)
        if not basket:
            return False
        
        product_key = str(product_id)
        if product_key in basket.get('basket_items', {}):
            del basket['basket_items'][product_key]
            basket['updated'] = datetime.now().isoformat()
            self.save_basket(basket)
            return True
        return False
    
    def optimize_basket(self, basket_id, products_data, prices_data, shop_configs):
        """Główny algorytm optymalizacji koszyka - PRZEPISANA WERSJA Z GRUPOWANIEM"""
        
        optimization_log = []
        
        def log(message):
            """Dodaj wpis do logu optymalizacji"""
            timestamp = datetime.now().strftime("%H:%M:%S")
            optimization_log.append(f"[{timestamp}] {message}")
        
        log("🚀 ROZPOCZĘCIE OPTYMALIZACJI KOSZYKA - NOWA WERSJA Z GRUPOWANIEM ZAMIENNIKÓW")
        
        # Pobierz koszyk
        basket = self.get_basket(basket_id)
        if not basket:
            log("❌ BŁĄD: Koszyk nie został znaleziony")
            return {'success': False, 'error': 'Koszyk nie został znaleziony'}
        
        if 'basket_items' not in basket or not basket['basket_items']:
            log("❌ BŁĄD: Koszyk jest pusty")
            return {'success': False, 'error': 'Koszyk jest pusty'}
        
        # Pobierz ustawienia
        settings = basket.get('optimization_settings', {})
        
        # Loguj wszystkie ustawienia szczegółowo
        self._log_basket_settings(basket, settings, log)
        
        # KROK 1: Normalizuj ceny do PLN
        log("💰 KROK 1: NORMALIZACJA CEN")
        normalized_prices = self._normalize_prices(prices_data, log)
        
        # KROK 2: Grupuj produkty w koszyku według grup zamienników
        log("🔗 KROK 2: GRUPOWANIE PRODUKTÓW ZAMIENNYCH")
        substitute_handler = SubstituteHandler(log)
        grouped_result = substitute_handler.group_substitute_products(basket, log)
        grouped_needs = grouped_result['groups']
        product_mapping = grouped_result['mapping']
        
        if not grouped_needs:
            log("❌ BŁĄD: Brak potrzeb po grupowaniu")
            return {'success': False, 'error': 'Brak potrzeb po grupowaniu'}
        
        # KROK 3: Rozszerz oferty o zamienniki dla zgrupowanych potrzeb
        log("🔄 KROK 3: ROZSZERZANIE OFERT DLA GRUP")
        expanded_offers = substitute_handler.expand_offers_with_substitutes_for_groups(
            grouped_needs, settings, log
        )
        
        if not expanded_offers or not any(expanded_offers.values()):
            log("❌ BŁĄD: Brak dostępnych ofert po grupowaniu")
            return {'success': False, 'error': 'Brak dostępnych ofert po grupowaniu'}
        
        # KROK 4: Znajdź najlepszą kombinację dla zgrupowanych potrzeb
        log("🧮 KROK 4: OPTYMALIZACJA KOMBINACJI DLA GRUP")
        best_combination = self._find_best_combination_for_groups(
            expanded_offers, grouped_needs, shop_configs, settings, log
        )
        
        if not best_combination:
            log("❌ BŁĄD: Nie znaleziono odpowiedniej kombinacji")
            return {'success': False, 'error': 'Nie znaleziono odpowiedniej kombinacji'}
        
        # KROK 5: Optymalizuj ilości
        log("📊 KROK 5: OPTYMALIZACJA ILOŚCI")
        quantity_optimizer = QuantityOptimizer(settings, log)
        optimized_result = quantity_optimizer.optimize_quantities_in_result(
            best_combination, shop_configs
        )
        
        # KROK 6: Podsumowanie
        log("✅ OPTYMALIZACJA ZAKOŃCZONA SUKCESEM!")
        self._log_final_summary(optimized_result, log)
        
        # Sprawdź optymalizacje
        optimizations_applied = sum(1 for item in optimized_result['items_list'] if item.get('quantity_optimized'))
        substitutes_used = sum(1 for item in optimized_result['items_list'] if item.get('is_substitute'))
        
        result = {
            'success': True,
            'basket_id': basket_id,
            'best_option': optimized_result,
            'optimized_at': datetime.now().isoformat(),
            'optimization_log': optimization_log,
            'show_logs': settings.get('show_logs', False),
            'optimizations_applied': optimizations_applied,
            'substitutes_used': substitutes_used,
            'grouped_needs': len(grouped_needs),  # NOWE: liczba potrzeb po grupowaniu
            'original_items': len(basket['basket_items'])  # NOWE: oryginalna liczba pozycji
        }
        
        basket['last_optimization'] = result['optimized_at']
        self.save_basket(basket)
        
        return result
    
    def _find_best_combination_for_groups(self, expanded_offers, grouped_needs, shop_configs, settings, log_func):
        """
        NOWA FUNKCJA: Znajduje najlepszą kombinację dla zgrupowanych potrzeb
        """
        priority = settings.get('priority', 'lowest_total_cost')
        max_shops = settings.get('max_shops', 5)
        
        need_keys = list(expanded_offers.keys())
        log_func(f"🔍 ANALIZA KOMBINACJI dla {len(need_keys)} zgrupowanych potrzeb")
        
        # Loguj podsumowanie ofert dla każdej potrzeby
        for i, need_key in enumerate(need_keys):
            offers = expanded_offers[need_key]
            need = grouped_needs[i]
            
            if need['type'] == 'substitute_group':
                log_func(f"   🔗 GRUPA {need['group_id']}: {len(offers)} ofert dla {need['total_quantity']} szt")
            else:
                log_func(f"   📦 PRODUKT {need['product_id']}: {len(offers)} ofert dla {need['quantity']} szt")
        
        # Sprawdź czy można użyć pełnego algorytmu
        if len(need_keys) > 7:
            log_func(f"⚠️ DUŻY KOSZYK ({len(need_keys)} potrzeb) - używam prostego algorytmu")
            return self._simple_optimization_for_groups(expanded_offers, grouped_needs, shop_configs, settings, log_func)
        
        # Generuj kombinacje
        offer_lists = [expanded_offers[need_key] for need_key in need_keys if expanded_offers[need_key]]
        
        if len(offer_lists) != len(need_keys):
            log_func("❌ BŁĄD: Niektóre potrzeby nie mają ofert")
            return None
            
        raw_combinations = list(itertools_product(*offer_lists))
        log_func(f"🔥 WYGENEROWANO {len(raw_combinations)} surowych kombinacji")
        
        # Filtruj według limitu sklepów
        valid_combinations = []
        for combo in raw_combinations:
            unique_shops = set(offer['shop_id'] for offer in combo)
            if len(unique_shops) <= max_shops:
                valid_combinations.append(combo)
        
        log_func(f"✂️ PO FILTROWANIU (max {max_shops} sklepów): {len(valid_combinations)} kombinacji")
        
        if not valid_combinations:
            log_func("❌ BŁĄD: Żadna kombinacja nie spełnia kryterium liczby sklepów")
            return self._simple_optimization_for_groups(expanded_offers, grouped_needs, shop_configs, settings, log_func)
        
        # Oceń kombinacje
        evaluator = CombinationEvaluator(settings, log_func)
        best_score = float('inf')
        best_combination = None
        
        for combo_idx, combination in enumerate(valid_combinations):
            log_func(f"KOMBINACJA #{combo_idx + 1}/{len(valid_combinations)}:")
            
            # Sprawdź czy kombinacja zawiera zamienniki
            substitutes_in_combo = [offer for offer in combination if offer.get('is_substitute', False)]
            if substitutes_in_combo:
                substitute_info = []
                for offer in substitutes_in_combo:
                    substitute_info.append(f"{offer.get('substitute_name', 'Zamiennik')} za {offer['price_pln']:.2f} PLN")
                log_func(f"   🔄 Zamienniki w kombinacji: {', '.join(substitute_info)}")
            
            # Przelicz kombinację dla grup
            result = self._calculate_combination_result_for_groups(
                combination, need_keys, grouped_needs, shop_configs, log_func
            )
            
            # Oblicz wynik
            score = evaluator.calculate_score(result)
            
            if score < best_score:
                best_score = score
                best_combination = result
                log_func(f"   ⭐ TO JEST NOWA NAJLEPSZA OPCJA! (wynik: {score:.2f})")
            else:
                difference = score - best_score
                log_func(f"   ❌ Gorsza od najlepszej o {difference:.2f}")
        
        return best_combination
    
    def _calculate_combination_result_for_groups(self, combination, need_keys, grouped_needs, shop_configs, log_func):
        """
        NOWA FUNKCJA: Przelicza kombinację na format wynikowy dla zgrupowanych potrzeb
        """
        
        # Grupuj produkty według sklepów
        shops_summary = {}
        items_list = []
        
        for i, offer in enumerate(combination):
            shop_id = offer['shop_id']
            need = grouped_needs[i]
            
            if need['type'] == 'substitute_group':
                # Obsługa grupy zamienników
                total_quantity = need['total_quantity']
                unit_price = offer['price_pln']
                
                # Znajdź nazwę produktu
                if offer.get('from_basket'):
                    # Produkt był w koszyku - użyj nazwy z koszyka
                    basket_product = next(
                        (p for p in need['products_in_basket'] if p['product_id'] == offer.get('basket_product_id')),
                        need['products_in_basket'][0]
                    )
                    product_name = f"{basket_product['product_name']} (grupa)"
                    actual_product_id = offer.get('basket_product_id', basket_product['product_id'])
                else:
                    # Produkt nie był w koszyku - to zamiennik
                    try:
                        from utils.data_utils import load_products
                        all_products = load_products()
                        substitute_product = next((p for p in all_products if p['id'] == offer['product_id']), None)
                        if substitute_product:
                            product_name = f"{substitute_product['name']} (zamiennik grupy)"
                        else:
                            product_name = f"Zamiennik {offer['product_id']} (grupa)"
                        actual_product_id = offer['product_id']
                    except:
                        product_name = f"Zamiennik {offer['product_id']} (grupa)"
                        actual_product_id = offer['product_id']
                
                # Utwórz pozycję dla całej grupy
                item_data = {
                    'product_id': need['products_in_basket'][0]['product_id'],  # Pierwszy z koszyka dla powiązania
                    'product_name': product_name,
                    'actual_product_id': actual_product_id,
                    'shop_id': shop_id,
                    'quantity': total_quantity,
                    'unit_price_pln': unit_price,
                    'total_price_pln': unit_price * total_quantity,
                    'is_substitute': offer.get('is_substitute', False),
                    'substitute_reason': offer.get('substitute_reason', ''),
                    'quantity_optimized': False,
                    'optimization_reason': '',
                    'is_group': True,
                    'group_id': need['group_id'],
                    'original_items_in_group': len(need['products_in_basket']),
                    'group_items_summary': ', '.join([f"{p['product_name']}({p['quantity']})" for p in need['products_in_basket']])
                }
                
                log_func(f"   🔗 GRUPA {need['group_id']}: {product_name} - {total_quantity} szt × {unit_price:.2f} PLN = {item_data['total_price_pln']:.2f} PLN")
                
            else:
                # Obsługa produktu indywidualnego
                product_id = need['product_id']
                quantity = need['quantity']
                unit_price = offer['price_pln']
                
                # Określ prawdziwy product_id i nazwę
                if offer.get('is_substitute', False):
                    actual_product_id = offer.get('substitute_product_id', offer['product_id'])
                    try:
                        from utils.data_utils import load_products
                        all_products = load_products()
                        substitute_product = next((p for p in all_products if p['id'] == actual_product_id), None)
                        if substitute_product:
                            product_name = f"{substitute_product['name']} (zamiennik)"
                        else:
                            product_name = f"Zamiennik {actual_product_id}"
                    except:
                        product_name = f"Zamiennik {actual_product_id}"
                else:
                    actual_product_id = product_id
                    product_name = need['product_name']
                
                item_data = {
                    'product_id': product_id,  # ID z koszyka (dla powiązania)
                    'product_name': product_name,
                    'actual_product_id': actual_product_id,
                    'shop_id': shop_id,
                    'quantity': quantity,
                    'unit_price_pln': unit_price,
                    'total_price_pln': unit_price * quantity,
                    'is_substitute': offer.get('is_substitute', False),
                    'substitute_reason': offer.get('substitute_reason', ''),
                    'quantity_optimized': False,
                    'optimization_reason': '',
                    'is_group': False
                }
                
                log_func(f"   📦 PRODUKT {product_id}: {product_name} - {quantity} szt × {unit_price:.2f} PLN = {item_data['total_price_pln']:.2f} PLN")
            
            if shop_id not in shops_summary:
                shops_summary[shop_id] = {
                    'items': [],
                    'subtotal': 0,
                    'shipping_cost': 0
                }
            
            shops_summary[shop_id]['items'].append(item_data)
            shops_summary[shop_id]['subtotal'] += item_data['total_price_pln']
            items_list.append(item_data)
        
        # Oblicz koszty dostawy
        total_products_cost = sum(item['total_price_pln'] for item in items_list)
        total_shipping_cost = 0
        
        for shop_id, summary in shops_summary.items():
            config = shop_configs.get(shop_id, {})
            free_from = config.get('delivery_free_from')
            shipping_cost = config.get('delivery_cost', 0)
            
            if free_from and summary['subtotal'] >= free_from:
                summary['shipping_cost'] = 0
                log_func(f"   🚚 {shop_id}: Darmowa dostawa (≥{free_from} PLN)")
            else:
                summary['shipping_cost'] = shipping_cost or 0
                log_func(f"   🚚 {shop_id}: Dostawa {summary['shipping_cost']:.2f} PLN")
            
            total_shipping_cost += summary['shipping_cost']
        
        total_cost = total_products_cost + total_shipping_cost
        
        # Loguj podsumowanie kombinacji
        log_func(f"   💵 Produkty: {total_products_cost:.2f} PLN")
        log_func(f"   🚚 Transport: {total_shipping_cost:.2f} PLN")
        log_func(f"   💳 RAZEM: {total_cost:.2f} PLN")
        
        return {
            'items_list': items_list,
            'shops_summary': shops_summary,
            'total_products_cost': total_products_cost,
            'total_shipping_cost': total_shipping_cost,
            'total_cost': total_cost,
            'shops_count': len(shops_summary)
        }
    
    def _simple_optimization_for_groups(self, expanded_offers, grouped_needs, shop_configs, settings, log_func):
        """NOWA FUNKCJA: Prosty algorytm - najlepsze oferty dla grup"""
        log_func("🔧 PROSTY ALGORYTM: Wybieranie najlepszych ofert dla każdej grupy/produktu")
        
        combination = []
        need_keys = list(expanded_offers.keys())
        
        for i, need_key in enumerate(need_keys):
            offers = expanded_offers[need_key]
            need = grouped_needs[i]
            
            if offers:
                best_offer = offers[0]  # Najtańsza (lista jest posortowana)
                combination.append(best_offer)
                
                # Loguj wybór
                if need['type'] == 'substitute_group':
                    if best_offer.get('is_substitute', False):
                        log_func(f"   🔗 GRUPA {need['group_id']}: wybrano ZAMIENNIK za {best_offer['price_pln']:.2f} PLN")
                    else:
                        log_func(f"   🔗 GRUPA {need['group_id']}: wybrano ORYGINALNY za {best_offer['price_pln']:.2f} PLN")
                else:
                    if best_offer.get('is_substitute', False):
                        log_func(f"   📦 PRODUKT {need['product_id']}: wybrano ZAMIENNIK za {best_offer['price_pln']:.2f} PLN")
                    else:
                        log_func(f"   📦 PRODUKT {need['product_id']}: wybrano ORYGINALNY za {best_offer['price_pln']:.2f} PLN")
        
        # Przelicz na wynik
        return self._calculate_combination_result_for_groups(
            combination, need_keys, grouped_needs, shop_configs, log_func
        )
    
    def _log_basket_settings(self, basket, settings, log_func):
        """Loguje wszystkie ustawienia koszyka"""
        log_func(f"📦 KOSZYK: {len(basket['basket_items'])} produktów")
        log_func(f"⚙️ USTAWIENIA OPTYMALIZACJI:")
        log_func(f"   🎯 Priorytet: {settings.get('priority', 'lowest_total_cost')}")
        log_func(f"   🏪 Max sklepów: {settings.get('max_shops', 5)}")
        log_func(f"   📈 Sugeruj ilości: {settings.get('suggest_quantities', False)}")
        log_func(f"   💰 Próg oszczędności: {settings.get('min_savings_threshold', 5.0)} PLN")
        log_func(f"   📊 Max mnożnik ilości: {settings.get('max_quantity_multiplier', 3)}")
        log_func(f"   🚚 Uwzględnij darmową dostawę: {settings.get('consider_free_shipping', True)}")
        
        substitute_settings = settings.get('substitute_settings', {})
        log_func(f"🔄 USTAWIENIA ZAMIENNIKÓW:")
        log_func(f"   ✅ Zezwalaj na zamienniki: {substitute_settings.get('allow_substitutes', True)}")
        log_func(f"   📈 Max wzrost ceny: {substitute_settings.get('max_price_increase_percent', 20.0)}%")
        log_func(f"   ⭐ Preferuj oryginal: {substitute_settings.get('prefer_original', True)}")
        log_func(f"   🔢 Max zamienników na produkt: {substitute_settings.get('max_substitutes_per_product', 3)}")
        
        # Loguj produkty w koszyku z potencjalnymi konfliktami grup
        log_func("📋 PRODUKTY W KOSZYKU:")
        
        # Sprawdź konflikty grup zamienników
        groups = substitute_manager.load_substitute_groups()
        product_to_group = {}
        for group_id, group_data in groups.items():
            for product_id in group_data['product_ids']:
                product_to_group[product_id] = group_id
        
        group_conflicts = {}
        for product_key, item in basket['basket_items'].items():
            product_id = item['product_id']
            group_id = product_to_group.get(product_id)
            
            if group_id:
                if group_id not in group_conflicts:
                    group_conflicts[group_id] = []
                group_conflicts[group_id].append(item)
        
        # Loguj konflikty
        for group_id, items in group_conflicts.items():
            if len(items) > 1:
                log_func(f"   ⚠️  KONFLIKT GRUPY {group_id}: {len(items)} produktów z tej samej grupy zamienników!")
                for item in items:
                    log_func(f"      • {item['product_name']} - {item['requested_quantity']} szt")
        
        # Loguj wszystkie produkty
        for product_key, item in basket['basket_items'].items():
            item_substitute_settings = item.get('substitute_settings', {})
            allow_subs = item_substitute_settings.get('allow_substitutes', True)
            max_increase = item_substitute_settings.get('max_price_increase_percent', 20.0)
            group_id = product_to_group.get(item['product_id'])
            
            group_info = f" (grupa {group_id})" if group_id else ""
            log_func(f"   • Produkt {item['product_id']}: {item['requested_quantity']} szt. ({item.get('product_name', 'bez nazwy')}){group_info}")
            log_func(f"     🔄 Zamienniki: {'TAK' if allow_subs else 'NIE'} (max +{max_increase}%)")
    
    def _normalize_prices(self, prices_data, log_func):
        """Normalizuje ceny do PLN"""
        fx_rates = {'PLN': 1.0, 'EUR': 4.30, 'USD': 4.00}
        normalized_prices = {}
        
        for key, price_info in prices_data.items():
            if price_info.get('price'):
                currency = price_info.get('currency', 'PLN')
                rate = fx_rates.get(currency, 1.0)
                
                normalized_prices[key] = {
                    'product_id': price_info['product_id'],
                    'shop_id': price_info['shop_id'],
                    'price_pln': price_info['price'] * rate,
                    'price_original': price_info['price'],
                    'currency': currency
                }
        
        log_func(f"💰 Znormalizowano {len(normalized_prices)} cen z {len(prices_data)} dostępnych")
        return normalized_prices
    
    def _find_available_offers(self, basket, normalized_prices, log_func):
        """Znajduje oferty dla produktów w koszyku"""
        available_offers = {}
        
        for product_key, item in basket['basket_items'].items():
            product_id = item['product_id']
            available_offers[product_id] = []
            
            for price_key, price_info in normalized_prices.items():
                if price_info['product_id'] == product_id:
                    available_offers[product_id].append(price_info)
            
            if available_offers[product_id]:
                available_offers[product_id].sort(key=lambda x: x['price_pln'])
                best_price = available_offers[product_id][0]['price_pln']
                worst_price = available_offers[product_id][-1]['price_pln']
                shop_count = len(available_offers[product_id])
                shops = [o['shop_id'] for o in available_offers[product_id]]
                log_func(f"   📊 Produkt {product_id}: {shop_count} ofert w sklepach: {', '.join(shops)}")
                log_func(f"      💲 Ceny: {best_price:.2f} PLN (najlepsze) - {worst_price:.2f} PLN (najgorsze)")
            else:
                log_func(f"   ❌ Produkt {product_id}: BRAK OFERT!")
        
        return available_offers
    
    def _find_best_combination(self, expanded_offers, basket, shop_configs, settings, log_func):
        """Znajduje najlepszą kombinację"""
        
        priority = settings.get('priority', 'lowest_total_cost')
        max_shops = settings.get('max_shops', 5)
        
        product_ids = list(expanded_offers.keys())
        log_func(f"🔍 ANALIZA KOMBINACJI dla {len(product_ids)} produktów")
        
        # Loguj podsumowanie ofert
        for product_id in product_ids:
            offers = expanded_offers[product_id]
            originals = [o for o in offers if not o.get('is_substitute', False)]
            substitutes = [o for o in offers if o.get('is_substitute', False)]
            log_func(f"   📦 Produkt {product_id}: {len(originals)} oryginalnych + {len(substitutes)} zamienników = {len(offers)} ofert")
        
        # Sprawdź czy można użyć pełnego algorytmu
        if len(product_ids) > 7:
            log_func(f"⚠️ DUŻY KOSZYK ({len(product_ids)} produktów) - używam prostego algorytmu")
            return self._simple_optimization(expanded_offers, basket, shop_configs, settings, log_func)
        
        # Generuj kombinacje
        offer_lists = [expanded_offers[pid] for pid in product_ids if expanded_offers[pid]]
        
        if len(offer_lists) != len(product_ids):
            log_func("❌ BŁĄD: Niektóre produkty nie mają ofert")
            return None
            
        raw_combinations = list(itertools_product(*offer_lists))
        log_func(f"🔥 WYGENEROWANO {len(raw_combinations)} surowych kombinacji")
        
        # Filtruj według limitu sklepów
        valid_combinations = []
        for combo in raw_combinations:
            unique_shops = set(offer['shop_id'] for offer in combo)
            if len(unique_shops) <= max_shops:
                valid_combinations.append(combo)
        
        log_func(f"✂️ PO FILTROWANIU (max {max_shops} sklepów): {len(valid_combinations)} kombinacji")
        
        if not valid_combinations:
            log_func("❌ BŁĄD: Żadna kombinacja nie spełnia kryterium liczby sklepów")
            return self._simple_optimization(expanded_offers, basket, shop_configs, settings, log_func)
        
        # Oceń kombinacje
        evaluator = CombinationEvaluator(settings, log_func)
        best_score = float('inf')
        best_combination = None
        
        for combo_idx, combination in enumerate(valid_combinations):
            log_func(f"KOMBINACJA #{combo_idx + 1}/{len(valid_combinations)}:")
            
            # Sprawdź czy kombinacja zawiera zamienniki
            substitutes_in_combo = [offer for offer in combination if offer.get('is_substitute', False)]
            if substitutes_in_combo:
                substitute_info = []
                for offer in substitutes_in_combo:
                    substitute_info.append(f"{offer.get('substitute_name', 'Zamiennik')} za {offer['price_pln']:.2f} PLN")
                log_func(f"   🔄 Zamienniki w kombinacji: {', '.join(substitute_info)}")
            
            # Przelicz kombinację
            result = evaluator.calculate_combination_result(
                combination, product_ids, basket, shop_configs
            )
            
            # Oblicz wynik
            score = evaluator.calculate_score(result)
            
            if score < best_score:
                best_score = score
                best_combination = result
                log_func(f"   ⭐ TO JEST NOWA NAJLEPSZA OPCJA! (wynik: {score:.2f})")
            else:
                difference = score - best_score
                log_func(f"   ❌ Gorsza od najlepszej o {difference:.2f}")
        
        return best_combination
    
    def _simple_optimization(self, expanded_offers, basket, shop_configs, settings, log_func):
        """Prosty algorytm - najlepsze oferty"""
        log_func("🔧 PROSTY ALGORYTM: Wybieranie najlepszych ofert dla każdego produktu")
        
        combination = []
        product_ids = []
        
        for product_id, offers in expanded_offers.items():
            if offers:
                best_offer = offers[0]  # Najtańsza (lista jest posortowana)
                combination.append(best_offer)
                product_ids.append(product_id)
                
                # Loguj wybór
                if best_offer.get('is_substitute', False):
                    sub_name = best_offer.get('substitute_name', f'Zamiennik {best_offer.get("substitute_product_id")}')
                    log_func(f"   🔄 Produkt {product_id}: wybrano ZAMIENNIK '{sub_name}' za {best_offer['price_pln']:.2f} PLN")
                else:
                    log_func(f"   ✅ Produkt {product_id}: wybrano ORYGINALNY za {best_offer['price_pln']:.2f} PLN")
        
        # Przelicz na wynik
        evaluator = CombinationEvaluator(settings, log_func)
        return evaluator.calculate_combination_result(
            combination, product_ids, basket, shop_configs
        )
    
    def _log_final_summary(self, result, log_func):
        """Loguje końcowe podsumowanie"""
        log_func(f"🏆 WYNIK KOŃCOWY:")
        log_func(f"   🏪 Sklepy: {', '.join(result['shops_summary'].keys())}")
        log_func(f"   💵 Produkty: {result['total_products_cost']:.2f} PLN")
        log_func(f"   🚚 Transport: {result['total_shipping_cost']:.2f} PLN")
        log_func(f"   💳 RAZEM: {result['total_cost']:.2f} PLN")
        
        # Sprawdź optymalizacje
        optimizations = [item for item in result['items_list'] if item.get('quantity_optimized')]
        substitutes = [item for item in result['items_list'] if item.get('is_substitute')]
        groups = [item for item in result['items_list'] if item.get('is_group')]
        
        if groups:
            log_func("🔗 ZGRUPOWANE POTRZEBY:")
            for item in groups:
                original_count = item.get('original_items_in_group', 1)
                log_func(f"   • {item['product_name']}: połączono {original_count} pozycji z koszyka")
                if item.get('group_items_summary'):
                    log_func(f"     📋 Oryginalne pozycje: {item['group_items_summary']}")
        
        if optimizations:
            log_func("🔢 OPTYMALIZACJE ILOŚCI:")
            for item in optimizations:
                product_name = item.get('product_name', f'Produkt {item["product_id"]}')
                reason = item.get('optimization_reason', 'zwiększono ilość')
                log_func(f"   • {product_name}: {reason}")
        
        if substitutes:
            log_func("🔄 UŻYTE ZAMIENNIKI:")
            for item in substitutes:
                product_name = item.get('product_name', f'Produkt {item["product_id"]}')
                reason = item.get('substitute_reason', 'użyto zamiennik')
                log_func(f"   • {product_name}: {reason}")

# Singleton instance
basket_manager = BasketManager()