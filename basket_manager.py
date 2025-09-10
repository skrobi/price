"""
Główny moduł zarządzania koszykami - POPRAWIONY z lepszą obsługą nowego silnika
"""
import json
import os
from datetime import datetime

class BasketManager:
    """Zarządzanie koszykami z wydzielonym silnikiem optymalizacji"""
    
    def __init__(self):
        self.baskets_file = 'data/baskets.txt'
        self.ensure_data_dir()
    
    def ensure_data_dir(self):
        """Upewnij się że folder data istnieje"""
        if not os.path.exists('data'):
            os.makedirs('data')
    
    def optimize_basket(self, basket_id, products_data, prices_data, shop_configs):
        """GŁÓWNY ALGORYTM OPTYMALIZACJI - używa nowego silnika"""
        
        optimization_log = []
        
        def log(message):
            """Dodaj wpis do logu optymalizacji"""
            timestamp = datetime.now().strftime("%H:%M:%S")
            optimization_log.append(f"[{timestamp}] {message}")
            print(f"BASKET_MANAGER LOG: {message}")
        
        log("🚀 ROZPOCZĘCIE OPTYMALIZACJI - POPRAWIONY SILNIK")
        
        # Pobierz koszyk
        basket = self.get_basket(basket_id)
        if not basket:
            log("❌ BŁĄD: Koszyk nie został znaleziony")
            return {'success': False, 'error': 'Koszyk nie został znaleziony', 'optimization_log': optimization_log}
        
        if 'basket_items' not in basket or not basket['basket_items']:
            log("❌ BŁĄD: Koszyk jest pusty")
            return {'success': False, 'error': 'Koszyk jest pusty', 'optimization_log': optimization_log}
        
        # Pobierz i zwaliduj ustawienia
        settings = basket.get('optimization_settings', {})
        settings = self._validate_and_fix_settings(settings, log)
        
        # Loguj wszystkie ustawienia
        self._log_all_settings(basket, settings, log)
        
        try:
            # UŻYJ NOWEGO SILNIKA OPTYMALIZACJI
            log("🔥 Importowanie OptimizationEngine...")
            from optimization_engine import OptimizationEngine
            log("✅ Import sukces!")
            
            log("🎯 Tworzenie engine...")
            engine = OptimizationEngine(settings, log)
            log("✅ Engine utworzony!")
            
            log("🧮 Wywołuję engine.optimize_basket...")
            result = engine.optimize_basket(basket, products_data, prices_data, shop_configs)
            log(f"✅ Engine zwrócił result: success={result.get('success')}")
            
            if result['success']:
                # Sprawdź czy znaleziono rozwiązanie w limicie sklepów
                best_option = result.get('best_option', {})
                
                if best_option.get('error_type') == 'shop_limit_too_low':
                    # Specjalna obsługa błędu limitu sklepów
                    min_required = best_option.get('min_shops_required', 0)
                    current_limit = settings.get('max_shops', 5)
                    
                    log(f"🚨 LIMIT SKLEPÓW ZA NISKI!")
                    log(f"   Obecny limit: {current_limit}")
                    log(f"   Wymagane minimum: {min_required}")
                    log(f"   Sugestia: Zwiększ limit do {min_required}")
                    
                    return {
                        'success': False,
                        'error': f'Nie można zrealizować koszyka w {current_limit} sklepach. Potrzeba minimum {min_required} sklepów.',
                        'error_type': 'shop_limit_too_low',
                        'current_shop_limit': current_limit,
                        'min_shops_required': min_required,
                        'suggestion': f'Zwiększ limit sklepów do co najmniej {min_required} w ustawieniach koszyka.',
                        'optimization_log': optimization_log,
                        'show_logs': True
                    }
                
                # Dodaj logi do wyniku
                result['optimization_log'] = optimization_log
                result['show_logs'] = settings.get('show_logs', False)
                
                # Zapisz informacje o ostatniej optymalizacji
                basket['last_optimization'] = result['optimized_at']
                basket['optimization_settings'] = settings  # Zapisz poprawione ustawienia
                self.save_basket(basket)
                
                log("✅ OPTYMALIZACJA ZAKOŃCZONA SUKCESEM!")
                self._log_final_summary(result['best_option'], log)
                
                return result
            else:
                result['optimization_log'] = optimization_log
                result['show_logs'] = True  # Zawsze pokażj logi gdy błąd
                log(f"❌ OPTYMALIZACJA NIEUDANA: {result.get('error', 'Nieznany błąd')}")
                return result
                
        except ImportError as e:
            log(f"💥 BŁĄD IMPORTU OptimizationEngine: {str(e)}")
            log("📁 Sprawdź czy plik optimization_engine.py istnieje w tym samym katalogu")
            
            return {
                'success': False,
                'error': f'Błąd importu nowego silnika: {str(e)}. Sprawdź czy plik optimization_engine.py istnieje.',
                'error_type': 'import_error',
                'optimization_log': optimization_log,
                'show_logs': True
            }
            
        except Exception as e:
            log(f"💥 KRYTYCZNY BŁĄD w silniku optymalizacji: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'error': f'Błąd w silniku optymalizacji: {str(e)}',
                'error_type': 'optimization_error',
                'optimization_log': optimization_log,
                'show_logs': True
            }
    
    def _validate_and_fix_settings(self, settings, log_func):
        """Waliduje i naprawia ustawienia optymalizacji"""
        
        log_func("🔧 WALIDACJA USTAWIEŃ:")
        
        # Domyślne ustawienia
        default_settings = {
            'priority': 'lowest_total_cost',
            'max_shops': 5,
            'suggest_quantities': False,
            'min_savings_threshold': 5.0,
            'max_quantity_multiplier': 3,
            'consider_free_shipping': True,
            'show_logs': False,
            'max_combinations': 200000,
            'substitute_settings': {
                'allow_substitutes': True,
                'max_price_increase_percent': 20.0,
                'prefer_original': True,
                'max_substitutes_per_product': 3,
                'show_substitute_reasons': True
            }
        }
        
        # Napraw brakujące ustawienia
        fixed_settings = default_settings.copy()
        fixed_settings.update(settings)
        
        # Waliduj wartości numeryczne
        try:
            fixed_settings['max_shops'] = max(1, min(20, int(fixed_settings['max_shops'])))
            fixed_settings['min_savings_threshold'] = max(0, float(fixed_settings['min_savings_threshold']))
            fixed_settings['max_quantity_multiplier'] = max(1, min(10, int(fixed_settings['max_quantity_multiplier'])))
            fixed_settings['max_combinations'] = max(1000, min(2000000, int(fixed_settings['max_combinations'])))
        except (ValueError, TypeError) as e:
            log_func(f"   ⚠️ Błąd walidacji numerycznej: {e}, używam domyślnych")
            
        # Waliduj ustawienia zamienników
        substitute_settings = fixed_settings.get('substitute_settings', {})
        default_substitute = default_settings['substitute_settings']
        
        for key, default_value in default_substitute.items():
            if key not in substitute_settings:
                substitute_settings[key] = default_value
                log_func(f"   🔧 Dodano brakujące: {key} = {default_value}")
        
        try:
            substitute_settings['max_price_increase_percent'] = max(0, min(100, float(substitute_settings['max_price_increase_percent'])))
            substitute_settings['max_substitutes_per_product'] = max(1, min(10, int(substitute_settings['max_substitutes_per_product'])))
        except (ValueError, TypeError):
            log_func("   ⚠️ Błąd walidacji zamienników, używam domyślnych")
            substitute_settings.update(default_substitute)
        
        fixed_settings['substitute_settings'] = substitute_settings
        
        # Waliduj priority
        valid_priorities = ['lowest_total_cost', 'fewest_shops', 'balanced']
        if fixed_settings['priority'] not in valid_priorities:
            fixed_settings['priority'] = 'lowest_total_cost'
            log_func(f"   🔧 Nieprawidłowy priorytet, ustawiam: lowest_total_cost")
        
        log_func("   ✅ Walidacja zakończona")
        return fixed_settings
    
    def _log_all_settings(self, basket, settings, log_func):
        """Loguje WSZYSTKIE ustawienia koszyka"""
        log_func(f"📦 KOSZYK: {len(basket['basket_items'])} produktów")
        log_func(f"⚙️ WSZYSTKIE USTAWIENIA OPTYMALIZACJI:")
        
        # Podstawowe ustawienia
        log_func(f"   🎯 Priorytet: {settings.get('priority', 'lowest_total_cost')}")
        log_func(f"   🏪 Max sklepów: {settings.get('max_shops', 5)} ⚠️ BĘDZIE EGZEKWOWANY!")
        log_func(f"   🔥 Max kombinacji: {settings.get('max_combinations', 200000):,}")
        log_func(f"   📈 Sugeruj ilości: {settings.get('suggest_quantities', False)}")
        log_func(f"   💰 Próg oszczędności: {settings.get('min_savings_threshold', 5.0)} PLN")
        log_func(f"   📊 Max mnożnik ilości: {settings.get('max_quantity_multiplier', 3)}")
        log_func(f"   🚚 Uwzględnij darmową dostawę: {settings.get('consider_free_shipping', True)}")
        log_func(f"   📋 Pokazuj logi: {settings.get('show_logs', False)}")
        
        # Ustawienia zamienników
        substitute_settings = settings.get('substitute_settings', {})
        log_func(f"🔄 USTAWIENIA ZAMIENNIKÓW:")
        log_func(f"   ✅ Zezwalaj na zamienniki: {substitute_settings.get('allow_substitutes', True)}")
        log_func(f"   📈 Max wzrost ceny: {substitute_settings.get('max_price_increase_percent', 20.0)}%")
        log_func(f"   ⭐ Preferuj oryginał: {substitute_settings.get('prefer_original', True)}")
        log_func(f"   🔢 Max zamienników na produkt: {substitute_settings.get('max_substitutes_per_product', 3)}")
        log_func(f"   📝 Pokazuj powody zastąpień: {substitute_settings.get('show_substitute_reasons', True)}")
    
    def _log_final_summary(self, result, log_func):
        """Loguje końcowe podsumowanie"""
        log_func(f"🏆 WYNIK KOŃCOWY:")
        log_func(f"   🏪 Sklepy: {', '.join(result['shops_summary'].keys())}")
        log_func(f"   💵 Produkty: {result['total_products_cost']:.2f} PLN")
        log_func(f"   🚚 Transport: {result['total_shipping_cost']:.2f} PLN")
        log_func(f"   💳 RAZEM: {result['total_cost']:.2f} PLN")
        log_func(f"   🏪 Liczba sklepów: {result['shops_count']}")
        
        optimizations = [item for item in result['items_list'] if item.get('quantity_optimized')]
        substitutes = [item for item in result['items_list'] if item.get('is_substitute')]
        groups = [item for item in result['items_list'] if item.get('is_group')]
        
        if optimizations:
            log_func(f"   📊 Optymalizacje ilości: {len(optimizations)} produktów")
        if substitutes:
            log_func(f"   🔄 Użyte zamienniki: {len(substitutes)} produktów")
        if groups:
            log_func(f"   🔗 Połączone grupy: {len(groups)} grup")
    
    # ===== POZOSTAŁE METODY BEZ ZMIAN =====
    
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
                            
                            # DODAJ DOMYŚLNE USTAWIENIA ZAMIENNIKÓW jeśli nie istnieją
                            if 'optimization_settings' not in basket:
                                basket['optimization_settings'] = {}
                            
                            # Upewnij się że wszystkie wymagane ustawienia istnieją
                            default_optimization = {
                                'priority': 'lowest_total_cost',
                                'max_shops': 5,
                                'suggest_quantities': False,
                                'min_savings_threshold': 5.0,
                                'max_quantity_multiplier': 3,
                                'consider_free_shipping': True,
                                'show_logs': False,
                                'max_combinations': 200000
                            }
                            
                            for key, default_value in default_optimization.items():
                                if key not in basket['optimization_settings']:
                                    basket['optimization_settings'][key] = default_value
                            
                            if 'substitute_settings' not in basket['optimization_settings']:
                                basket['optimization_settings']['substitute_settings'] = {
                                    'allow_substitutes': True,
                                    'max_price_increase_percent': 20.0,
                                    'prefer_original': True,
                                    'max_substitutes_per_product': 3,
                                    'show_substitute_reasons': True
                                }
                            
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
    
    def create_new_basket(self, name, optimization_settings=None):
        """Tworzy nowy koszyk"""
        basket_id = f"basket_{int(datetime.now().timestamp())}"
        
        if optimization_settings is None:
            optimization_settings = {
                'priority': 'lowest_total_cost',
                'max_shops': 5,
                'suggest_quantities': False,
                'min_savings_threshold': 5.0,
                'max_quantity_multiplier': 3,
                'consider_free_shipping': True,
                'show_logs': False,
                'max_combinations': 200000,
                'substitute_settings': {
                    'allow_substitutes': True,
                    'max_price_increase_percent': 20.0,
                    'prefer_original': True,
                    'max_substitutes_per_product': 3,
                    'show_substitute_reasons': True
                }
            }
        
        basket_data = {
            'basket_id': basket_id,
            'name': name,
            'created': datetime.now().isoformat(),
            'updated': datetime.now().isoformat(),
            'basket_items': {},
            'optimization_settings': optimization_settings
        }
        
        self.save_basket(basket_data)
        return basket_id
    
    def add_item_to_basket(self, basket_id, product_id, quantity, product_name=''):
        """Dodaje produkt do koszyka"""
        basket = self.get_basket(basket_id)
        if not basket:
            return False
        
        product_key = str(product_id)
        
        if product_key in basket['basket_items']:
            # Jeśli już istnieje, zwiększ ilość
            basket['basket_items'][product_key]['requested_quantity'] += quantity
            basket['basket_items'][product_key]['suggested_quantity'] += quantity
        else:
            # Dodaj nowy produkt z domyślnymi ustawieniami zamienników
            basket['basket_items'][product_key] = {
                'product_id': product_id,
                'product_name': product_name,
                'requested_quantity': quantity,
                'suggested_quantity': quantity,
                'added_at': datetime.now().isoformat(),
                # NOWE: Ustawienia zamienników dla konkretnego produktu
                'substitute_settings': {
                    'allow_substitutes': True,
                    'max_price_increase_percent': 20.0
                }
            }
        
        basket['updated'] = datetime.now().isoformat()
        self.save_basket(basket)
        return True
    
    def remove_item_from_basket(self, basket_id, product_id):
        """Usuwa produkt z koszyka"""
        basket = self.get_basket(basket_id)
        if not basket:
            return False
        
        product_key = str(product_id)
        if product_key in basket['basket_items']:
            del basket['basket_items'][product_key]
            basket['updated'] = datetime.now().isoformat()
            self.save_basket(basket)
            return True
        
        return False
    
    def update_basket_settings(self, basket_id, optimization_settings, name=None):
        """Aktualizuje ustawienia koszyka"""
        basket = self.get_basket(basket_id)
        if not basket:
            return False
        
        # UPEWNIJ SIĘ ŻE WSZYSTKIE USTAWIENIA SĄ ZACHOWANE
        current_settings = basket.get('optimization_settings', {})
        current_substitute_settings = current_settings.get('substitute_settings', {})
        
        # Zachowaj istniejące ustawienia zamienników jeśli nie podano nowych
        if 'substitute_settings' not in optimization_settings:
            optimization_settings['substitute_settings'] = current_substitute_settings
        else:
            # Połącz nowe z istniejącymi
            merged_substitute_settings = current_substitute_settings.copy()
            merged_substitute_settings.update(optimization_settings['substitute_settings'])
            optimization_settings['substitute_settings'] = merged_substitute_settings
        
        # Dodaj max_combinations jeśli nie istnieje
        if 'max_combinations' not in optimization_settings:
            optimization_settings['max_combinations'] = current_settings.get('max_combinations', 200000)
        
        # WALIDUJ USTAWIENIA
        try:
            optimization_settings['max_shops'] = max(1, min(20, int(optimization_settings.get('max_shops', 5))))
            optimization_settings['max_combinations'] = max(1000, min(2000000, int(optimization_settings.get('max_combinations', 200000))))
        except (ValueError, TypeError):
            pass  # Zostaw bez zmian jeśli błąd konwersji
        
        basket['optimization_settings'] = optimization_settings
        
        if name:
            basket['name'] = name
        
        basket['updated'] = datetime.now().isoformat()
        self.save_basket(basket)
        return True
    
    def update_item_substitute_settings(self, basket_id, product_id, allow_substitutes, max_price_increase_percent):
        """Aktualizuje ustawienia zamienników dla konkretnego produktu"""
        basket = self.get_basket(basket_id)
        if not basket:
            return False
        
        product_key = str(product_id)
        if product_key not in basket['basket_items']:
            return False
        
        basket['basket_items'][product_key]['substitute_settings'] = {
            'allow_substitutes': allow_substitutes,
            'max_price_increase_percent': max_price_increase_percent
        }
        
        basket['updated'] = datetime.now().isoformat()
        self.save_basket(basket)
        return True
    
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

# Singleton instance
basket_manager = BasketManager()