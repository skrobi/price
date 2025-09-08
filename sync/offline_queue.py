"""
Kolejka offline do przechowywania operacji gdy API jest niedostępne - POPRAWIONA
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class OfflineQueue:
    """Kolejka operacji offline z persistent storage - POPRAWIONA"""
    
    def __init__(self, queue_file: str = 'data/sync_queue.json'):
        self.queue_file = queue_file
        self.queue: List[Dict[str, Any]] = []
        self.max_queue_size = 1000
        self.max_attempts = 3
        self.ensure_data_dir()
        self.load_queue()
    
    def ensure_data_dir(self):
        """Upewnij się że folder data istnieje"""
        os.makedirs('data', exist_ok=True)
    
    def load_queue(self):
        """Załaduj kolejkę z pliku - POPRAWIONE"""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # POPRAWKA: Sprawdź czy plik nie jest pusty
                        self.queue = json.loads(content)
                    else:
                        self.queue = []  # Pusty plik = pusta kolejka
                        logger.info("Empty queue file found, starting with empty queue")
                logger.info(f"Loaded {len(self.queue)} items from offline queue")
            else:
                self.queue = []
                # POPRAWKA: Stwórz pusty plik
                self.save_queue()
                logger.info("No existing offline queue found, created empty queue")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading offline queue: {e}")
            self.queue = []
            # POPRAWKA: Stwórz nowy pusty plik w przypadku błędu
            try:
                self.save_queue()
                logger.info("Created new empty queue file after error")
            except Exception as save_error:
                logger.error(f"Failed to create new queue file: {save_error}")
    
    def save_queue(self):
        """Zapisz kolejkę do pliku - POPRAWIONE"""
        try:
            # POPRAWKA: Upewnij się że katalog istnieje
            os.makedirs(os.path.dirname(self.queue_file), exist_ok=True)
            
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(self.queue, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved {len(self.queue)} items to offline queue")
        except IOError as e:
            logger.error(f"Error saving offline queue: {e}")
    
    def add_to_queue(self, action: str, data: Dict[str, Any], 
                     priority: int = 0, metadata: Optional[Dict] = None):
        """
        Dodaj operację do kolejki offline
        
        Args:
            action: Typ operacji (np. 'add_product', 'add_price')
            data: Dane do wysłania
            priority: Priorytet (0 = najwyższy)
            metadata: Dodatkowe metadane
        """
        if len(self.queue) >= self.max_queue_size:
            logger.warning("Queue is full, removing oldest item")
            self.queue.pop(0)
        
        queue_item = {
            'id': self._generate_queue_id(),
            'action': action,
            'data': data,
            'priority': priority,
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat(),
            'attempts': 0,
            'last_attempt': None,
            'status': 'pending'  # pending, processing, failed, completed
        }
        
        self.queue.append(queue_item)
        
        # Sortuj po priorytecie (0 = najwyższy)
        self.queue.sort(key=lambda x: (x['priority'], x['created_at']))
        
        self.save_queue()
        logger.info(f"Added {action} to offline queue (queue size: {len(self.queue)})")
    
    def _generate_queue_id(self) -> str:
        """Generuj unikalny ID dla elementu kolejki"""
        timestamp = int(datetime.now().timestamp() * 1000000)
        return f"queue_{timestamp}"
    
    def get_pending_items(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Pobierz oczekujące elementy z kolejki"""
        pending = [item for item in self.queue if item['status'] == 'pending']
        if limit:
            return pending[:limit]
        return pending
    
    def mark_as_processing(self, queue_id: str):
        """Oznacz element jako przetwarzany"""
        for item in self.queue:
            if item['id'] == queue_id:
                item['status'] = 'processing'
                item['last_attempt'] = datetime.now().isoformat()
                item['attempts'] += 1
                break
        self.save_queue()
    
    def mark_as_completed(self, queue_id: str, result: Optional[Dict] = None):
        """Oznacz element jako ukończony i usuń z kolejki"""
        self.queue = [item for item in self.queue if item['id'] != queue_id]
        self.save_queue()
        logger.info(f"Removed completed item {queue_id} from queue")
    
    def mark_as_failed(self, queue_id: str, error: str):
        """Oznacz element jako nieudany"""
        for item in self.queue:
            if item['id'] == queue_id:
                item['status'] = 'failed'
                item['error'] = error
                item['failed_at'] = datetime.now().isoformat()
                
                # Jeśli przekroczono max próby, usuń z kolejki
                if item['attempts'] >= self.max_attempts:
                    logger.error(f"Item {queue_id} failed after {self.max_attempts} attempts, removing from queue")
                    self.queue = [i for i in self.queue if i['id'] != queue_id]
                else:
                    # Reset status do pending dla kolejnej próby
                    item['status'] = 'pending'
                    logger.warning(f"Item {queue_id} failed (attempt {item['attempts']}/{self.max_attempts}), will retry")
                break
        self.save_queue()
    
    def clear_queue(self):
        """Wyczyść całą kolejkę"""
        self.queue = []
        self.save_queue()
        logger.info("Cleared offline queue")
    
    def clear_failed_items(self):
        """Usuń wszystkie nieudane elementy"""
        original_count = len(self.queue)
        self.queue = [item for item in self.queue if item['status'] != 'failed']
        removed_count = original_count - len(self.queue)
        if removed_count > 0:
            self.save_queue()
            logger.info(f"Removed {removed_count} failed items from queue")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Pobierz statystyki kolejki"""
        stats = {
            'total_items': len(self.queue),
            'pending': 0,
            'processing': 0,
            'failed': 0,
            'oldest_item': None,
            'newest_item': None,
            'actions_count': {}
        }
        
        if not self.queue:
            return stats
        
        # Policz statusy
        for item in self.queue:
            status = item.get('status', 'pending')
            stats[status] = stats.get(status, 0) + 1
            
            # Policz akcje
            action = item.get('action', 'unknown')
            stats['actions_count'][action] = stats['actions_count'].get(action, 0) + 1
        
        # Znajdź najstarszy i najnowszy element
        sorted_by_date = sorted(self.queue, key=lambda x: x['created_at'])
        stats['oldest_item'] = sorted_by_date[0]['created_at']
        stats['newest_item'] = sorted_by_date[-1]['created_at']
        
        return stats
    
    def process_queue_with_api(self, api_client):
        """
        Przetwórz kolejkę używając API client
        
        Args:
            api_client: Instancja PriceTrackerAPIClient
        
        Returns:
            Dict ze statystykami przetwarzania
        """
        if not api_client.is_online:
            logger.warning("API is offline, skipping queue processing")
            return {'processed': 0, 'failed': 0, 'skipped': len(self.queue)}
        
        pending_items = self.get_pending_items()
        if not pending_items:
            logger.info("No pending items in offline queue")
            return {'processed': 0, 'failed': 0, 'skipped': 0}
        
        logger.info(f"Processing {len(pending_items)} items from offline queue")
        
        processed = 0
        failed = 0
        
        for item in pending_items:
            queue_id = item['id']
            action = item['action']
            data = item['data']
            
            try:
                self.mark_as_processing(queue_id)
                result = self._execute_api_action(api_client, action, data)
                self.mark_as_completed(queue_id, result)
                processed += 1
                logger.debug(f"Successfully processed {action} from queue")
                
            except Exception as e:
                self.mark_as_failed(queue_id, str(e))
                failed += 1
                logger.error(f"Failed to process {action} from queue: {e}")
        
        stats = {'processed': processed, 'failed': failed, 'skipped': 0}
        logger.info(f"Queue processing completed: {stats}")
        return stats
    
    def _execute_api_action(self, api_client, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wykonaj konkretną akcję API na podstawie typu
        
        Args:
            api_client: Klient API
            action: Typ akcji
            data: Dane do przesłania
        
        Returns:
            Wynik z API
        """
        # Mapowanie akcji na metody API
        action_map = {
            'add_product': lambda: api_client.add_product(data['name'], data.get('ean', '')),
            'add_link': lambda: api_client.add_link(data['product_id'], data['shop_id'], data['url']),
            'add_price': lambda: api_client.add_price(
                data['product_id'], data['shop_id'], data['price'],
                data.get('currency', 'PLN'), data.get('price_type', 'scraped'),
                data.get('url', ''), data.get('source', 'offline_queue')
            ),
            'update_shop_config': lambda: api_client.update_shop_config(data),
            'add_substitute_group': lambda: api_client.add_substitute_group(
                data['name'], data['product_ids'],
                data.get('priority_map'), data.get('settings')
            ),
            'bulk_add_products': lambda: api_client.bulk_add_products(data['products']),
            'bulk_add_links': lambda: api_client.bulk_add_links(data['links']),
            'bulk_add_prices': lambda: api_client.bulk_add_prices(data['prices'])
        }
        
        if action not in action_map:
            raise ValueError(f"Unknown action: {action}")
        
        return action_map[action]()
    
    def __len__(self) -> int:
        """Zwróć liczbę elementów w kolejce"""
        return len(self.queue)
    
    def __bool__(self) -> bool:
        """Zwróć True jeśli kolejka nie jest pusta"""
        return len(self.queue) > 0

# Singleton instance
offline_queue = OfflineQueue()