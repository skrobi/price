print("🔥🔥🔥 OPTIMIZATION_ENGINE: POPRAWIONY PLIK ZAŁADOWANY! 🔥🔥🔥")

"""
Silnik optymalizacji koszyków - POPRAWIONA WERSJA z działającym limitem sklepów
Ulepszone algorytmy z wieloma strategiami optymalizacji
"""
import copy
from datetime import datetime
from itertools import product as itertools_product, combinations
import random
import math

class OptimizationEngine:
    """Główny silnik optymalizacji koszyków - POPRAWIONA WERSJA"""
    
    def __init__(self, settings, log_func):
        self.settings = settings
        self.log = log_func
        
        # WSZYSTKIE USTAWIENIA Z BASKET_SETTINGS
        self.priority = settings.get('priority', 'lowest_total_cost')
        self.max_shops = settings.get('max_shops', 5)
        self.suggest_quantities = settings.get('suggest_quantities', False)
        self.min_savings_threshold = settings.get('min_savings_threshold', 5.0)
        self.max_quantity_multiplier = settings.get('max_quantity_multiplier', 3)
        self.consider_free_shipping = settings.get('consider_free_shipping', True)
        self.show_logs = settings.get('show_logs', False)
        
        # USTAWIENIA ZAMIENNIKÓW
        substitute_settings = settings.get('substitute_settings', {})
        self.allow_substitutes = substitute_settings.get('allow_substitutes', True)
        self.max_price_increase_percent = substitute_settings.get('max_price_increase_percent', 20.0)
        self.prefer_original = substitute_settings.get('prefer_original', True)
        self.max_substitutes_per_product = substitute_settings.get('max_substitutes_per_product', 3)
        self.show_substitute_reasons = substitute_settings.get('show_substitute_reasons', True)
        
        # KONFIGURACJA ALGORYTMU
        self.MAX_COMBINATIONS = settings.get('max_combinations', 200000)
        
        # NOWE: Statystyki wydajności
        self.stats = {
            'combinations_evaluated': 0,
            'combinations_filtered_by_shops': 0,
            'combinations_within_limit': 0,
            'optimization_strategies_used': []
        }
        
        self.log(f"🎯 SILNIK OPTYMALIZACJI - POPRAWIONA WERSJA:")
        self.log(f"   Priority: {self.priority}")
        self.log(f"   Max shops: {self.max_shops} ⚠️ BĘDZIE EGZEKWOWANY!")
        self.log(f"   Max combinations: {self.MAX_COMBINATIONS}")
        self.log(f"   Allow substitutes: {self.allow_substitutes}")
        self.log(f"   Max price increase: {self.max_price_increase_percent}%")
        self.log(f"   Prefer original: {self.prefer_original}")
        self.log(f"   Suggest quantities: {self.suggest_quantities}")
        self.log(f"   Consider free shipping: {self.consider_free_shipping}")
    
    def optimize_basket(self, basket, products_data, prices_data, shop_configs):
        """GŁÓWNA FUNKCJA OPTYMALIZACJI - POPRAWIONA"""
        
        self.log("🚀 ROZPOCZĘCIE OPTYMALIZACJI - POPRAWIONY SILNIK")
        
        # KROK 1: Normalizuj ceny
        self.log("💰 KROK 1: NORMALIZACJA CEN")
        normalized_prices = self._normalize_prices(prices_data)
        
        # KROK 2: Grupuj produkty zamienne (ŁĄCZ ILOŚCI!)
        self.log("🔗 KROK 2: GRUPOWANIE ZAMIENNIKÓW Z ŁĄCZENIEM ILOŚCI")
        grouped_needs = self._group_substitute_products_with_combining(basket)
        
        if not grouped_needs:
            self.log("❌ BŁĄD: Brak potrzeb po grupowaniu")
            return {'success': False, 'error': 'Brak potrzeb po grupowaniu'}
        
        # KROK 3: Rozszerz oferty o zamienniki
        self.log("🔄 KROK 3: ROZSZERZANIE OFERT O ZAMIENNIKI")
        expanded_offers, products_without_offers = self._expand_offers_with_substitutes(
            grouped_needs, normalized_prices
        )
        
        # KROK 4: ULEPSZONE ALGORYTMY Z EGZEKWOWANIEM LIMITU SKLEPÓW
        self.log("🧮 KROK 4: ALGORYTMY Z LIMITEM SKLEPÓW")
        best_combination = self._optimization_with_shop_limit_enforcement(
            expanded_offers, grouped_needs, shop_configs
        )
        
        if not best_combination:
            self.log("❌ BŁĄD: Nie znaleziono kombinacji w limicie sklepów")
            return self._create_no_offers_result(basket['basket_id'], grouped_needs, products_without_offers)
        
        # KROK 5: Optymalizuj ilości (jeśli włączone)
        if self.suggest_quantities and self.consider_free_shipping:
            self.log("📊 KROK 5: OPTYMALIZACJA ILOŚCI DLA DARMOWEJ DOSTAWY")
            best_combination = self._optimize_quantities(best_combination, shop_configs)
        
        # KROK 6: Dodaj produkty bez ofert
        if products_without_offers:
            self.log("📝 KROK 6: DODAWANIE PRODUKTÓW DO UZUPEŁNIENIA")
            best_combination['products_to_complete'] = self._create_completion_section(products_without_offers)
        
        # KROK 7: Loguj statystyki
        self._log_optimization_stats()
        
        self.log("✅ OPTYMALIZACJA ZAKOŃCZONA SUKCESEM!")
        return {
            'success': True,
            'basket_id': basket['basket_id'],
            'best_option': best_combination,
            'optimized_at': datetime.now().isoformat(),
            'optimizations_applied': sum(1 for item in best_combination['items_list'] if item.get('quantity_optimized')),
            'substitutes_used': sum(1 for item in best_combination['items_list'] if item.get('is_substitute')),
            'grouped_needs': len(grouped_needs),
            'original_items': len(basket['basket_items']),
            'products_without_offers': len(products_without_offers),
            'optimization_stats': self.stats
        }
    
    def _optimization_with_shop_limit_enforcement(self, expanded_offers, grouped_needs, shop_configs):
        """NOWA FUNKCJA: Optymalizacja z BEZWZGLĘDNYM egzekwowaniem limitu sklepów"""
        
        need_keys = list(expanded_offers.keys())
        need_keys = [key for key in need_keys if expanded_offers[key]]  # Usuń puste
        
        if not need_keys:
            self.log("❌ Brak potrzeb z ofertami")
            return None
        
        self.log(f"🔒 EGZEKWOWANIE LIMITU SKLEPÓW: maksymalnie {self.max_shops} sklepów")
        
        # STRATEGIA 1: Próbuj znaleźć rozwiązania w limicie sklepów
        self.log("🎯 STRATEGIA 1: Szukanie w limicie sklepów")
        best_combination = self._find_solutions_within_shop_limit(
            expanded_offers, need_keys, grouped_needs, shop_configs
        )
        
        if best_combination:
            self.log(f"✅ ZNALEZIONO ROZWIĄZANIE w {best_combination['shops_count']} sklepach")
            return best_combination
        
        # STRATEGIA 2: Jeśli nie ma rozwiązań w limicie, sprawdź czy to możliwe
        self.log("⚠️ STRATEGIA 2: Analiza dostępności w limicie sklepów")
        min_shops_required = self._calculate_minimum_shops_required(expanded_offers, need_keys)
        
        self.log(f"📊 Minimalna liczba sklepów potrzebna: {min_shops_required}")
        self.log(f"📊 Limit ustawiony przez użytkownika: {self.max_shops}")
        
        if min_shops_required > self.max_shops:
            self.log(f"🚨 NIEMOŻLIWE: Potrzeba minimum {min_shops_required} sklepów")
            self.log(f"💡 SUGESTIA: Zwiększ limit sklepów do co najmniej {min_shops_required}")
            
            # OPCJA A: Zwróć błąd z sugestią
            return {
                'items_list': [],
                'shops_summary': {},
                'total_products_cost': 0,
                'total_shipping_cost': 0,
                'total_cost': 0,
                'shops_count': 0,
                'error_type': 'shop_limit_too_low',
                'min_shops_required': min_shops_required,
                'suggestion': f'Zwiększ limit sklepów do co najmniej {min_shops_required}'
            }
        
        # STRATEGIA 3: Ostatnia szansa - ulepszone algorytmy
        self.log("🔥 STRATEGIA 3: Zaawansowane algorytmy w limicie")
        return self._advanced_shop_limited_optimization(
            expanded_offers, need_keys, grouped_needs, shop_configs
        )
    
    def _find_solutions_within_shop_limit(self, expanded_offers, need_keys, grouped_needs, shop_configs):
        """Znajdź rozwiązania TYLKO w limicie sklepów"""
        
        # Sprawdź rozmiar przestrzeni
        offer_counts = [len(expanded_offers[key]) for key in need_keys]
        total_combinations = 1
        for count in offer_counts:
            total_combinations *= count
            if total_combinations > self.MAX_COMBINATIONS * 10:  # Przerwij wcześnie
                break
        
        if total_combinations <= self.MAX_COMBINATIONS:
            self.log(f"⚡ PEŁNE PRZESZUKIWANIE: {total_combinations:,} kombinacji")
            return self._exhaustive_search_with_shop_filter(
                expanded_offers, need_keys, grouped_needs, shop_configs
            )
        else:
            self.log(f"🎯 PRÓBKOWANIE: z {total_combinations:,} możliwych kombinacji")
            return self._smart_sampling_with_shop_filter(
                expanded_offers, need_keys, grouped_needs, shop_configs
            )
    
    def _exhaustive_search_with_shop_filter(self, expanded_offers, need_keys, grouped_needs, shop_configs):
        """Pełne przeszukiwanie z filtrowaniem po sklepach"""
        
        offer_lists = [expanded_offers[need_key] for need_key in need_keys]
        all_combinations = list(itertools_product(*offer_lists))
        
        self.log(f"🔍 Filtrowanie {len(all_combinations):,} kombinacji przez limit {self.max_shops} sklepów")
        
        valid_combinations = []
        shops_distribution = {}
        
        for combo in all_combinations:
            self.stats['combinations_evaluated'] += 1
            
            unique_shops = set(offer['shop_id'] for offer in combo)
            shop_count = len(unique_shops)
            shops_distribution[shop_count] = shops_distribution.get(shop_count, 0) + 1
            
            # TYLKO kombinacje w limicie sklepów
            if shop_count <= self.max_shops:
                valid_combinations.append(combo)
                self.stats['combinations_within_limit'] += 1
            else:
                self.stats['combinations_filtered_by_shops'] += 1
        
        # Loguj statystyki filtrowania
        self.log(f"📊 ROZKŁAD LICZBY SKLEPÓW:")
        for shops_count in sorted(shops_distribution.keys()):
            count = shops_distribution[shops_count]
            status = "✅" if shops_count <= self.max_shops else "🚫"
            self.log(f"   {status} {shops_count} sklepów: {count:,} kombinacji")
        
        self.log(f"✅ KOMBINACJE W LIMICIE: {len(valid_combinations):,}")
        self.log(f"🚫 ODRZUCONE: {self.stats['combinations_filtered_by_shops']:,}")
        
        if not valid_combinations:
            self.log("❌ BRAK KOMBINACJI W LIMICIE SKLEPÓW")
            return None
        
        return self._evaluate_combinations(valid_combinations, need_keys, grouped_needs, shop_configs)
    
    def _smart_sampling_with_shop_filter(self, expanded_offers, need_keys, grouped_needs, shop_configs):
        """Inteligentne próbkowanie z filtrowaniem sklepów"""
        
        self.log(f"🎲 PRÓBKOWANIE z limitem {self.max_shops} sklepów")
        self.stats['optimization_strategies_used'].append('smart_sampling')
        
        # STRATEGIA A: Próbkowanie najbliższe optymalnemu
        valid_combinations = []
        offer_lists = [expanded_offers[need_key] for need_key in need_keys]
        
        # 1. Najlepsze oferty z każdej potrzeby
        best_offers_combo = [offers[0] for offers in offer_lists if offers]
        if best_offers_combo and len(set(offer['shop_id'] for offer in best_offers_combo)) <= self.max_shops:
            valid_combinations.append(best_offers_combo)
            self.log("✅ Dodano kombinację z najlepszych ofert")
        
        # 2. Kombinacje skupione wokół popularnych sklepów
        shop_popularity = self._calculate_shop_popularity(expanded_offers, need_keys)
        popular_shops = sorted(shop_popularity.keys(), key=lambda x: shop_popularity[x], reverse=True)
        
        for shop_combination in combinations(popular_shops, min(self.max_shops, len(popular_shops))):
            limited_combinations = self._generate_combinations_for_shops(
                expanded_offers, need_keys, shop_combination
            )
            valid_combinations.extend(limited_combinations[:100])  # Ogranicz ilość
            
            if len(valid_combinations) >= self.MAX_COMBINATIONS:
                break
        
        # 3. Losowe próbkowanie z filtrowaniem
        random.seed(42)
        attempts = 0
        max_attempts = self.MAX_COMBINATIONS * 5
        
        while len(valid_combinations) < self.MAX_COMBINATIONS and attempts < max_attempts:
            combo = []
            for offers in offer_lists:
                if offers:
                    # Ważone losowanie - większe prawdopodobieństwo dla tańszych
                    weights = [1/max(0.01, offer['price_pln']) for offer in offers]
                    combo.append(random.choices(offers, weights=weights)[0])
            
            if combo:
                unique_shops = set(offer['shop_id'] for offer in combo)
                if len(unique_shops) <= self.max_shops:
                    if combo not in valid_combinations:
                        valid_combinations.append(combo)
                        self.stats['combinations_within_limit'] += 1
                else:
                    self.stats['combinations_filtered_by_shops'] += 1
            
            attempts += 1
            self.stats['combinations_evaluated'] += 1
        
        self.log(f"🎯 Wygenerowano {len(valid_combinations):,} kombinacji w limicie")
        self.log(f"📊 Próby: {attempts:,} z {max_attempts:,}")
        
        if not valid_combinations:
            self.log("❌ BRAK KOMBINACJI W LIMICIE PO PRÓBKOWANIU")
            return None
        
        return self._evaluate_combinations(valid_combinations, need_keys, grouped_needs, shop_configs)
    
    def _calculate_minimum_shops_required(self, expanded_offers, need_keys):
        """Oblicza minimalną liczbę sklepów potrzebną do realizacji koszyka"""
        
        # Dla każdej potrzeby znajdź dostępne sklepy
        shops_per_need = []
        for need_key in need_keys:
            offers = expanded_offers[need_key]
            available_shops = set(offer['shop_id'] for offer in offers)
            shops_per_need.append(available_shops)
        
        # Algorytm zachłanny: znajdź minimalny zestaw sklepów
        min_shops = self._greedy_set_cover(shops_per_need)
        
        self.log(f"📊 Analiza pokrycia sklepów:")
        for i, shops in enumerate(shops_per_need):
            self.log(f"   Potrzeba {i}: {len(shops)} sklepów {list(shops)[:3]}...")
        
        return len(min_shops)
    
    def _greedy_set_cover(self, shops_per_need):
        """Algorytm zachłanny dla problemu pokrycia zbiorów"""
        
        all_needs = set(range(len(shops_per_need)))
        covered_needs = set()
        selected_shops = set()
        
        while covered_needs != all_needs:
            best_shop = None
            best_coverage = 0
            
            # Znajdź sklep który pokrywa najwięcej niepokrytych potrzeb
            all_shops = set()
            for shops in shops_per_need:
                all_shops.update(shops)
            
            for shop in all_shops:
                if shop in selected_shops:
                    continue
                
                # Ile nowych potrzeb pokryje ten sklep?
                new_coverage = 0
                for need_idx, shops in enumerate(shops_per_need):
                    if need_idx not in covered_needs and shop in shops:
                        new_coverage += 1
                
                if new_coverage > best_coverage:
                    best_coverage = new_coverage
                    best_shop = shop
            
            if best_shop:
                selected_shops.add(best_shop)
                # Oznacz pokryte potrzeby
                for need_idx, shops in enumerate(shops_per_need):
                    if best_shop in shops:
                        covered_needs.add(need_idx)
            else:
                # Nie można pokryć - błąd w danych
                break
        
        return selected_shops
    
    def _calculate_shop_popularity(self, expanded_offers, need_keys):
        """Oblicza popularność sklepów (ile potrzeb może zaspokoić)"""
        
        shop_popularity = {}
        
        for need_key in need_keys:
            offers = expanded_offers[need_key]
            for offer in offers:
                shop_id = offer['shop_id']
                shop_popularity[shop_id] = shop_popularity.get(shop_id, 0) + 1
        
        return shop_popularity
    
    def _generate_combinations_for_shops(self, expanded_offers, need_keys, shop_combination):
        """Generuje kombinacje używające tylko określonych sklepów"""
        
        combinations = []
        offer_lists = []
        
        for need_key in need_keys:
            offers = expanded_offers[need_key]
            # Filtruj oferty tylko z wybranych sklepów
            filtered_offers = [offer for offer in offers if offer['shop_id'] in shop_combination]
            
            if not filtered_offers:
                # Ta potrzeba nie może być zaspokojona przez te sklepy
                return []
            
            offer_lists.append(filtered_offers[:5])  # Ogranicz do 5 najlepszych na potrzebę
        
        # Generuj kombinacje
        for combo in itertools_product(*offer_lists):
            combinations.append(combo)
            if len(combinations) >= 1000:  # Ogranicz ilość
                break
        
        return combinations
    
    def _advanced_shop_limited_optimization(self, expanded_offers, need_keys, grouped_needs, shop_configs):
        """Zaawansowane algorytmy gdy podstawowe nie działają"""
        
        self.log("🔥 ALGORYTMY ZAAWANSOWANE - ostatnia szansa")
        self.stats['optimization_strategies_used'].append('advanced_algorithms')
        
        # ALGORYTM 1: Genetyczny z limitem sklepów
        genetic_result = self._genetic_algorithm_with_shop_limit(
            expanded_offers, need_keys, grouped_needs, shop_configs
        )
        
        if genetic_result:
            self.log("✅ Algorytm genetyczny znalazł rozwiązanie")
            return genetic_result
        
        # ALGORYTM 2: Lokalne przeszukiwanie
        local_search_result = self._local_search_with_shop_limit(
            expanded_offers, need_keys, grouped_needs, shop_configs
        )
        
        if local_search_result:
            self.log("✅ Przeszukiwanie lokalne znalazło rozwiązanie")
            return local_search_result
        
        self.log("❌ Wszystkie zaawansowane algorytmy zawiodły")
        return None
    
    def _genetic_algorithm_with_shop_limit(self, expanded_offers, need_keys, grouped_needs, shop_configs):
        """Uproszczony algorytm genetyczny z limitem sklepów"""
        
        self.log("🧬 ALGORYTM GENETYCZNY z limitem sklepów")
        
        # Parametry algorytmu
        population_size = 100
        generations = 50
        mutation_rate = 0.1
        
        # Generuj populację początkową
        population = []
        offer_lists = [expanded_offers[need_key] for need_key in need_keys]
        
        attempts = 0
        while len(population) < population_size and attempts < population_size * 10:
            individual = []
            for offers in offer_lists:
                if offers:
                    individual.append(random.choice(offers))
            
            # Sprawdź limit sklepów
            if individual:
                unique_shops = set(offer['shop_id'] for offer in individual)
                if len(unique_shops) <= self.max_shops:
                    population.append(individual)
            
            attempts += 1
        
        if len(population) < 10:  # Zbyt mała populacja
            self.log(f"❌ Zbyt mała populacja: {len(population)}")
            return None
        
        self.log(f"🧬 Populacja początkowa: {len(population)} osobników")
        
        # Ewolucja
        for generation in range(generations):
            # Ocena fitness
            fitness_scores = []
            for individual in population:
                result = self._calculate_combination_result(individual, need_keys, grouped_needs, shop_configs)
                score = 1.0 / (1.0 + result['total_cost'])  # Im niższy koszt, tym wyższy fitness
                fitness_scores.append((individual, score, result))
            
            # Sortuj po fitness
            fitness_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Nowa populacja - najlepsi + potomkowie
            new_population = [ind for ind, _, _ in fitness_scores[:population_size//2]]
            
            # Krzyżowanie i mutacja
            while len(new_population) < population_size:
                parent1 = random.choice(fitness_scores[:population_size//4])[0]
                parent2 = random.choice(fitness_scores[:population_size//4])[0]
                
                child = self._crossover_with_shop_limit(parent1, parent2, need_keys, offer_lists)
                if child and random.random() < mutation_rate:
                    child = self._mutate_with_shop_limit(child, need_keys, offer_lists)
                
                if child:
                    new_population.append(child)
                else:
                    # Jeśli nie udało się stworzyć potomka, weź losowego z populacji
                    new_population.append(random.choice(population))
            
            population = new_population
        
        # Zwróć najlepszego
        best_individual = fitness_scores[0]
        self.log(f"🏆 Najlepszy osobnik: {best_individual[1]:.4f} fitness")
        
        return best_individual[2]  # Zwróć result
    
    def _crossover_with_shop_limit(self, parent1, parent2, need_keys, offer_lists):
        """Krzyżowanie z zachowaniem limitu sklepów"""
        
        child = []
        for i in range(len(parent1)):
            # Losowo wybierz gen od jednego z rodziców
            if random.random() < 0.5:
                child.append(parent1[i])
            else:
                child.append(parent2[i])
        
        # Sprawdź limit sklepów
        unique_shops = set(offer['shop_id'] for offer in child)
        if len(unique_shops) <= self.max_shops:
            return child
        
        # Jeśli przekracza limit, spróbuj naprawić
        return self._repair_shop_limit_violation(child, need_keys, offer_lists)
    
    def _mutate_with_shop_limit(self, individual, need_keys, offer_lists):
        """Mutacja z zachowaniem limitu sklepów"""
        
        mutant = individual.copy()
        
        # Zmutuj losowy gen
        mutation_point = random.randint(0, len(mutant) - 1)
        available_offers = offer_lists[mutation_point]
        
        if available_offers:
            mutant[mutation_point] = random.choice(available_offers)
        
        # Sprawdź limit sklepów
        unique_shops = set(offer['shop_id'] for offer in mutant)
        if len(unique_shops) <= self.max_shops:
            return mutant
        
        # Jeśli przekracza limit, spróbuj naprawić
        return self._repair_shop_limit_violation(mutant, need_keys, offer_lists)
    
    def _repair_shop_limit_violation(self, individual, need_keys, offer_lists):
        """Naprawia osobnika który przekracza limit sklepów"""
        
        # Znajdź sklepy i ich częstość
        shop_usage = {}
        for offer in individual:
            shop_id = offer['shop_id']
            shop_usage[shop_id] = shop_usage.get(shop_id, 0) + 1
        
        # Jeśli limit nie jest przekroczony, zwróć bez zmian
        if len(shop_usage) <= self.max_shops:
            return individual
        
        # Wybierz sklepy do zachowania (najczęściej używane)
        shops_to_keep = sorted(shop_usage.keys(), key=lambda x: shop_usage[x], reverse=True)[:self.max_shops]
        
        # Napraw osobnika
        repaired = []
        for i, offer in enumerate(individual):
            if offer['shop_id'] in shops_to_keep:
                repaired.append(offer)
            else:
                # Znajdź zamiennik z dozwolonych sklepów
                alternative_offers = [o for o in offer_lists[i] if o['shop_id'] in shops_to_keep]
                if alternative_offers:
                    repaired.append(alternative_offers[0])  # Najlepszy z dozwolonych
                else:
                    # Nie da się naprawić
                    return None
        
        return repaired
    
    def _local_search_with_shop_limit(self, expanded_offers, need_keys, grouped_needs, shop_configs):
        """Przeszukiwanie lokalne z limitem sklepów"""
        
        self.log("🔍 PRZESZUKIWANIE LOKALNE z limitem sklepów")
        
        # Znajdź rozwiązanie początkowe
        current_solution = self._find_initial_solution_within_limit(expanded_offers, need_keys)
        
        if not current_solution:
            self.log("❌ Nie znaleziono rozwiązania początkowego")
            return None
        
        current_result = self._calculate_combination_result(current_solution, need_keys, grouped_needs, shop_configs)
        current_score = self._calculate_priority_score(current_result)
        
        self.log(f"🎯 Rozwiązanie początkowe: {current_score:.2f}")
        
        # Przeszukiwanie lokalne
        max_iterations = 1000
        no_improvement_count = 0
        
        for iteration in range(max_iterations):
            # Generuj sąsiadów
            neighbors = self._generate_neighbors_within_shop_limit(
                current_solution, expanded_offers, need_keys
            )
            
            # Znajdź najlepszego sąsiada
            best_neighbor = None
            best_neighbor_score = float('inf')
            
            for neighbor in neighbors:
                neighbor_result = self._calculate_combination_result(neighbor, need_keys, grouped_needs, shop_configs)
                neighbor_score = self._calculate_priority_score(neighbor_result)
                
                if neighbor_score < best_neighbor_score:
                    best_neighbor = neighbor
                    best_neighbor_score = neighbor_score
                    best_neighbor_result = neighbor_result
            
            # Sprawdź czy jest poprawa
            if best_neighbor and best_neighbor_score < current_score:
                current_solution = best_neighbor
                current_result = best_neighbor_result
                current_score = best_neighbor_score
                no_improvement_count = 0
                self.log(f"🔥 Iteracja {iteration}: poprawa do {current_score:.2f}")
            else:
                no_improvement_count += 1
                
                # Zatrzymaj jeśli brak poprawy
                if no_improvement_count > 50:
                    break
        
        self.log(f"🏁 Przeszukiwanie zakończone po {iteration+1} iteracjach")
        return current_result
    
    def _find_initial_solution_within_limit(self, expanded_offers, need_keys):
        """Znajdź początkowe rozwiązanie w limicie sklepów"""
        
        # STRATEGIA 1: Spróbuj najlepsze oferty
        offer_lists = [expanded_offers[need_key] for need_key in need_keys]
        best_solution = [offers[0] for offers in offer_lists if offers]
        
        if best_solution:
            unique_shops = set(offer['shop_id'] for offer in best_solution)
            if len(unique_shops) <= self.max_shops:
                return best_solution
        
        # STRATEGIA 2: Algorytm zachłanny - buduj rozwiązanie sklep po sklepie
        solution = [None] * len(need_keys)
        used_shops = set()
        
        # Sortuj potrzeby po liczbie dostępnych ofert (rosnąco)
        needs_by_availability = sorted(enumerate(need_keys), 
                                     key=lambda x: len(expanded_offers[x[1]]))
        
        for need_idx, need_key in needs_by_availability:
            offers = expanded_offers[need_key]
            best_offer = None
            
            # Najpierw spróbuj oferty z już używanych sklepów
            for offer in offers:
                if offer['shop_id'] in used_shops:
                    best_offer = offer
                    break
            
            # Jeśli nie ma w używanych sklepach, weź najlepszą z nowych
            if not best_offer:
                for offer in offers:
                    if len(used_shops) < self.max_shops:
                        best_offer = offer
                        used_shops.add(offer['shop_id'])
                        break
            
            if best_offer:
                solution[need_idx] = best_offer
            else:
                # Nie da się zbudować rozwiązania
                return None
        
        # Sprawdź czy rozwiązanie jest kompletne
        if all(solution):
            return solution
        
        return None
    
    def _generate_neighbors_within_shop_limit(self, solution, expanded_offers, need_keys):
        """Generuje sąsiadów w limicie sklepów"""
        
        neighbors = []
        current_shops = set(offer['shop_id'] for offer in solution)
        
        # Dla każdej pozycji w rozwiązaniu
        for i, current_offer in enumerate(solution):
            need_key = need_keys[i]
            available_offers = expanded_offers[need_key]
            
            for alternative_offer in available_offers:
                if alternative_offer == current_offer:
                    continue  # Pomiń obecną ofertę
                
                # Sprawdź czy zamiana nie przekroczy limitu sklepów
                new_solution = solution.copy()
                new_solution[i] = alternative_offer
                
                new_shops = set(offer['shop_id'] for offer in new_solution)
                
                if len(new_shops) <= self.max_shops:
                    neighbors.append(new_solution)
        
        return neighbors[:50]  # Ogranicz liczbę sąsiadów
    
    def _group_substitute_products_with_combining(self, basket):
        """Grupuje produkty zamienne I ŁĄCZY ILOŚCI jeśli w tym samym koszyku"""
        
        try:
            from substitute_manager import substitute_manager
        except ImportError:
            self.log("⚠️ substitute_manager nie dostępny - wszystkie produkty jako indywidualne")
            # Fallback - wszystkie jako produkty indywidualne
            basket_items = basket.get('basket_items', {})
            individual_products = []
            
            for product_key, item in basket_items.items():
                individual_products.append({
                    'type': 'individual',
                    'product_id': item['product_id'],
                    'quantity': item['requested_quantity'],
                    'product_name': item.get('product_name', f'Produkt {item["product_id"]}'),
                    'substitute_settings': item.get('substitute_settings', {}),
                    'has_substitutes': False,
                    'group_id': None
                })
            
            return individual_products
        
        groups = substitute_manager.load_substitute_groups()
        basket_items = basket.get('basket_items', {})
        
        # Mapowanie: product_id -> group_id
        product_to_group = {}
        for group_id, group_data in groups.items():
            for product_id in group_data['product_ids']:
                product_to_group[product_id] = group_id
        
        grouped_needs = []
        used_groups = set()
        individual_products = []
        
        self.log(f"   📋 Analiza {len(basket_items)} produktów w koszyku:")
        
        for product_key, item in basket_items.items():
            product_id = item['product_id']
            quantity = item['requested_quantity']
            
            group_id = product_to_group.get(product_id)
            
            if group_id and group_id not in used_groups and self.allow_substitutes:
                # NOWA LOGIKA: ŁĄCZ WSZYSTKIE PRODUKTY Z TEJ GRUPY W KOSZYKU
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
                
                if len(group_products) > 1:
                    # ŁĄCZENIE ILOŚCI!
                    self.log(f"   🔗 GRUPA {group_id}: ŁĄCZĘ {len(group_products)} produktów")
                    product_names = [p['product_name'] for p in group_products]
                    quantities = [f"{p['product_id']}({p['quantity']}szt)" for p in group_products]
                    
                    self.log(f"      📦 Produkty: {', '.join(product_names)}")
                    self.log(f"      🔢 Ilości: {', '.join(quantities)} = {total_quantity} szt ŁĄCZNIE")
                    
                    # Wybierz najrestrykcyjniejsze ustawienia
                    group_settings = self._merge_substitute_settings([p['substitute_settings'] for p in group_products])
                    
                    grouped_needs.append({
                        'type': 'substitute_group',
                        'group_id': group_id,
                        'products_in_basket': group_products,
                        'total_quantity': total_quantity,  # POŁĄCZONA ILOŚĆ
                        'substitute_settings': group_settings,
                        'group_name': f"Grupa zamienników {group_id}"
                    })
                    
                    used_groups.add(group_id)
                    self.log(f"      ✅ POŁĄCZONO w grupę o łącznej ilości {total_quantity}")
                    
                else:
                    # Pojedynczy produkt z grupy
                    individual_products.append({
                        'type': 'individual',
                        'product_id': product_id,
                        'quantity': quantity,
                        'product_name': item.get('product_name', f'Produkt {product_id}'),
                        'substitute_settings': item.get('substitute_settings', {}),
                        'has_substitutes': True,
                        'group_id': group_id
                    })
                    self.log(f"   📦 Produkt {product_id}: pojedynczy ze skupiny {group_id} ({quantity} szt)")
                    
            elif not group_id or not self.allow_substitutes:
                # Produkt bez grupy lub wyłączone zamienniki
                individual_products.append({
                    'type': 'individual',
                    'product_id': product_id,
                    'quantity': quantity,
                    'product_name': item.get('product_name', f'Produkt {product_id}'),
                    'substitute_settings': item.get('substitute_settings', {}),
                    'has_substitutes': False,
                    'group_id': None
                })
                reason = "bez zamienników" if not group_id else "zamienniki wyłączone"
                self.log(f"   📦 Produkt {product_id}: pojedynczy {reason} ({quantity} szt)")
        
        all_needs = grouped_needs + individual_products
        
        self.log(f"   🎯 PODSUMOWANIE GRUPOWANIA:")
        self.log(f"      🔗 Grup zamienników (połączonych): {len(grouped_needs)}")
        self.log(f"      📦 Produktów indywidualnych: {len(individual_products)}")
        self.log(f"      🎯 Łączna liczba potrzeb: {len(all_needs)}")
        
        return all_needs
    
    def _expand_offers_with_substitutes(self, grouped_needs, normalized_prices):
        """Rozszerza oferty o zamienniki z pełną implementacją ustawień"""
        
        self.log(f"🔍 ROZSZERZANIE OFERT:")
        self.log(f"   📊 Liczba grouped_needs: {len(grouped_needs)}")
        self.log(f"   📊 Liczba normalized_prices: {len(normalized_prices)}")
        self.log(f"   🔧 allow_substitutes: {self.allow_substitutes}")
        
        if not self.allow_substitutes:
            self.log("   ❌ Zamienniki WYŁĄCZONE globalnie")
            return self._get_original_offers_only(grouped_needs, normalized_prices), []

        expanded_offers = {}
        products_without_offers = []
        
        for need_index, need in enumerate(grouped_needs):
            need_key = f"need_{need_index}"
            expanded_offers[need_key] = []
            
            self.log(f"\n   🔍 NEED #{need_index} ({need_key}):")
            self.log(f"      📦 Typ: {need['type']}")
            
            if need['type'] == 'substitute_group':
                # Obsługa grupy zamienników
                self.log(f"   🔗 GRUPA {need['group_id']}: {need['total_quantity']} szt łącznie")
                
                group_settings = need['substitute_settings']
                group_allow_substitutes = group_settings.get('allow_substitutes', True) and self.allow_substitutes
                
                if not group_allow_substitutes:
                    self.log(f"      ❌ Zamienniki wyłączone dla tej grupy")
                    original_offers = self._get_group_original_offers(need, normalized_prices)
                    expanded_offers[need_key] = original_offers
                    if not original_offers:
                        products_without_offers.append(need)
                    continue
                
                # Pobierz oferty dla grupy z zamiennikmi
                group_offers = self._get_group_offers_with_substitutes(need, normalized_prices)
                expanded_offers[need_key] = group_offers
                
                if not group_offers:
                    products_without_offers.append(need)
                    
            else:
                # Produkt indywidualny
                product_id = need['product_id']
                quantity = need['quantity']
                item_settings = need['substitute_settings']
                
                item_allow_substitutes = (item_settings.get('allow_substitutes', True) 
                                        and self.allow_substitutes 
                                        and need['has_substitutes'])
                
                self.log(f"   📦 PRODUKT {product_id}: {quantity} szt")
                
                if not item_allow_substitutes:
                    reason = "wyłączone" if not item_settings.get('allow_substitutes', True) else "brak grupy"
                    self.log(f"      ❌ Zamienniki {reason} dla tego produktu")
                    
                    original_offers = self._get_individual_original_offers(need, normalized_prices)
                    expanded_offers[need_key] = original_offers
                    
                    if not original_offers:
                        products_without_offers.append(need)
                    continue
                
                # Pobierz oferty z zamiennikmi
                individual_offers = self._get_individual_offers_with_substitutes(need, normalized_prices)
                expanded_offers[need_key] = individual_offers
                
                if not individual_offers:
                    products_without_offers.append(need)
        
        # Podsumowanie
        total_offers = sum(len(offers) for offers in expanded_offers.values())
        needs_with_offers = len([k for k, v in expanded_offers.items() if v])
        
        self.log(f"\n🎯 PODSUMOWANIE ROZSZERZANIA OFERT:")
        self.log(f"   📊 expanded_offers kluczy: {len(expanded_offers)}")
        self.log(f"   📊 products_without_offers: {len(products_without_offers)}")
        self.log(f"   ✅ Potrzeby z ofertami: {needs_with_offers}")
        self.log(f"   🎯 Łączna liczba ofert: {total_offers}")
        
        return expanded_offers, products_without_offers
    
    def _get_individual_offers_with_substitutes(self, need, normalized_prices):
        """Pobiera oferty dla produktu indywidualnego z zamiennikmi"""
        
        offers = []
        product_id = need['product_id']
        item_settings = need['substitute_settings']
        max_price_increase = item_settings.get('max_price_increase_percent', self.max_price_increase_percent)
        
        # Najpierw dodaj oryginalne oferty
        original_offers = self._get_individual_original_offers(need, normalized_prices)
        offers.extend(original_offers)
        
        # Znajdź najlepszą cenę oryginału dla porównania
        original_best_price = None
        if original_offers:
            original_best_price = min(offer['price_pln'] for offer in original_offers)
        
        # Dodaj zamienniki jeśli są dostępne
        try:
            from substitute_manager import substitute_manager
            substitute_info = substitute_manager.get_substitutes_for_product(product_id)
            
            if substitute_info['substitutes']:
                for substitute in substitute_info['substitutes'][:self.max_substitutes_per_product]:
                    sub_offers = self._get_substitute_offers(
                        substitute['id'], normalized_prices, product_id, 
                        original_best_price, max_price_increase, need['quantity']
                    )
                    offers.extend(sub_offers)
                    
        except ImportError:
            pass  # Brak substitute_manager
        
        # Sortuj według ceny
        offers.sort(key=lambda x: x['price_pln'])
        
        return offers
    
    def _get_group_offers_with_substitutes(self, need, normalized_prices):
        """Pobiera oferty dla grupy z zamiennikmi"""
        
        offers = []
        
        # Dodaj oryginalne oferty z koszyka
        original_offers = self._get_group_original_offers(need, normalized_prices)
        offers.extend(original_offers)
        
        # Znajdź najlepszą cenę w grupie
        group_best_price = None
        if original_offers:
            group_best_price = min(offer['price_pln'] for offer in original_offers)
        
        # Dodaj zamienniki spoza koszyka
        try:
            from substitute_manager import substitute_manager
            
            # Dla pierwszego produktu z grupy znajdź zamienniki
            first_product = need['products_in_basket'][0]
            substitute_info = substitute_manager.get_substitutes_for_product(first_product['product_id'])
            
            group_settings = need['substitute_settings']
            max_price_increase = group_settings.get('max_price_increase_percent', self.max_price_increase_percent)
            
            if substitute_info['substitutes']:
                for substitute in substitute_info['substitutes'][:self.max_substitutes_per_product]:
                    # Sprawdź czy zamiennik nie jest już w koszyku
                    if not any(p['product_id'] == substitute['id'] for p in need['products_in_basket']):
                        sub_offers = self._get_substitute_offers(
                            substitute['id'], normalized_prices, first_product['product_id'],
                            group_best_price, max_price_increase, need['total_quantity']
                        )
                        offers.extend(sub_offers)
                        
        except ImportError:
            pass
        
        # Sortuj według ceny
        offers.sort(key=lambda x: x['price_pln'])
        
        return offers
    
    def _get_substitute_offers(self, substitute_id, normalized_prices, original_id, 
                             original_best_price, max_price_increase, quantity):
        """Pobiera oferty dla konkretnego zamiennika"""
        
        offers = []
        
        for key, price_data in normalized_prices.items():
            if price_data['product_id'] == substitute_id and price_data.get('price_pln'):
                substitute_price = price_data['price_pln']
                
                # Sprawdź limit wzrostu ceny
                if original_best_price:
                    price_increase = ((substitute_price - original_best_price) / original_best_price) * 100
                    if price_increase > max_price_increase:
                        continue  # Za drogi zamiennik
                
                # Określ powód zastąpienia
                if original_best_price:
                    if substitute_price < original_best_price:
                        reason = f"Tańszy o {abs(((substitute_price - original_best_price) / original_best_price) * 100):.1f}%"
                    elif substitute_price > original_best_price:
                        reason = f"Droższy o {((substitute_price - original_best_price) / original_best_price) * 100:.1f}%"
                    else:
                        reason = "Podobna cena"
                else:
                    reason = "Oryginał niedostępny"
                
                offer = {
                    'product_id': substitute_id,
                    'shop_id': price_data['shop_id'],
                    'price_pln': substitute_price,
                    'price_original': price_data['price_original'],
                    'currency': price_data['currency'],
                    'is_substitute': True,
                    'original_product_id': original_id,
                    'substitute_product_id': substitute_id,
                    'substitute_reason': reason,
                    'quantity': quantity
                }
                offers.append(offer)
        
        return offers
    
    def _get_individual_original_offers(self, need, normalized_prices):
        """Pobiera oryginalne oferty dla pojedynczego produktu"""
        offers = []
        product_id = need['product_id']
        
        for key, price_data in normalized_prices.items():
            if price_data['product_id'] == product_id and price_data.get('price_pln'):
                offer = {
                    'product_id': product_id,
                    'shop_id': price_data['shop_id'],
                    'price_pln': price_data['price_pln'],
                    'price_original': price_data['price_original'],
                    'currency': price_data['currency'],
                    'is_substitute': False,
                    'original_product_id': product_id,
                    'substitute_reason': '',
                    'individual_quantity': need['quantity']
                }
                offers.append(offer)
        
        # Sortuj według ceny
        offers.sort(key=lambda x: x['price_pln'])
        return offers
    
    def _get_group_original_offers(self, need, normalized_prices):
        """Pobiera oryginalne oferty dla grupy"""
        offers = []
        
        for product_info in need['products_in_basket']:
            product_id = product_info['product_id']
            
            for key, price_data in normalized_prices.items():
                if price_data['product_id'] == product_id and price_data.get('price_pln'):
                    offer = {
                        'product_id': product_id,
                        'shop_id': price_data['shop_id'],
                        'price_pln': price_data['price_pln'],
                        'price_original': price_data['price_original'],
                        'currency': price_data['currency'],
                        'is_substitute': False,
                        'original_group': need['group_id'],
                        'substitute_reason': '',
                        'group_quantity': need['total_quantity'],
                        'from_basket': True,
                        'basket_product_id': product_id
                    }
                    offers.append(offer)
        
        # Sortuj według ceny
        offers.sort(key=lambda x: x['price_pln'])
        return offers
    
    def _get_original_offers_only(self, grouped_needs, normalized_prices):
        """Pobiera tylko oryginalne oferty (gdy zamienniki wyłączone)"""
        expanded_offers = {}
        
        for need_index, need in enumerate(grouped_needs):
            need_key = f"need_{need_index}"
            
            if need['type'] == 'substitute_group':
                expanded_offers[need_key] = self._get_group_original_offers(need, normalized_prices)
            else:
                expanded_offers[need_key] = self._get_individual_original_offers(need, normalized_prices)
        
        return expanded_offers
    
    def _evaluate_combinations(self, combinations, need_keys, grouped_needs, shop_configs):
        """Ocena kombinacji z pełną implementacją priorytetów"""
        
        if not combinations:
            return None
        
        best_score = float('inf')
        best_combination = None
        
        self.log(f"⚖️ OCENA {len(combinations)} KOMBINACJI")
        self.log(f"🎯 PRIORYTET: {self.priority}")
        
        # Grupuj według liczby sklepów dla lepszego logowania
        by_shops = {}
        for combo in combinations:
            shop_count = len(set(offer['shop_id'] for offer in combo))
            if shop_count not in by_shops:
                by_shops[shop_count] = []
            by_shops[shop_count].append(combo)
        
        evaluated = 0
        for shop_count in sorted(by_shops.keys()):
            combos = by_shops[shop_count]
            self.log(f"   🏪 Oceniam {len(combos)} kombinacji z {shop_count} sklepami")
            
            for combo in combos:
                # Przelicz kombinację
                result = self._calculate_combination_result(combo, need_keys, grouped_needs, shop_configs)
                
                # Oblicz wynik według priorytetu
                score = self._calculate_priority_score(result)
                evaluated += 1
                
                if score < best_score:
                    best_score = score
                    best_combination = result
                    self.log(f"      ⭐ Nowa najlepsza (#{evaluated}): {score:.2f}, {result['shops_count']} sklepów, {result['total_cost']:.2f} PLN")
        
        self.log(f"✅ NAJLEPSZA KOMBINACJA: wynik {best_score:.2f} w {best_combination['shops_count'] if best_combination else 0} sklepach")
        return best_combination
    
    def _calculate_priority_score(self, result):
        """Oblicza wynik według wybranego priorytetu"""
        
        if self.priority == 'fewest_shops':
            score = result['shops_count'] * 1000 + result['total_cost']
        elif self.priority == 'balanced':
            penalty = (result['shops_count'] - 1) * 15
            score = result['total_cost'] + penalty
        else:  # 'lowest_total_cost'
            score = result['total_cost']
        
        return score
    
    def _calculate_combination_result(self, combination, need_keys, grouped_needs, shop_configs):
        """Przelicza kombinację na format wynikowy"""
        
        shops_summary = {}
        items_list = []
        
        for i, offer in enumerate(combination):
            shop_id = offer['shop_id']
            need_index = int(need_keys[i].split('_')[1])
            need = grouped_needs[need_index]
            
            if need['type'] == 'substitute_group':
                # Obsługa grupy zamienników
                total_quantity = need['total_quantity']
                unit_price = offer['price_pln']
                
                # Określ nazwę produktu
                if offer.get('from_basket'):
                    basket_product = next(
                        (p for p in need['products_in_basket'] if p['product_id'] == offer.get('basket_product_id')),
                        need['products_in_basket'][0]
                    )
                    product_name = f"{basket_product['product_name']} (grupa {len(need['products_in_basket'])} produktów)"
                    actual_product_id = offer.get('basket_product_id', basket_product['product_id'])
                else:
                    # Zamiennik spoza koszyka
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
                
                item_data = {
                    'product_id': need['products_in_basket'][0]['product_id'],  # Pierwszy z koszyka
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
                
            else:
                # Obsługa produktu indywidualnego
                product_id = need['product_id']
                quantity = need['quantity']
                unit_price = offer['price_pln']
                
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
                    'product_id': product_id,
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
            free_from = float(config.get('delivery_free_from')) if config.get('delivery_free_from') else None
            shipping_cost = float(config.get('delivery_cost', 0)) if config.get('delivery_cost') else 0

            if free_from and summary['subtotal'] >= free_from:
                summary['shipping_cost'] = 0
            else:
                summary['shipping_cost'] = shipping_cost or 0
            
            total_shipping_cost += summary['shipping_cost']
        
        total_cost = total_products_cost + total_shipping_cost
        
        return {
            'items_list': items_list,
            'shops_summary': shops_summary,
            'total_products_cost': total_products_cost,
            'total_shipping_cost': total_shipping_cost,
            'total_cost': total_cost,
            'shops_count': len(shops_summary)
        }
    
    def _optimize_quantities(self, result, shop_configs):
        """Optymalizuje ilości dla darmowej dostawy - ZABEZPIECZONA WERSJA"""
        
        if not self.suggest_quantities or not self.consider_free_shipping:
            self.log("⭐️ Optymalizacja ilości POMINIĘTA (wyłączona w ustawieniach)")
            return result
        
        self.log(f"🔢 OPTYMALIZACJA ILOŚCI:")
        self.log(f"   💰 Próg oszczędności: {self.min_savings_threshold} PLN")
        self.log(f"   📊 Max mnożnik: {self.max_quantity_multiplier}")
        
        total_savings = 0
        optimizations_count = 0
        
        for shop_id, shop_summary in result['shops_summary'].items():
            config = shop_configs.get(shop_id, {})
            
            # BEZPIECZNE POBIERANIE WARTOŚCI
            try:
                delivery_free_from = config.get('delivery_free_from')
                delivery_cost = config.get('delivery_cost')
                
                self.log(f"   🏪 Sklep {shop_id}: {shop_summary['subtotal']:.2f} PLN")
                
                # BEZPIECZNA KONWERSJA
                free_from = None
                shipping_cost = None
                
                if delivery_free_from is not None:
                    try:
                        free_from = float(delivery_free_from)
                    except (ValueError, TypeError):
                        free_from = None
                
                if delivery_cost is not None:
                    try:
                        shipping_cost = float(delivery_cost)
                    except (ValueError, TypeError):
                        shipping_cost = None
                
                # SPRAWDZENIE WARUNKÓW
                if free_from is None or shipping_cost is None:
                    self.log(f"      ⭐ Brak warunków darmowej dostawy")
                    continue
                
                if shipping_cost <= 0:
                    self.log(f"      ⭐ Dostawa już darmowa")
                    continue
                    
                # BEZPIECZNE PORÓWNANIE
                current_subtotal = float(shop_summary['subtotal'])
                if current_subtotal >= free_from:
                    self.log(f"      ⭐ Już ma darmową dostawę ({current_subtotal:.2f} ≥ {free_from})")
                    continue
                
                # OBLICZENIA OPTYMALIZACJI
                missing_amount = free_from - current_subtotal
                potential_savings = shipping_cost - missing_amount
                
                self.log(f"      🎯 Brakuje: {missing_amount:.2f} PLN do darmowej dostawy")
                self.log(f"      💡 Potencjalne oszczędności: {potential_savings:.2f} PLN")
                
                effective_threshold = min(self.min_savings_threshold, missing_amount * 2)
                
                if potential_savings >= effective_threshold:
                    best_optimization = self._find_best_quantity_increase(shop_summary['items'], missing_amount)
                    
                    if best_optimization:
                        item = best_optimization['item']
                        old_quantity = item['quantity']
                        new_quantity = best_optimization['new_quantity']
                        additional_cost = best_optimization['additional_cost']
                        real_savings = shipping_cost - additional_cost
                        
                        if real_savings > 0:
                            # Aplikuj optymalizację
                            item['quantity'] = new_quantity
                            item['total_price_pln'] = item['unit_price_pln'] * new_quantity
                            item['quantity_optimized'] = True
                            item['optimization_reason'] = f"Zwiększono z {old_quantity} do {new_quantity} dla darmowej dostawy (oszczędność: {real_savings:.2f} PLN)"
                            
                            # Przelicz koszty
                            shop_summary['subtotal'] += additional_cost
                            shop_summary['shipping_cost'] = 0
                            
                            result['total_products_cost'] += additional_cost
                            result['total_shipping_cost'] -= shipping_cost
                            result['total_cost'] = result['total_products_cost'] + result['total_shipping_cost']
                            
                            total_savings += real_savings
                            optimizations_count += 1
                            
                            self.log(f"      ✅ OPTYMALIZACJA: {item.get('product_name', item['product_id'])}")
                            self.log(f"         📦 {old_quantity} → {new_quantity} sztuk (+{additional_cost:.2f} PLN)")
                            self.log(f"         💎 Oszczędności: {real_savings:.2f} PLN")
                        else:
                            self.log(f"      ❌ Brak realnych oszczędności ({real_savings:.2f} PLN)")
                    else:
                        self.log(f"      ❌ Nie znaleziono odpowiedniego produktu do zwiększenia")
                else:
                    self.log(f"      ❌ Za małe oszczędności ({potential_savings:.2f} < {effective_threshold:.2f} PLN)")
                    
            except Exception as e:
                self.log(f"      💥 BŁĄD w optymalizacji dla sklepu {shop_id}: {str(e)}")
                continue
        
        if total_savings > 0:
            self.log(f"🏆 ŁĄCZNE OSZCZĘDNOŚCI: {total_savings:.2f} PLN")
            self.log(f"📊 Zoptymalizowano {optimizations_count} produktów")
        else:
            self.log(f"📋 Brak możliwości optymalizacji ilości")
        
        return result
    
    def _find_best_quantity_increase(self, shop_items, needed_amount):
        """Znajduje najlepszy produkt do zwiększenia ilości"""
        best_option = None
        
        for item in shop_items:
            if item.get('is_group'):
                continue  # Pomiń grupy zamienników
            
            unit_price = item['unit_price_pln']
            current_qty = item['quantity']
            
            for additional_qty in [1, 2, 3, 5, 10]:
                new_quantity = current_qty + additional_qty
                additional_cost = additional_qty * unit_price
                
                # Sprawdź limit mnożnika
                if new_quantity > current_qty * self.max_quantity_multiplier:
                    continue
                
                if additional_cost >= needed_amount:
                    efficiency = needed_amount / additional_cost
                    
                    if not best_option or efficiency > best_option['efficiency']:
                        best_option = {
                            'item': item,
                            'new_quantity': new_quantity,
                            'additional_cost': additional_cost,
                            'efficiency': efficiency,
                            'additional_qty': additional_qty
                        }
        
        return best_option
    
    def _normalize_prices(self, prices_data):
        """Normalizuje ceny do PLN"""
        fx_rates = {'PLN': 1.0, 'EUR': 4.30, 'USD': 4.00}
        normalized_prices = {}
        
        for key, price_info in prices_data.items():
            if price_info.get('price'):
                currency = price_info.get('currency', 'PLN')
                rate = fx_rates.get(currency, 1.0)
                
                try:
                    price_value = price_info['price']
                    
                    if isinstance(price_value, str):
                        price_clean = price_value.strip().replace(',', '.')
                        import re
                        numbers = re.findall(r'\d+\.?\d*', price_clean)
                        if numbers:
                            price_value = float(numbers[-1])
                        else:
                            continue
                    elif not isinstance(price_value, (int, float)):
                        continue
                    else:
                        price_value = float(price_value)
                    
                    if price_value <= 0:
                        continue
                    
                    normalized_prices[key] = {
                        'product_id': price_info['product_id'],
                        'shop_id': price_info['shop_id'],
                        'price_pln': price_value * rate,
                        'price_original': price_value,
                        'currency': currency
                    }
                    
                except (ValueError, TypeError):
                    continue
        
        self.log(f"💰 Znormalizowano {len(normalized_prices)} cen z {len(prices_data)} dostępnych")
        return normalized_prices
    
    def _merge_substitute_settings(self, settings_list):
        """Łączy ustawienia zamienników (wybiera najrestrykcyjniejsze)"""
        if not settings_list:
            return {'allow_substitutes': True, 'max_price_increase_percent': 20.0}
        
        allow_substitutes = all(s.get('allow_substitutes', True) for s in settings_list)
        max_increases = [s.get('max_price_increase_percent', 20.0) for s in settings_list]
        min_max_increase = min(max_increases)
        
        return {
            'allow_substitutes': allow_substitutes,
            'max_price_increase_percent': min_max_increase
        }
    
    def _create_no_offers_result(self, basket_id, grouped_needs, products_without_offers):
        """Tworzy wynik gdy brak ofert"""
        return {
            'success': True,
            'basket_id': basket_id,
            'best_option': {
                'items_list': [],
                'shops_summary': {},
                'total_products_cost': 0,
                'total_shipping_cost': 0,
                'total_cost': 0,
                'shops_count': 0,
                'products_to_complete': self._create_completion_section(products_without_offers)
            },
            'optimized_at': datetime.now().isoformat(),
            'optimizations_applied': 0,
            'substitutes_used': 0,
            'grouped_needs': len(grouped_needs),
            'original_items': len(products_without_offers),
            'products_without_offers': len(products_without_offers)
        }
    
    def _create_completion_section(self, products_without_offers):
        """Tworzy sekcję produktów do uzupełnienia"""
        completion_items = []
        
        for need in products_without_offers:
            if need['type'] == 'substitute_group':
                for product_info in need['products_in_basket']:
                    completion_items.append({
                        'product_id': product_info['product_id'],
                        'product_name': product_info['product_name'],
                        'quantity': product_info['quantity'],
                        'reason': f"Brak ofert dla grupy zamienników {need['group_id']}",
                        'is_group': True,
                        'group_id': need['group_id'],
                        'type': 'no_offers'
                    })
            else:
                completion_items.append({
                    'product_id': need['product_id'],
                    'product_name': need.get('product_name', f'Produkt {need["product_id"]}'),
                    'quantity': need['quantity'],
                    'reason': 'Brak dostępnych ofert',
                    'is_group': False,
                    'group_id': need.get('group_id'),
                    'type': 'no_offers'
                })
        
        return completion_items
    
    def _log_optimization_stats(self):
        """Loguje statystyki optymalizacji"""
        self.log(f"📈 STATYSTYKI OPTYMALIZACJI:")
        self.log(f"   🔍 Oceniono kombinacji: {self.stats['combinations_evaluated']:,}")
        self.log(f"   ✅ W limicie sklepów: {self.stats['combinations_within_limit']:,}")
        self.log(f"   🚫 Odrzucone przez limit: {self.stats['combinations_filtered_by_shops']:,}")
        self.log(f"   🧠 Użyte strategie: {', '.join(self.stats['optimization_strategies_used'])}")
        
        if self.stats['combinations_evaluated'] > 0:
            acceptance_rate = (self.stats['combinations_within_limit'] / self.stats['combinations_evaluated']) * 100
            self.log(f"   📊 Wskaźnik akceptacji: {acceptance_rate:.1f}%")
            
            if acceptance_rate < 10:
                self.log(f"   ⚠️ UWAGA: Niski wskaźnik akceptacji - rozważ zwiększenie limitu sklepów")
    
    # NOWE: Funkcje pomocnicze dla zaawansowanych algorytmów
    
    def _estimate_complexity(self, expanded_offers, need_keys):
        """Szacuje złożoność obliczeniową"""
        total_combinations = 1
        for need_key in need_keys:
            offers_count = len(expanded_offers[need_key])
            total_combinations *= offers_count
            if total_combinations > 10**12:  # Przerwij przy bardzo dużych liczbach
                return float('inf')
        
        return total_combinations
    
    def _adaptive_algorithm_selection(self, expanded_offers, need_keys, grouped_needs, shop_configs):
        """Inteligentny wybór algorytmu na podstawie charakterystyki problemu"""
        
        complexity = self._estimate_complexity(expanded_offers, need_keys)
        num_needs = len(need_keys)
        num_shops = len(set(
            offer['shop_id'] 
            for offers in expanded_offers.values() 
            for offer in offers
        ))
        
        self.log(f"🧠 ANALIZA PROBLEMU:")
        self.log(f"   📊 Złożoność: {complexity if complexity != float('inf') else 'Bardzo wysoka'}")
        self.log(f"   📦 Potrzeb: {num_needs}")
        self.log(f"   🏪 Sklepów: {num_shops}")
        self.log(f"   🎯 Limit sklepów: {self.max_shops}")
        
        # Wybór strategii
        if complexity <= 1000:
            self.log("   ⚡ WYBRANO: Pełne przeszukiwanie")
            return "exhaustive"
        elif complexity <= self.MAX_COMBINATIONS:
            self.log("   🎯 WYBRANO: Inteligentne próbkowanie")
            return "smart_sampling"
        elif num_shops <= self.max_shops * 2:
            self.log("   🧬 WYBRANO: Algorytm genetyczny")
            return "genetic"
        else:
            self.log("   🔍 WYBRANO: Przeszukiwanie lokalne")
            return "local_search"
    
    def _advanced_preprocessing(self, expanded_offers, need_keys):
        """Zaawansowane przetwarzanie wstępne ofert"""
        
        # Usuń zdominowane oferty
        for need_key in need_keys:
            offers = expanded_offers[need_key]
            if len(offers) > 10:  # Tylko dla dużych zbiorów
                filtered_offers = self._remove_dominated_offers(offers)
                expanded_offers[need_key] = filtered_offers
                
                removed_count = len(offers) - len(filtered_offers)
                if removed_count > 0:
                    self.log(f"   🗑️ Usunięto {removed_count} zdominowanych ofert dla {need_key}")
        
        return expanded_offers
    
    def _remove_dominated_offers(self, offers):
        """Usuwa oferty zdominowane (droższe w tym samym sklepie)"""
        
        # Grupuj według sklepu
        by_shop = {}
        for offer in offers:
            shop_id = offer['shop_id']
            if shop_id not in by_shop:
                by_shop[shop_id] = []
            by_shop[shop_id].append(offer)
        
        # Dla każdego sklepu pozostaw tylko najtańszą ofertę
        filtered_offers = []
        for shop_id, shop_offers in by_shop.items():
            best_offer = min(shop_offers, key=lambda x: x['price_pln'])
            filtered_offers.append(best_offer)
        
        return filtered_offers