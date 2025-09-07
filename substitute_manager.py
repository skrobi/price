"""
Moduł do zarządzania zamiennością produktów
"""
import json
import os
from datetime import datetime
from utils.data_utils import load_products, save_product, load_prices, get_latest_prices, convert_to_pln

class SubstituteManager:
    """Zarządzanie zamiennością produktów"""
    
    def __init__(self):
        self.substitutes_file = 'data/substitutes.txt'
        self.ensure_data_dir()
    
    def ensure_data_dir(self):
        """Upewnij się że folder data istnieje"""
        if not os.path.exists('data'):
            os.makedirs('data')
    
    def load_substitute_groups(self):
        """Ładuje grupy zamienników z pliku"""
        try:
            with open(self.substitutes_file, 'r', encoding='utf-8') as f:
                groups = {}
                for line in f:
                    if line.strip():
                        try:
                            group = json.loads(line)
                            groups[group['group_id']] = group
                        except (json.JSONDecodeError, KeyError) as e:
                            print(f"Błąd w linii grup zamienników: {e}")
                            continue
                return groups
        except FileNotFoundError:
            return {}
    
    def save_substitute_group(self, group_data):
        """Zapisuje grupę zamienników do pliku"""
        groups = self.load_substitute_groups()
        groups[group_data['group_id']] = group_data
        
        with open(self.substitutes_file, 'w', encoding='utf-8') as f:
            for group in groups.values():
                f.write(json.dumps(group, ensure_ascii=False) + '\n')
    
    def create_substitute_group(self, name, product_ids, priority_map=None):
        """
        Tworzy nową grupę zamienników
        
        Args:
            name: nazwa grupy (np. "iPhone 15 różne pojemności")
            product_ids: lista ID produktów w grupie
            priority_map: dict {product_id: priority} gdzie 1=preferowany, 2=alternatywa, itd.
        """
        groups = self.load_substitute_groups()
        group_id = f"group_{len(groups) + 1}_{int(datetime.now().timestamp())}"
        
        if priority_map is None:
            priority_map = {pid: 1 for pid in product_ids}  # wszyscy równi domyślnie
        
        group_data = {
            "group_id": group_id,
            "name": name,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "product_ids": product_ids,
            "priority_map": priority_map,
            "settings": {
                "max_price_increase_percent": 20.0,  # max 20% drożej
                "min_quantity_ratio": 0.8,  # min 80% ilości
                "max_quantity_ratio": 1.5,  # max 150% ilości
                "allow_automatic_substitution": True
            }
        }
        
        self.save_substitute_group(group_data)
        
        # Aktualizuj produkty - dodaj informację o grupie
        self._update_products_with_group(product_ids, group_id)
        
        return group_id
    
    def _update_products_with_group(self, product_ids, group_id):
        """Aktualizuje produkty - dodaje im informację o grupie zamienników"""
        products = load_products()
        
        for product in products:
            if product['id'] in product_ids:
                product['substitute_group'] = group_id
                product['updated'] = datetime.now().isoformat()
        
        # Przepisz plik produktów
        with open('data/products.txt', 'w', encoding='utf-8') as f:
            for product in products:
                f.write(json.dumps(product, ensure_ascii=False) + '\n')
    
    def get_substitutes_for_product(self, product_id):
        """
        Zwraca listę zamienników dla danego produktu
        
        Returns:
            dict: {
                'group_id': str,
                'substitutes': [list of product dicts],
                'settings': dict
            }
        """
        groups = self.load_substitute_groups()
        products = load_products()
        
        # Znajdź grupę dla tego produktu
        target_group = None
        for group in groups.values():
            if product_id in group['product_ids']:
                target_group = group
                break
        
        if not target_group:
            return {
                'group_id': None,
                'substitutes': [],
                'settings': {}
            }
        
        # Znajdź wszystkie produkty w grupie oprócz bieżącego
        substitute_products = []
        for pid in target_group['product_ids']:
            if pid != product_id:
                product = next((p for p in products if p['id'] == pid), None)
                if product:
                    product['priority'] = target_group['priority_map'].get(pid, 99)
                    substitute_products.append(product)
        
        # Sortuj według priorytetu
        substitute_products.sort(key=lambda x: x['priority'])
        
        return {
            'group_id': target_group['group_id'],
            'substitutes': substitute_products,
            'settings': target_group['settings']
        }
    
    def find_best_substitute_offers(self, product_id, requested_quantity, max_price_increase_percent=20.0):
        """
        Znajduje najlepsze oferty dla produktu lub jego zamienników
        
        Args:
            product_id: ID głównego produktu
            requested_quantity: żądana ilość
            max_price_increase_percent: maksymalny wzrost ceny w %
            
        Returns:
            list: [
                {
                    'product_id': int,
                    'is_substitute': bool,
                    'substitute_reason': str,
                    'offers': [list],
                    'best_price_pln': float,
                    'priority': int
                }
            ]
        """
        results = []
        latest_prices = get_latest_prices()
        
        # Dodaj oryginalny produkt
        original_offers = self._get_product_offers(product_id, latest_prices)
        if original_offers:
            results.append({
                'product_id': product_id,
                'is_substitute': False,
                'substitute_reason': '',
                'offers': original_offers,
                'best_price_pln': min(offer['price_pln'] for offer in original_offers),
                'priority': 0  # najwyższy priorytet
            })
        
        # Dodaj zamienniki
        substitute_info = self.get_substitutes_for_product(product_id)
        
        if substitute_info['substitutes']:
            # Znajdź najlepszą cenę oryginału dla porównania
            original_best_price = None
            if original_offers:
                original_best_price = min(offer['price_pln'] for offer in original_offers)
            
            for substitute in substitute_info['substitutes']:
                sub_offers = self._get_product_offers(substitute['id'], latest_prices)
                
                if sub_offers:
                    sub_best_price = min(offer['price_pln'] for offer in sub_offers)
                    
                    # Sprawdź czy cena zamiennika jest akceptowalna
                    price_acceptable = True
                    reason = f"Zamiennik (priorytet {substitute['priority']})"
                    
                    if original_best_price:
                        price_increase = ((sub_best_price - original_best_price) / original_best_price) * 100
                        if price_increase > max_price_increase_percent:
                            price_acceptable = False
                            reason += f" - za drogi (+{price_increase:.1f}%)"
                        elif price_increase < 0:
                            reason += f" - tańszy o {abs(price_increase):.1f}%"
                        else:
                            reason += f" - droższy o {price_increase:.1f}%"
                    
                    if price_acceptable:
                        results.append({
                            'product_id': substitute['id'],
                            'is_substitute': True,
                            'substitute_reason': reason,
                            'offers': sub_offers,
                            'best_price_pln': sub_best_price,
                            'priority': substitute['priority']
                        })
        
        # Sortuj według priorytetu, potem według ceny
        results.sort(key=lambda x: (x['priority'], x['best_price_pln']))
        
        return results
    
    def _get_product_offers(self, product_id, latest_prices):
        """Pobiera oferty dla konkretnego produktu"""
        offers = []
        
        for key, price_data in latest_prices.items():
            if price_data['product_id'] == product_id and price_data.get('price'):
                currency = price_data.get('currency', 'PLN')
                price_pln = convert_to_pln(price_data['price'], currency)
                
                offers.append({
                    'product_id': product_id,
                    'shop_id': price_data['shop_id'],
                    'price_pln': price_pln,
                    'price_original': price_data['price'],
                    'currency': currency
                })
        
        # Sortuj według ceny
        offers.sort(key=lambda x: x['price_pln'])
        return offers
    
    def get_all_substitute_groups(self):
        """Zwraca wszystkie grupy zamienników z dodatkowymi informacjami"""
        groups = self.load_substitute_groups()
        products = load_products()
        
        enriched_groups = []
        
        for group in groups.values():
            group_products = []
            for pid in group['product_ids']:
                product = next((p for p in products if p['id'] == pid), None)
                if product:
                    product['priority'] = group['priority_map'].get(pid, 99)
                    group_products.append(product)
            
            group_products.sort(key=lambda x: x['priority'])
            
            enriched_groups.append({
                'group_id': group['group_id'],
                'name': group['name'],
                'created': group['created'],
                'product_count': len(group_products),
                'products': group_products,
                'settings': group['settings']
            })
        
        return enriched_groups
    
    def remove_product_from_group(self, product_id):
        """Usuwa produkt ze wszystkich grup zamienników"""
        groups = self.load_substitute_groups()
        products = load_products()
        
        modified = False
        
        for group in groups.values():
            if product_id in group['product_ids']:
                group['product_ids'].remove(product_id)
                if product_id in group['priority_map']:
                    del group['priority_map'][product_id]
                group['updated'] = datetime.now().isoformat()
                modified = True
                
                # Jeśli grupa ma mniej niż 2 produkty, usuń ją
                if len(group['product_ids']) < 2:
                    del groups[group['group_id']]
        
        if modified:
            # Zapisz grupy
            with open(self.substitutes_file, 'w', encoding='utf-8') as f:
                for group in groups.values():
                    f.write(json.dumps(group, ensure_ascii=False) + '\n')
            
            # Usuń informację o grupie z produktu
            for product in products:
                if product['id'] == product_id and 'substitute_group' in product:
                    del product['substitute_group']
                    product['updated'] = datetime.now().isoformat()
            
            with open('data/products.txt', 'w', encoding='utf-8') as f:
                for product in products:
                    f.write(json.dumps(product, ensure_ascii=False) + '\n')
    
    def update_group_settings(self, group_id, settings):
        """Aktualizuje ustawienia grupy zamienników"""
        groups = self.load_substitute_groups()
        
        if group_id in groups:
            groups[group_id]['settings'].update(settings)
            groups[group_id]['updated'] = datetime.now().isoformat()
            self.save_substitute_group(groups[group_id])
            return True
        
        return False
    
    def delete_substitute_group(self, group_id):
        """Usuwa grupę zamienników"""
        groups = self.load_substitute_groups()
        products = load_products()
        
        if group_id in groups:
            # Usuń informację o grupie z produktów
            product_ids = groups[group_id]['product_ids']
            for product in products:
                if product['id'] in product_ids and product.get('substitute_group') == group_id:
                    del product['substitute_group']
                    product['updated'] = datetime.now().isoformat()
            
            # Usuń grupę
            del groups[group_id]
            
            # Zapisz zmiany
            with open(self.substitutes_file, 'w', encoding='utf-8') as f:
                for group in groups.values():
                    f.write(json.dumps(group, ensure_ascii=False) + '\n')
            
            with open('data/products.txt', 'w', encoding='utf-8') as f:
                for product in products:
                    f.write(json.dumps(product, ensure_ascii=False) + '\n')
            
            return True
        
        return False

# Singleton instance
substitute_manager = SubstituteManager()