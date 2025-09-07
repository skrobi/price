"""
Moduł oceny kombinacji zakupów
"""
import copy

class CombinationEvaluator:
    """Klasa odpowiedzialna za ocenę kombinacji zakupów"""
    
    def __init__(self, settings, log_func):
        self.settings = settings
        self.log = log_func
        self.priority = settings.get('priority', 'lowest_total_cost')
    
    def calculate_combination_result(self, combination, product_ids, basket, shop_configs):
        """Przelicza kombinację na format wynikowy z nazwami produktów"""
        
        # Grupuj produkty według sklepów
        shops_summary = {}
        items_list = []
        
        for i, offer in enumerate(combination):
            shop_id = offer['shop_id']
            
            # OBSŁUGA ZAMIENNIKÓW - określ prawidłowy product_id
            if offer.get('is_substitute', False):
                product_id = offer.get('original_product_id', product_ids[i])
                actual_substitute_id = offer.get('substitute_product_id', product_ids[i])
                substitute_name = offer.get('substitute_name', f'Zamiennik {actual_substitute_id}')
                self.log(f"   🔄 Używam zamiennika: {substitute_name} (ID:{actual_substitute_id}) zamiast produktu {product_id}")
            else:
                product_id = product_ids[i]
            
            product_key = str(product_id)
            
            # Pobierz podstawową ilość z koszyka
            base_quantity = basket['basket_items'][product_key]['requested_quantity']
            unit_price = offer['price_pln']
            
            # POPRAWKA: Pobierz nazwę produktu z różnych źródeł
            if offer.get('is_substitute', False):
                # Dla zamienników - użyj nazwy zamiennika lub znajdź w bazie produktów
                product_name = offer.get('substitute_name', '')
                if not product_name or product_name.startswith('Zamiennik '):
                    # Spróbuj znaleźć prawdziwą nazwę produktu zamiennika
                    try:
                        from utils.data_utils import load_products
                        all_products = load_products()
                        substitute_product = next((p for p in all_products if p['id'] == actual_substitute_id), None)
                        if substitute_product:
                            product_name = f"{substitute_product['name']} (zamiennik)"
                        else:
                            product_name = f"Zamiennik {actual_substitute_id}"
                    except:
                        product_name = f"Zamiennik {actual_substitute_id}"
            else:
                # Dla produktów oryginalnych - weź z koszyka lub znajdź w bazie
                product_name = basket['basket_items'][product_key].get('product_name', '')
                if not product_name:
                    # Spróbuj znaleźć w bazie produktów
                    try:
                        from utils.data_utils import load_products
                        all_products = load_products()
                        original_product = next((p for p in all_products if p['id'] == product_id), None)
                        if original_product:
                            product_name = original_product['name']
                        else:
                            product_name = f'Produkt {product_id}'
                    except:
                        product_name = f'Produkt {product_id}'
            
            # Jeśli nadal nie ma nazwy, użyj domyślnej
            if not product_name or product_name.strip() == '':
                product_name = f'Produkt {product_id}'
            
            # Inicjalizuj dane przedmiotu
            item_data = {
                'product_id': product_id,  # ID z koszyka (dla powiązania)
                'product_name': product_name,  # POPRAWIONA NAZWA
                'actual_product_id': actual_substitute_id if offer.get('is_substitute') else product_id,
                'shop_id': shop_id,
                'quantity': base_quantity,
                'unit_price_pln': unit_price,
                'total_price_pln': unit_price * base_quantity,
                'is_substitute': offer.get('is_substitute', False),
                'substitute_reason': offer.get('substitute_reason', ''),
                'quantity_optimized': False,
                'optimization_reason': ''
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
            free_from = config.get('delivery_free_from')
            shipping_cost = config.get('delivery_cost', 0)
            
            if free_from and summary['subtotal'] >= free_from:
                summary['shipping_cost'] = 0
                self.log(f"   🚚 {shop_id}: Darmowa dostawa (≥{free_from} PLN)")
            else:
                summary['shipping_cost'] = shipping_cost or 0
                self.log(f"   🚚 {shop_id}: Dostawa {summary['shipping_cost']:.2f} PLN")
            
            total_shipping_cost += summary['shipping_cost']
        
        total_cost = total_products_cost + total_shipping_cost
        
        # Loguj podsumowanie kombinacji z nazwami produktów
        self.log(f"   💵 Produkty: {total_products_cost:.2f} PLN")
        self.log(f"   🚚 Transport: {total_shipping_cost:.2f} PLN")
        self.log(f"   💳 RAZEM: {total_cost:.2f} PLN")
        
        # Loguj szczegóły produktów
        for item in items_list:
            if item.get('is_substitute'):
                self.log(f"   📦 {item['product_name']} - {item['quantity']} szt × {item['unit_price_pln']:.2f} PLN = {item['total_price_pln']:.2f} PLN")
            else:
                self.log(f"   📦 {item['product_name']} - {item['quantity']} szt × {item['unit_price_pln']:.2f} PLN = {item['total_price_pln']:.2f} PLN")
        
        return {
            'items_list': items_list,
            'shops_summary': shops_summary,
            'total_products_cost': total_products_cost,
            'total_shipping_cost': total_shipping_cost,
            'total_cost': total_cost,
            'shops_count': len(shops_summary)
        }
    
    def calculate_score(self, result):
        """Oblicza wynik według wybranego priorytetu"""
        if self.priority == 'fewest_shops':
            score = result['shops_count'] * 1000 + result['total_cost']
            self.log(f"   📊 Wynik (najmniej sklepów): {result['shops_count']} × 1000 + {result['total_cost']:.2f} = {score:.2f}")
        elif self.priority == 'balanced':
            penalty = (result['shops_count'] - 1) * 15
            score = result['total_cost'] + penalty
            self.log(f"   📊 Wynik (zbalansowany): {result['total_cost']:.2f} + kara {penalty:.2f} = {score:.2f}")
        else:  # lowest_total_cost
            score = result['total_cost']
            self.log(f"   📊 Wynik (najniższy koszt): {score:.2f}")
        
        return score