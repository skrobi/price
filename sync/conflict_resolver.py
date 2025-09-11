"""
System rozwiązywania konfliktów podczas synchronizacji danych
"""
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Callable
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class ConflictStrategy(Enum):
    """Strategie rozwiązywania konfliktów"""
    API_WINS = "api_wins"              # API ma zawsze rację
    LOCAL_WINS = "local_wins"          # Lokalne dane mają rację
    NEWEST_WINS = "newest_wins"        # Najnowszy timestamp wygrywa
    USER_CHOICE = "user_choice"        # Pyta użytkownika
    MERGE = "merge"                    # Próbuje scalić dane
    SKIP = "skip"                      # Pomija konfliktowy element

class ConflictType(Enum):
    """Typy konfliktów"""
    DATA_MISMATCH = "data_mismatch"    # Różne dane dla tego samego ID
    DUPLICATE_ENTRY = "duplicate"      # Duplikat wpisu
    MISSING_DEPENDENCY = "missing_dep" # Brakuje powiązanego obiektu
    VERSION_CONFLICT = "version"       # Konflikt wersji
    CONSTRAINT_VIOLATION = "constraint" # Naruszenie ograniczeń

class ConflictItem:
    """Reprezentuje pojedynczy konflikt"""
    
    def __init__(self, conflict_type: ConflictType, entity_type: str, 
                 entity_id: Any, local_data: Dict[str, Any], 
                 remote_data: Dict[str, Any], description: str = ""):
        self.conflict_type = conflict_type
        self.entity_type = entity_type  # 'product', 'link', 'price', etc.
        self.entity_id = entity_id
        self.local_data = local_data
        self.remote_data = remote_data
        self.description = description
        self.created_at = datetime.now()
        self.resolved = False
        self.resolution_strategy = None
        self.resolved_data = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik dla serializacji"""
        return {
            'conflict_type': self.conflict_type.value,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'local_data': self.local_data,
            'remote_data': self.remote_data,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'resolved': self.resolved,
            'resolution_strategy': self.resolution_strategy.value if self.resolution_strategy else None,
            'resolved_data': self.resolved_data
        }

class ConflictResolver:
    """Główna klasa rozwiązywania konfliktów"""
    
    def __init__(self):
        self.default_strategies = {
            'product': ConflictStrategy.NEWEST_WINS,
            'link': ConflictStrategy.API_WINS,
            'price': ConflictStrategy.NEWEST_WINS,
            'shop_config': ConflictStrategy.MERGE,
            'substitute_group': ConflictStrategy.API_WINS
        }
        
        # Callback do interakcji z użytkownikiem
        self.user_choice_callback: Optional[Callable[[ConflictItem], Dict[str, Any]]] = None
        
        # Historia konfliktów
        self.conflict_history: List[ConflictItem] = []
    
    def set_user_choice_callback(self, callback: Callable[[ConflictItem], Dict[str, Any]]):
        """
        Ustaw callback do obsługi konfliktów wymagających wyboru użytkownika
        
        Args:
            callback: Funkcja(ConflictItem) -> Dict z kluczami 'strategy' i opcjonalnie 'data'
        """
        self.user_choice_callback = callback
    
    def detect_conflicts(self, local_data: List[Dict], remote_data: List[Dict], 
                        entity_type: str, id_field: str = 'id') -> List[ConflictItem]:
        """
        Wykryj konflikty między danymi lokalnymi a zdalnymi
        
        Args:
            local_data: Lista lokalnych obiektów
            remote_data: Lista zdalnych obiektów
            entity_type: Typ encji ('product', 'link', etc.)
            id_field: Pole używane jako identyfikator
        
        Returns:
            Lista wykrytych konfliktów
        """
        conflicts = []
        
        # Stwórz mapę dla szybkiego wyszukiwania
        local_map = {item[id_field]: item for item in local_data if id_field in item}
        remote_map = {item[id_field]: item for item in remote_data if id_field in item}
        
        # Sprawdź konflikty danych
        for item_id, local_item in local_map.items():
            if item_id in remote_map:
                remote_item = remote_map[item_id]
                conflict = self._compare_items(local_item, remote_item, entity_type, item_id)
                if conflict:
                    conflicts.append(conflict)
        
        # Sprawdź duplikaty (różne ID, ale te same dane)
        conflicts.extend(self._detect_duplicates(local_data, remote_data, entity_type, id_field))
        
        logger.info(f"Detected {len(conflicts)} conflicts for {entity_type}")
        return conflicts
    
    def _compare_items(self, local_item: Dict, remote_item: Dict, 
                      entity_type: str, item_id: Any) -> Optional[ConflictItem]:
        """Porównaj dwa elementy i wykryj konflikty"""
        
        # Pola do ignorowania przy porównaniu
        ignore_fields = {'created_at', 'updated_at', 'user_id', 'source'}
        
        # Porównaj znaczące pola
        local_significant = {k: v for k, v in local_item.items() if k not in ignore_fields}
        remote_significant = {k: v for k, v in remote_item.items() if k not in ignore_fields}
        
        if local_significant != remote_significant:
            # Wykryj różnice
            differences = []
            all_keys = set(local_significant.keys()) | set(remote_significant.keys())
            
            for key in all_keys:
                local_val = local_significant.get(key)
                remote_val = remote_significant.get(key)
                if local_val != remote_val:
                    differences.append(f"{key}: local='{local_val}' vs remote='{remote_val}'")
            
            description = f"Data mismatch in {entity_type} {item_id}: " + "; ".join(differences)
            
            return ConflictItem(
                ConflictType.DATA_MISMATCH,
                entity_type,
                item_id,
                local_item,
                remote_item,
                description
            )
        
        return None
    
    def _detect_duplicates(self, local_data: List[Dict], remote_data: List[Dict],
                          entity_type: str, id_field: str) -> List[ConflictItem]:
        """Wykryj potencjalne duplikaty o różnych ID"""
        conflicts = []
        
        # Dla produktów sprawdź po nazwie i EAN
        if entity_type == 'product':
            conflicts.extend(self._detect_product_duplicates(local_data, remote_data))
        
        # Dla linków sprawdź po URL
        elif entity_type == 'link':
            conflicts.extend(self._detect_link_duplicates(local_data, remote_data))
        
        return conflicts
    
    def _detect_product_duplicates(self, local_data: List[Dict], 
                                  remote_data: List[Dict]) -> List[ConflictItem]:
        """Wykryj duplikaty produktów po nazwie lub EAN"""
        conflicts = []
        
        for local_product in local_data:
            local_name = local_product.get('name', '').strip().lower()
            local_ean = local_product.get('ean', '').strip()
            
            for remote_product in remote_data:
                # Pomiń jeśli to ten sam ID
                if local_product.get('id') == remote_product.get('id'):
                    continue
                
                remote_name = remote_product.get('name', '').strip().lower()
                remote_ean = remote_product.get('ean', '').strip()
                
                # Sprawdź duplikat po nazwie
                if local_name and remote_name and local_name == remote_name:
                    conflicts.append(ConflictItem(
                        ConflictType.DUPLICATE_ENTRY,
                        'product',
                        f"{local_product.get('id')}-{remote_product.get('id')}",
                        local_product,
                        remote_product,
                        f"Duplicate product name: '{local_product.get('name')}'"
                    ))
                
                # Sprawdź duplikat po EAN
                elif local_ean and remote_ean and local_ean == remote_ean:
                    conflicts.append(ConflictItem(
                        ConflictType.DUPLICATE_ENTRY,
                        'product',
                        f"{local_product.get('id')}-{remote_product.get('id')}",
                        local_product,
                        remote_product,
                        f"Duplicate product EAN: '{local_ean}'"
                    ))
        
        return conflicts
    
    def _detect_link_duplicates(self, local_data: List[Dict], 
                               remote_data: List[Dict]) -> List[ConflictItem]:
        """Wykryj duplikaty linków po URL"""
        conflicts = []
        
        for local_link in local_data:
            local_url = local_link.get('url', '').strip()
            
            if not local_url:
                continue
            
            for remote_link in remote_data:
                # Pomiń jeśli to ten sam ID
                if local_link.get('id') == remote_link.get('id'):
                    continue
                
                remote_url = remote_link.get('url', '').strip()
                
                if local_url == remote_url:
                    conflicts.append(ConflictItem(
                        ConflictType.DUPLICATE_ENTRY,
                        'link',
                        f"{local_link.get('id')}-{remote_link.get('id')}",
                        local_link,
                        remote_link,
                        f"Duplicate URL: '{local_url}'"
                    ))
        
        return conflicts
    
    def resolve_conflict(self, conflict: ConflictItem, 
                        strategy: Optional[ConflictStrategy] = None) -> Dict[str, Any]:
        """
        Rozwiąż konflikt używając określonej strategii
        
        Args:
            conflict: Konflikt do rozwiązania
            strategy: Strategia rozwiązania (jeśli None, użyje domyślnej)
        
        Returns:
            Dict z rozwiązanymi danymi
        """
        if strategy is None:
            strategy = self.default_strategies.get(conflict.entity_type, ConflictStrategy.NEWEST_WINS)
        
        logger.info(f"CONFLICT RESOLVE: {conflict.entity_type} ID={conflict.entity_id}")
        logger.info(f"LOCAL: {conflict.local_data}")
        logger.info(f"REMOTE: {conflict.remote_data}")
        logger.info(f"STRATEGY: {strategy.value}")
        logger.info(f"Resolving {conflict.conflict_type.value} conflict for {conflict.entity_type} "
                   f"{conflict.entity_id} using {strategy.value}")
        
        resolved_data = None
        
        try:
            if strategy == ConflictStrategy.API_WINS:
                resolved_data = conflict.remote_data.copy()
                logger.info(f"API_WINS: using remote data")
            
            elif strategy == ConflictStrategy.LOCAL_WINS:
                resolved_data = conflict.local_data.copy()
                logger.info(f"LOCAL_WINS: using local data")
            
            elif strategy == ConflictStrategy.NEWEST_WINS:
                resolved_data = self._resolve_by_timestamp(conflict.local_data, conflict.remote_data)
                logger.info(f"NEWEST_WINS: chose data")
            
            elif strategy == ConflictStrategy.MERGE:
                resolved_data = self._merge_data(conflict.local_data, conflict.remote_data, conflict.entity_type)
            
            elif strategy == ConflictStrategy.USER_CHOICE:
                if self.user_choice_callback:
                    user_decision = self.user_choice_callback(conflict)
                    user_strategy = ConflictStrategy(user_decision.get('strategy', 'api_wins'))
                    if 'data' in user_decision:
                        resolved_data = user_decision['data']
                    else:
                        # Rekurencyjnie wywołaj z wybraną strategią
                        return self.resolve_conflict(conflict, user_strategy)
                else:
                    logger.warning("User choice requested but no callback set, falling back to API_WINS")
                    resolved_data = conflict.remote_data.copy()
            
            elif strategy == ConflictStrategy.SKIP:
                logger.info(f"Skipping conflict for {conflict.entity_type} {conflict.entity_id}")
                resolved_data = None
            
            # Oznacz konflikt jako rozwiązany
            conflict.resolved = True
            conflict.resolution_strategy = strategy
            conflict.resolved_data = resolved_data
            self.conflict_history.append(conflict)
            
            return {
                'success': True,
                'strategy': strategy.value,
                'data': resolved_data,
                'conflict_id': id(conflict)
            }
            
        except Exception as e:
            logger.error(f"Error resolving conflict: {e}")
            return {
                'success': False,
                'error': str(e),
                'conflict_id': id(conflict)
            }
    
    def _resolve_by_timestamp(self, local_data: Dict, remote_data: Dict) -> Dict[str, Any]:
        """Rozwiąż konflikt na podstawie timestamp'u (najnowszy wygrywa)"""
        
        # Pola z timestamp'ami do sprawdzenia
        timestamp_fields = ['updated_at', 'created_at', 'updated', 'created']
        
        local_timestamp = None
        remote_timestamp = None
        
        # Znajdź najnowszy timestamp w danych lokalnych
        for field in timestamp_fields:
            if field in local_data and local_data[field]:
                try:
                    local_timestamp = datetime.fromisoformat(local_data[field].replace('Z', '+00:00'))
                    break
                except:
                    continue
        
        # Znajdź najnowszy timestamp w danych zdalnych
        for field in timestamp_fields:
            if field in remote_data and remote_data[field]:
                try:
                    remote_timestamp = datetime.fromisoformat(remote_data[field].replace('Z', '+00:00'))
                    break
                except:
                    continue
        
        # Porównaj timestamp'y
        if local_timestamp and remote_timestamp:
            if local_timestamp > remote_timestamp:
                logger.debug("Local data is newer, using local")
                return local_data.copy()
            else:
                logger.debug("Remote data is newer, using remote")
                return remote_data.copy()
        elif local_timestamp:
            logger.debug("Only local has timestamp, using local")
            return local_data.copy()
        elif remote_timestamp:
            logger.debug("Only remote has timestamp, using remote")
            return remote_data.copy()
        else:
            logger.debug("No timestamps found, defaulting to remote")
            return remote_data.copy()
    
    def _merge_data(self, local_data: Dict, remote_data: Dict, entity_type: str) -> Dict[str, Any]:
        """Scal dane lokalne i zdalne inteligentnie"""
        
        merged = remote_data.copy()  # Zacznij od danych zdalnych
        
        # Strategia scalania zależna od typu encji
        if entity_type == 'shop_config':
            # Dla konfiguracji sklepów, scal selektory
            local_selectors = local_data.get('price_selectors', {})
            remote_selectors = remote_data.get('price_selectors', {})
            
            if isinstance(local_selectors, dict) and isinstance(remote_selectors, dict):
                merged_selectors = {}
                
                # Scal każdy typ selektora
                for selector_type in set(local_selectors.keys()) | set(remote_selectors.keys()):
                    local_list = local_selectors.get(selector_type, [])
                    remote_list = remote_selectors.get(selector_type, [])
                    
                    # Połącz i usuń duplikaty, zachowując kolejność
                    combined = remote_list.copy()
                    for item in local_list:
                        if item not in combined:
                            combined.append(item)
                    
                    merged_selectors[selector_type] = combined
                
                merged['price_selectors'] = merged_selectors
            
            # Dla innych pól, użyj lokalnych jeśli są ustawione
            numeric_fields = ['delivery_free_from', 'delivery_cost']
            for field in numeric_fields:
                if field in local_data and local_data[field] is not None:
                    merged[field] = local_data[field]
        
        else:
            # Dla innych typów, po prostu nadpisz pola które są ustawione lokalnie
            for key, value in local_data.items():
                if value is not None and value != '':
                    merged[key] = value
        
        logger.debug(f"Merged {entity_type} data")
        return merged
    
    def resolve_all_conflicts(self, conflicts: List[ConflictItem]) -> Dict[str, Any]:
        """
        Rozwiąż wszystkie konflikty używając domyślnych strategii
        
        Returns:
            Podsumowanie rozwiązań
        """
        if not conflicts:
            return {'total': 0, 'resolved': 0, 'failed': 0, 'skipped': 0}
        
        logger.info(f"Resolving {len(conflicts)} conflicts")
        
        resolved = 0
        failed = 0
        skipped = 0
        resolution_results = []
        
        for conflict in conflicts:
            result = self.resolve_conflict(conflict)
            resolution_results.append(result)
            
            if result['success']:
                if result.get('strategy') == 'skip':
                    skipped += 1
                else:
                    resolved += 1
            else:
                failed += 1
        
        summary = {
            'total': len(conflicts),
            'resolved': resolved,
            'failed': failed,
            'skipped': skipped,
            'results': resolution_results
        }
        
        logger.info(f"Conflict resolution summary: {resolved} resolved, {failed} failed, {skipped} skipped")
        return summary
    
    def get_conflict_statistics(self) -> Dict[str, Any]:
        """Zwróć statystyki konfliktów"""
        if not self.conflict_history:
            return {'total_conflicts': 0}
        
        stats = {
            'total_conflicts': len(self.conflict_history),
            'by_type': {},
            'by_entity': {},
            'by_strategy': {},
            'resolved_count': 0,
            'unresolved_count': 0
        }
        
        for conflict in self.conflict_history:
            # Statystyki po typie konfliktu
            conflict_type = conflict.conflict_type.value
            stats['by_type'][conflict_type] = stats['by_type'].get(conflict_type, 0) + 1
            
            # Statystyki po typie encji
            entity_type = conflict.entity_type
            stats['by_entity'][entity_type] = stats['by_entity'].get(entity_type, 0) + 1
            
            # Statystyki po strategii rozwiązania
            if conflict.resolution_strategy:
                strategy = conflict.resolution_strategy.value
                stats['by_strategy'][strategy] = stats['by_strategy'].get(strategy, 0) + 1
            
            # Statystyki rozwiązanych/nierozwiązanych
            if conflict.resolved:
                stats['resolved_count'] += 1
            else:
                stats['unresolved_count'] += 1
        
        return stats

def create_simple_user_choice_callback() -> Callable[[ConflictItem], Dict[str, Any]]:
    """Factory function dla prostego callback'a wyboru użytkownika w konsoli"""
    
    def console_choice_callback(conflict: ConflictItem) -> Dict[str, Any]:
        print(f"\n{'='*60}")
        print(f"CONFLICT DETECTED: {conflict.entity_type} {conflict.entity_id}")
        print(f"Type: {conflict.conflict_type.value}")
        print(f"Description: {conflict.description}")
        print(f"{'='*60}")
        
        print("\nLOCAL DATA:")
        for key, value in conflict.local_data.items():
            print(f"  {key}: {value}")
        
        print("\nREMOTE DATA:")
        for key, value in conflict.remote_data.items():
            print(f"  {key}: {value}")
        
        print(f"\n{'='*60}")
        print("Choose resolution strategy:")
        print("1. Use REMOTE data (from API)")
        print("2. Use LOCAL data")
        print("3. Use NEWEST data (by timestamp)")
        print("4. SKIP this conflict")
        print("5. MERGE data (if applicable)")
        
        while True:
            try:
                choice = input("\nEnter choice (1-5): ").strip()
                
                if choice == '1':
                    return {'strategy': 'api_wins'}
                elif choice == '2':
                    return {'strategy': 'local_wins'}
                elif choice == '3':
                    return {'strategy': 'newest_wins'}
                elif choice == '4':
                    return {'strategy': 'skip'}
                elif choice == '5':
                    return {'strategy': 'merge'}
                else:
                    print("Invalid choice. Please enter 1-5.")
            except KeyboardInterrupt:
                print("\nDefaulting to API wins...")
                return {'strategy': 'api_wins'}
    
    return console_choice_callback

# Przykład zaawansowanego callback'a z GUI (mock)
def create_gui_choice_callback(gui_handler) -> Callable[[ConflictItem], Dict[str, Any]]:
    """Factory function dla callback'a z GUI"""
    
    def gui_choice_callback(conflict: ConflictItem) -> Dict[str, Any]:
        # Tutaj byłaby integracja z rzeczywistym GUI
        # Na razie mock implementacja
        
        conflict_data = {
            'type': conflict.conflict_type.value,
            'entity': conflict.entity_type,
            'id': conflict.entity_id,
            'description': conflict.description,
            'local': conflict.local_data,
            'remote': conflict.remote_data
        }
        
        # Wywołaj GUI handler (to byłaby prawdziwa implementacja)
        # result = gui_handler.show_conflict_dialog(conflict_data)
        
        # Mock response - w rzeczywistości pochodziłby z GUI
        result = {
            'strategy': 'api_wins',  # Domyślna strategia
            'remember_choice': False  # Czy zapamiętać wybór dla tego typu
        }
        
        return result
    
    return gui_choice_callback

class ConflictResolutionBatch:
    """Klasa do batch'owego rozwiązywania konfliktów z postępem"""
    
    def __init__(self, resolver: ConflictResolver):
        self.resolver = resolver
        self.conflicts: List[ConflictItem] = []
        self.resolved_conflicts: List[ConflictItem] = []
        self.failed_conflicts: List[ConflictItem] = []
        
        # Callback'i postępu
        self.progress_callback: Optional[Callable[[int, int, ConflictItem], None]] = None
        self.completion_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    
    def add_conflicts(self, conflicts: List[ConflictItem]):
        """Dodaj konflikty do batch'a"""
        self.conflicts.extend(conflicts)
    
    def set_progress_callback(self, callback: Callable[[int, int, ConflictItem], None]):
        """Ustaw callback postępu: callback(completed, total, current_conflict)"""
        self.progress_callback = callback
    
    def set_completion_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Ustaw callback zakończenia: callback(summary)"""
        self.completion_callback = callback
    
    def resolve_all(self, auto_strategies: Optional[Dict[str, ConflictStrategy]] = None) -> Dict[str, Any]:
        """
        Rozwiąż wszystkie konflikty w batch'u
        
        Args:
            auto_strategies: Mapa entity_type -> strategy dla automatycznego rozwiązywania
        """
        if not self.conflicts:
            return {'total': 0, 'resolved': 0, 'failed': 0, 'skipped': 0}
        
        total_conflicts = len(self.conflicts)
        logger.info(f"Starting batch conflict resolution for {total_conflicts} conflicts")
        
        for i, conflict in enumerate(self.conflicts):
            # Wywołaj callback postępu
            if self.progress_callback:
                self.progress_callback(i, total_conflicts, conflict)
            
            # Wybierz strategię
            strategy = None
            if auto_strategies and conflict.entity_type in auto_strategies:
                strategy = auto_strategies[conflict.entity_type]
            
            # Rozwiąż konflikt
            result = self.resolver.resolve_conflict(conflict, strategy)
            
            if result['success']:
                self.resolved_conflicts.append(conflict)
            else:
                self.failed_conflicts.append(conflict)
                logger.error(f"Failed to resolve conflict {conflict.entity_id}: {result.get('error')}")
        
        # Finalne wywołanie callback'a postępu
        if self.progress_callback:
            self.progress_callback(total_conflicts, total_conflicts, None)
        
        # Przygotuj podsumowanie
        skipped_count = sum(1 for c in self.resolved_conflicts 
                           if c.resolution_strategy == ConflictStrategy.SKIP)
        
        summary = {
            'total': total_conflicts,
            'resolved': len(self.resolved_conflicts) - skipped_count,
            'failed': len(self.failed_conflicts),
            'skipped': skipped_count,
            'success_rate': ((len(self.resolved_conflicts) - skipped_count) / total_conflicts * 100) if total_conflicts > 0 else 0
        }
        
        # Wywołaj callback zakończenia
        if self.completion_callback:
            self.completion_callback(summary)
        
        logger.info(f"Batch conflict resolution completed: {summary}")
        return summary

# Singleton instance
conflict_resolver = ConflictResolver()