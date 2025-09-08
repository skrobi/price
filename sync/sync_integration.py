"""
Moduł integracji synchronizacji z istniejącym kodem aplikacji
Zapewnia minimalne zmiany w obecnej strukturze
"""
import os
import json
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# Import oryginalnych funkcji
import utils.data_utils as original_data_utils
from .sync_manager import sync_manager

logger = logging.getLogger(__name__)

class SyncWrapper:
    """
    Wrapper class który zastępuje oryginalne funkcje data_utils
    zachowując pełną kompatybilność wsteczną
    """
    
    def __init__(self):
        self.sync_enabled = True
        self.fallback_to_local = True
    
    def _should_sync(self) -> bool:
        """Sprawdź czy można i należy używać sync'u"""
        return (self.sync_enabled and 
                sync_manager is not None and 
                sync_manager.sync_enabled)
    
    def _log_sync_action(self, action: str, success: bool, details: str = ""):
        """Loguj akcje synchronizacji"""
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"SYNC {status}: {action} - {details}")
    
    # ==========================================================================
    # PRODUCTS
    # ==========================================================================
    
    def load_products(self) -> List[Dict[str, Any]]:
        """
        Załaduj produkty z sync'iem startup'owym jeśli potrzeba
        
        Zachowuje pełną kompatybilność z oryginalną funkcją
        """
        try:
            # Sprawdź czy potrzeba sync'u startowego
            if self._should_sync() and self._should_startup_sync():
                logger.info("Performing startup sync before loading products")
                sync_result = sync_manager.startup_sync()
                self._log_sync_action("startup_sync", sync_result['success'], 
                                    f"Duration: {sync_result.get('duration', 0):.1f}s")
            
            # Załaduj dane używając oryginalnej funkcji
            products = original_data_utils.load_products()
            
            # Dodaj informacje o sync'u jeśli dostępne
            if self._should_sync():
                for product in products:
                    product['_sync_status'] = 'synced' if sync_manager.is_online else 'local_only'
            
            return products
            
        except Exception as e:
            logger.error(f"Error in load_products with sync: {e}")
            # Fallback do oryginalnej funkcji
            return original_data_utils.load_products()
    
    def save_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Zapisz produkt z natychmiastowym sync'iem
        
        Args:
            product_data: Dane produktu (format oryginalny)
        
        Returns:
            Dict z wynikiem operacji i informacjami o sync'u
        """
        try:
            if self._should_sync():
                # Użyj sync manager dla natychmiastowego sync'u
                result = sync_manager.add_product_with_sync(
                    product_data['name'], 
                    product_data.get('ean', '')
                )
                
                self._log_sync_action("add_product", result['success'], 
                                    f"Name: {product_data['name']}, Synced: {result.get('synced', False)}")
                
                return result
            else:
                # Fallback do oryginalnej funkcji
                original_data_utils.save_product(product_data)
                return {
                    'success': True,
                    'product_id': product_data.get('id'),
                    'name': product_data['name'],
                    'synced': False,
                    'fallback': True
                }
                
        except Exception as e:
            logger.error(f"Error in save_product with sync: {e}")
            
            if self.fallback_to_local:
                # Fallback - zapisz lokalnie
                original_data_utils.save_product(product_data)
                return {
                    'success': True,
                    'product_id': product_data.get('id'),
                    'error': str(e),
                    'fallback': True
                }
            else:
                return {'success': False, 'error': str(e)}
    
    def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Aktualizuj produkt (kompatybilność z istniejącym kodem)"""
        try:
            # Dla aktualizacji używamy oryginalnej funkcji + dodajemy do queue
            original_data_utils.update_product(product_data)
            
            if self._should_sync():
                # Dodaj do offline queue jako backup
                from offline_queue import offline_queue
                offline_queue.add_to_queue('update_product', product_data, priority=2)
            
            return {'success': True, 'updated': True}
            
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==========================================================================
    # LINKS
    # ==========================================================================
    
    def load_links(self) -> List[Dict[str, Any]]:
        """Załaduj linki (kompatybilność z oryginalną funkcją)"""
        try:
            links = original_data_utils.load_links()
            
            # Dodaj informacje o sync'u
            if self._should_sync():
                for link in links:
                    link['_sync_status'] = 'synced' if sync_manager.is_online else 'local_only'
            
            return links
            
        except Exception as e:
            logger.error(f"Error in load_links: {e}")
            return original_data_utils.load_links()
    
    def save_link(self, link_data: Dict[str, Any]) -> Dict[str, Any]:
        """Zapisz link z sync'iem"""
        try:
            if self._should_sync():
                # Użyj sync manager
                result = sync_manager.add_link_with_sync(
                    link_data['product_id'],
                    link_data['shop_id'],
                    link_data['url']
                )
                
                self._log_sync_action("add_link", result['success'], 
                                    f"Product: {link_data['product_id']}, Shop: {link_data['shop_id']}")
                
                return result
            else:
                # Fallback
                original_data_utils.save_link(link_data)
                return {'success': True, 'synced': False, 'fallback': True}
                
        except Exception as e:
            logger.error(f"Error in save_link with sync: {e}")
            
            if self.fallback_to_local:
                original_data_utils.save_link(link_data)
                return {'success': True, 'error': str(e), 'fallback': True}
            else:
                return {'success': False, 'error': str(e)}
    
    # ==========================================================================
    # PRICES
    # ==========================================================================
    
    def load_prices(self) -> List[Dict[str, Any]]:
        """Załaduj ceny (kompatybilność z oryginalną funkcją)"""
        return original_data_utils.load_prices()
    
    def save_price(self, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """Zapisz cenę z sync'iem"""
        try:
            if self._should_sync():
                # Użyj sync manager
                result = sync_manager.add_price_with_sync(
                    price_data['product_id'],
                    price_data['shop_id'],
                    price_data['price'],
                    price_data.get('currency', 'PLN'),
                    price_data.get('price_type', 'manual'),
                    price_data.get('url', ''),
                    price_data.get('source', 'user_input')
                )
                
                self._log_sync_action("add_price", result['success'], 
                                    f"Product: {price_data['product_id']}, Price: {price_data['price']}")
                
                return result
            else:
                # Fallback
                original_data_utils.save_price(price_data)
                return {'success': True, 'synced': False, 'fallback': True}
                
        except Exception as e:
            logger.error(f"Error in save_price with sync: {e}")
            
            if self.fallback_to_local:
                original_data_utils.save_price(price_data)
                return {'success': True, 'error': str(e), 'fallback': True}
            else:
                return {'success': False, 'error': str(e)}
    
    def get_latest_prices(self, include_url_in_key: bool = False) -> Dict[str, Any]:
        """Pobierz najnowsze ceny (kompatybilność z oryginalną funkcją)"""
        return original_data_utils.get_latest_prices(include_url_in_key)
    
    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================
    
    def _should_startup_sync(self) -> bool:
        """Sprawdź czy potrzeba sync'u startowego"""
        if not sync_manager:
            return False
        
        # Jeśli nigdy nie było sync'u
        if not sync_manager.last_successful_sync:
            return True
        
        # Jeśli ostatni sync był dawno temu (>1 godzina)
        time_since_sync = datetime.now() - sync_manager.last_successful_sync
        return time_since_sync.total_seconds() > 3600
    
    def get_sync_info(self) -> Dict[str, Any]:
        """Pobierz informacje o statusie synchronizacji"""
        if not sync_manager:
            return {
                'enabled': False,
                'status': 'disabled',
                'message': 'Sync manager not initialized'
            }
        
        status = sync_manager.get_sync_status()
        return {
            'enabled': status['sync_enabled'],
            'online': status['is_online'],
            'in_progress': status['sync_in_progress'],
            'last_sync': status['last_successful_sync'],
            'user_id': status['user_id'],
            'queue_size': status['offline_queue_size']
        }
    
    def force_sync(self) -> Dict[str, Any]:
        """Wymuś synchronizację (API dla UI)"""
        if not self._should_sync():
            return {'success': False, 'error': 'Sync not available'}
        
        try:
            result = sync_manager.force_sync_now()
            self._log_sync_action("force_sync", result['success'], 
                                f"Duration: {result.get('duration', 0):.1f}s")
            return result
        except Exception as e:
            logger.error(f"Force sync failed: {e}")
            return {'success': False, 'error': str(e)}

# =============================================================================
# MONKEY PATCHING - zastąp oryginalne funkcje
# =============================================================================

# Utwórz singleton wrapper
_sync_wrapper = SyncWrapper()

# Zastąp funkcje w module data_utils
def patch_data_utils():
    """Zastąp oryginalne funkcje data_utils funkcjami z sync'iem"""
    
    # Zapisz oryginalne funkcje jako backup
    original_data_utils._original_load_products = original_data_utils.load_products
    original_data_utils._original_save_product = original_data_utils.save_product
    original_data_utils._original_load_links = original_data_utils.load_links
    original_data_utils._original_save_link = original_data_utils.save_link
    original_data_utils._original_load_prices = original_data_utils.load_prices
    original_data_utils._original_save_price = original_data_utils.save_price
    
    # Zastąp funkcjami z sync'iem
    original_data_utils.load_products = _sync_wrapper.load_products
    original_data_utils.save_product = _sync_wrapper.save_product
    original_data_utils.load_links = _sync_wrapper.load_links
    original_data_utils.save_link = _sync_wrapper.save_link
    original_data_utils.load_prices = _sync_wrapper.load_prices
    original_data_utils.save_price = _sync_wrapper.save_price
    
    logger.info("Patched data_utils functions with sync support")

def unpatch_data_utils():
    """Przywróć oryginalne funkcje data_utils"""
    if hasattr(original_data_utils, '_original_load_products'):
        original_data_utils.load_products = original_data_utils._original_load_products
        original_data_utils.save_product = original_data_utils._original_save_product
        original_data_utils.load_links = original_data_utils._original_load_links
        original_data_utils.save_link = original_data_utils._original_save_link
        original_data_utils.load_prices = original_data_utils._original_load_prices
        original_data_utils.save_price = original_data_utils._original_save_price
        
        logger.info("Restored original data_utils functions")

# =============================================================================
# CONTEXT MANAGER dla tymczasowego wyłączenia sync'u
# =============================================================================

class NoSync:
    """Context manager do tymczasowego wyłączenia sync'u"""
    
    def __init__(self):
        self.original_sync_enabled = None
    
    def __enter__(self):
        self.original_sync_enabled = _sync_wrapper.sync_enabled
        _sync_wrapper.sync_enabled = False
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        _sync_wrapper.sync_enabled = self.original_sync_enabled

# =============================================================================
# DECORATOR dla funkcji wymagających sync'u
# =============================================================================

def with_sync(fallback_on_error=True):
    """
    Decorator dla funkcji które powinny używać sync'u
    
    Args:
        fallback_on_error: Czy użyć lokalnych danych w przypadku błędu sync'u
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Sprawdź czy sync jest dostępny
                if _sync_wrapper._should_sync():
                    return func(*args, **kwargs)
                elif fallback_on_error:
                    logger.warning(f"Sync not available for {func.__name__}, using fallback")
                    return func(*args, **kwargs)
                else:
                    raise Exception("Sync required but not available")
            except Exception as e:
                if fallback_on_error:
                    logger.error(f"Error in {func.__name__} with sync: {e}, using fallback")
                    return func(*args, **kwargs)
                else:
                    raise
        return wrapper
    return decorator

# =============================================================================
# HELPER FUNCTIONS dla istniejącego kodu
# =============================================================================

def ensure_sync_ready():
    """Upewnij się że sync jest gotowy do użycia"""
    if not sync_manager:
        logger.warning("Sync manager not initialized")
        return False
    
    if not sync_manager.sync_enabled:
        logger.warning("Sync is disabled")
        return False
    
    return True

def get_sync_status_for_ui() -> Dict[str, Any]:
    """Pobierz status sync'u w formacie przyjaznym dla UI"""
    sync_info = _sync_wrapper.get_sync_info()
    
    if not sync_info['enabled']:
        return {
            'status': 'disabled',
            'message': 'Synchronizacja wyłączona',
            'icon': 'offline',
            'color': 'gray'
        }
    
    if sync_info['in_progress']:
        return {
            'status': 'syncing',
            'message': 'Synchronizacja w toku...',
            'icon': 'syncing',
            'color': 'blue'
        }
    
    if sync_info['online']:
        last_sync = sync_info['last_sync']
        if last_sync:
            # Sprawdź jak dawno był ostatni sync
            last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            time_since = datetime.now() - last_sync_dt.replace(tzinfo=None)
            
            if time_since.total_seconds() < 3600:  # < 1 godzina
                return {
                    'status': 'synced',
                    'message': f'Zsynchronizowano {int(time_since.total_seconds() // 60)} min temu',
                    'icon': 'check',
                    'color': 'green'
                }
            else:
                return {
                    'status': 'stale',
                    'message': 'Synchronizacja nieaktualna',
                    'icon': 'warning',
                    'color': 'yellow'
                }
        else:
            return {
                'status': 'never_synced',
                'message': 'Nigdy nie synchronizowano',
                'icon': 'warning',
                'color': 'orange'
            }
    else:
        queue_size = sync_info.get('queue_size', 0)
        if queue_size > 0:
            return {
                'status': 'offline_with_queue',
                'message': f'Offline ({queue_size} w kolejce)',
                'icon': 'offline',
                'color': 'red'
            }
        else:
            return {
                'status': 'offline',
                'message': 'Brak połączenia z API',
                'icon': 'offline',
                'color': 'red'
            }

def manual_sync_trigger() -> Dict[str, Any]:
    """Wyzwól ręczną synchronizację (dla przycisków w UI)"""
    return _sync_wrapper.force_sync()

def get_offline_queue_info() -> Dict[str, Any]:
    """Pobierz informacje o kolejce offline"""
    from offline_queue import offline_queue
    return offline_queue.get_queue_stats()

# =============================================================================
# COMPATIBILITY FUNCTIONS - dla łatwiejszej migracji
# =============================================================================

# Te funkcje można importować w miejscu oryginalnych
def load_products_sync():
    """Explicit sync version of load_products"""
    return _sync_wrapper.load_products()

def save_product_sync(product_data):
    """Explicit sync version of save_product"""
    return _sync_wrapper.save_product(product_data)

def load_links_sync():
    """Explicit sync version of load_links"""
    return _sync_wrapper.load_links()

def save_link_sync(link_data):
    """Explicit sync version of save_link"""
    return _sync_wrapper.save_link(link_data)

def save_price_sync(price_data):
    """Explicit sync version of save_price"""
    return _sync_wrapper.save_price(price_data)

# =============================================================================
# MIGRATION HELPERS - dla stopniowego przechodzenia na sync
# =============================================================================

def migrate_to_sync_gradually():
    """
    Stopniowo migruj do sync'u - patch tylko niektóre funkcje
    Użyteczne dla testowania sync'u bez pełnej migracji
    """
    # Patch tylko save functions (dodawanie nowych danych)
    original_data_utils.save_product = _sync_wrapper.save_product
    original_data_utils.save_link = _sync_wrapper.save_link  
    original_data_utils.save_price = _sync_wrapper.save_price
    
    logger.info("Partially patched data_utils - only save functions use sync")

def enable_sync_for_module(module_name: str):
    """
    Włącz sync tylko dla określonego modułu
    Pozwala na kontrolowane testowanie sync'u
    """
    # To może być rozszerzone do bardziej granularnej kontroli
    logger.info(f"Enabled sync for module: {module_name}")

# =============================================================================
# ERROR RECOVERY - obsługa błędów sync'u
# =============================================================================

def recover_from_sync_error():
    """Odzyskaj po błędzie sync'u"""
    try:
        if sync_manager:
            # Sprawdź połączenie
            sync_manager._check_api_connection()
            
            # Przetwórz offline queue jeśli online
            if sync_manager.is_online:
                from offline_queue import offline_queue
                result = offline_queue.process_queue_with_api(sync_manager.api_client)
                logger.info(f"Processed offline queue: {result}")
            
            return True
    except Exception as e:
        logger.error(f"Error in sync recovery: {e}")
        return False

def reset_sync_state():
    """Zresetuj stan sync'u (w przypadku problemów)"""
    try:
        if sync_manager:
            sync_manager.sync_in_progress = False
            sync_manager.last_sync_attempt = None
            
        from offline_queue import offline_queue
        offline_queue.clear_failed_items()
        
        logger.info("Reset sync state")
        return True
    except Exception as e:
        logger.error(f"Error resetting sync state: {e}")
        return False

# =============================================================================
# EXPORTY dla łatwego importu
# =============================================================================

__all__ = [
    # Main wrapper
    'patch_data_utils',
    'unpatch_data_utils',
    
    # Context managers and decorators
    'NoSync',
    'with_sync',
    
    # Helper functions
    'ensure_sync_ready',
    'get_sync_status_for_ui',
    'manual_sync_trigger',
    'get_offline_queue_info',
    
    # Explicit sync functions
    'load_products_sync',
    'save_product_sync',
    'load_links_sync', 
    'save_link_sync',
    'save_price_sync',
    
    # Migration helpers
    'migrate_to_sync_gradually',
    'enable_sync_for_module',
    
    # Error recovery
    'recover_from_sync_error',
    'reset_sync_state'
]