"""
Moduł optymalizacji ilości dla darmowej dostawy
"""

class QuantityOptimizer:
    """Klasa odpowiedzialna za optymalizację ilości produktów"""
    
    def __init__(self, settings, log_func):
        self.settings = settings
        self.log = log_func
        self.suggest_quantities = settings.get('suggest_quantities', False)
        self.min_savings_threshold = settings.get('min_savings_threshold', 5.0)
        self.max_quantity_multiplier = settings.get('max_quantity_multiplier', 3)
        self.consider_free_shipping = settings.get('consider_free_shipping', True)
    
    def optimize_quantities_in_result(self, result, shop_configs):
        """Optymalizuje ilości w gotowym wyniku kombinacji"""
        
        if not self.suggest_quantities:
            self.log("⚙️ Sugestie ilości WYŁĄCZONE - pomijam optymalizację")
            return result
        
        if not self.consider_free_shipping:
            self.log("🚚 Optymalizacja dostawy WYŁĄCZONA")
            return result
        
        self.log(f"📢 OPTYMALIZACJA ILOŚCI:")
        self.log(f"   💰 Próg oszczędności: {self.min_savings_threshold} PLN")
        self.log(f"   📊 Max mnożnik: {self.max_quantity_multiplier}")
        
        total_savings = 0
        optimizations_count = 0
        
        # Sprawdź każdy sklep
        for shop_id, shop_summary in result['shops_summary'].items():
            config = shop_configs.get(shop_id, {})
            free_from = config.get('delivery_free_from')
            shipping_cost = config.get('delivery_cost', 0)
            
            self.log(f"   🏪 Sklep {shop_id}: {shop_summary['subtotal']:.2f} PLN")
            
            if not free_from or not shipping_cost:
                self.log(f"      ⭐ Brak warunków darmowej dostawy")
                continue
                
            if shop_summary['subtotal'] >= free_from:
                self.log(f"      ✅ Już ma darmową dostawę (≥{free_from} PLN)")
                continue
                
            # Sprawdź czy warto dopłacić do darmowej dostawy
            missing_amount = free_from - shop_summary['subtotal']
            potential_savings = shipping_cost - missing_amount
            
            self.log(f"      🎯 Brakuje: {missing_amount:.2f} PLN do darmowej dostawy")
            self.log(f"      💡 Potencjalne oszczędności: {potential_savings:.2f} PLN")
            
            # POPRAWKA: Obniżamy próg dla bardzo małych kwot
            effective_threshold = min(self.min_savings_threshold, missing_amount * 2)
            self.log(f"      📏 Efektywny próg oszczędności: {effective_threshold:.2f} PLN")
            
            if potential_savings >= effective_threshold:
                # Znajdź najlepszy produkt do zwiększenia ilości
                best_optimization = self._find_best_quantity_increase(
                    shop_summary['items'], missing_amount
                )
                
                if best_optimization:
                    item = best_optimization['item']
                    old_quantity = item['quantity']
                    new_quantity = best_optimization['new_quantity']
                    additional_cost = best_optimization['additional_cost']
                    
                    # POPRAWKA: Sprawdź czy to rzeczywiście oszczędność
                    real_savings = shipping_cost - additional_cost
                    
                    if real_savings > 0:
                        # Aplikuj optymalizację
                        item['quantity'] = new_quantity
                        item['total_price_pln'] = item['unit_price_pln'] * new_quantity
                        item['quantity_optimized'] = True
                        item['optimization_reason'] = f"Zwiększono z {old_quantity} do {new_quantity} dla darmowej dostawy (oszczędność: {real_savings:.2f} PLN)"
                        
                        # Przelicz koszty sklepu
                        shop_summary['subtotal'] += additional_cost
                        shop_summary['shipping_cost'] = 0  # Teraz darmowa dostawa
                        
                        # Przelicz koszty całkowite
                        result['total_products_cost'] += additional_cost
                        result['total_shipping_cost'] -= shipping_cost
                        result['total_cost'] = result['total_products_cost'] + result['total_shipping_cost']
                        
                        total_savings += real_savings
                        optimizations_count += 1
                        
                        self.log(f"      ✅ OPTYMALIZACJA: Produkt {item.get('product_name', item['product_id'])}")
                        self.log(f"         📦 {old_quantity} → {new_quantity} sztuk (+{additional_cost:.2f} PLN)")
                        self.log(f"         💎 Oszczędności: {real_savings:.2f} PLN")
                    else:
                        self.log(f"      ❌ Brak realnych oszczędności ({real_savings:.2f} PLN)")
                else:
                    self.log(f"      ❌ Nie znaleziono odpowiedniego produktu do zwiększenia")
            else:
                self.log(f"      ❌ Za małe oszczędności ({potential_savings:.2f} < {effective_threshold:.2f} PLN)")
        
        if total_savings > 0:
            self.log(f"🏆 ŁĄCZNE OSZCZĘDNOŚCI Z OPTYMALIZACJI ILOŚCI: {total_savings:.2f} PLN")
            self.log(f"📊 Zoptymalizowano {optimizations_count} produktów")
        else:
            self.log(f"📋 Brak możliwości optymalizacji ilości w tym koszyku")
        
        return result
    
    def _find_best_quantity_increase(self, shop_items, needed_amount):
        """Znajduje najlepszy produkt do zwiększenia ilości"""
        best_option = None
        
        self.log(f"      🔍 Szukam najlepszego produktu do zwiększenia (potrzeba: {needed_amount:.2f} PLN)")
        
        for item in shop_items:
            unit_price = item['unit_price_pln']
            current_qty = item['quantity']
            
            # POPRAWKA: Sprawdź różne opcje zwiększenia ilości
            for additional_qty in [1, 2, 3, 5, 10]:  # Dodajemy różne opcje
                new_quantity = current_qty + additional_qty
                additional_cost = additional_qty * unit_price
                
                # Sprawdź limit mnożnika
                if new_quantity > current_qty * self.max_quantity_multiplier:
                    continue
                
                if additional_cost >= needed_amount:
                    efficiency = needed_amount / additional_cost
                    
                    product_name = item.get('product_name', f"ID:{item['product_id']}")
                    self.log(f"         💭 {product_name}: +{additional_qty} szt = +{additional_cost:.2f} PLN (efektywność: {efficiency:.3f})")
                    
                    if not best_option or efficiency > best_option['efficiency']:
                        best_option = {
                            'item': item,
                            'new_quantity': new_quantity,
                            'additional_cost': additional_cost,
                            'efficiency': efficiency,
                            'additional_qty': additional_qty
                        }
                        self.log(f"         ⭐ NOWA NAJLEPSZA OPCJA!")
        
        if best_option:
            item_name = best_option['item'].get('product_name', f"ID:{best_option['item']['product_id']}")
            self.log(f"      🎯 WYBRANO: {item_name} +{best_option['additional_qty']} szt za {best_option['additional_cost']:.2f} PLN")
        else:
            self.log(f"      ❌ Brak odpowiednich opcji zwiększenia ilości")
        
        return best_option