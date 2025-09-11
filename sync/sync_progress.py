"""
System trackingu postępu synchronizacji z callback'ami dla UI
"""
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional
import threading
import time
import logging

logger = logging.getLogger(__name__)

class SyncProgress:
    """Klasa do monitorowania postępu synchronizacji"""
    
    def __init__(self):
        self.total_steps = 0
        self.completed_steps = 0
        self.current_operation = ""
        self.is_running = False
        self.start_time = None
        self.end_time = None
        self.error = None
        self.details = {}
        
        # Callback'i dla UI
        self.progress_callbacks: List[Callable[[int, str, Dict], None]] = []
        self.completion_callbacks: List[Callable[[bool, Optional[str]], None]] = []
        
        # Thread safety
        self._lock = threading.Lock()
    
    def add_progress_callback(self, callback: Callable[[int, str, Dict], None]):
        """
        Dodaj callback wywoływany przy zmianie postępu
        
        Args:
            callback: Funkcja(progress_percent, operation, details)
        """
        self.progress_callbacks.append(callback)
    
    def add_completion_callback(self, callback: Callable[[bool, Optional[str]], None]):
        """
        Dodaj callback wywoływany po zakończeniu sync'u
        
        Args:
            callback: Funkcja(success, error_message)
        """
        self.completion_callbacks.append(callback)
    
    def start_sync(self, total_steps: int, operation: str = "Initializing..."):
        """Rozpocznij tracking synchronizacji"""
        with self._lock:
            self.total_steps = total_steps
            self.completed_steps = 0
            self.current_operation = operation
            self.is_running = True
            self.start_time = datetime.now()
            self.end_time = None
            self.error = None
            self.details = {
                'sync_type': 'unknown',
                'items_processed': 0,
                'items_failed': 0,
                'items_skipped': 0
            }
        
        logger.info(f"Started sync tracking: {total_steps} steps, operation: {operation}")
        self._notify_progress_callbacks()
    
    def update_progress(self, completed: int, operation: str = None, details: Dict[str, Any] = None):
        """Aktualizuj postęp synchronizacji"""
        with self._lock:
            self.completed_steps = min(completed, self.total_steps)
            if operation:
                self.current_operation = operation
            if details:
                self.details.update(details)
        
        self._notify_progress_callbacks()
        logger.debug(f"Progress updated: {self.get_progress_percent()}% - {self.current_operation}")
    
    def advance_step(self, operation: str = None, details: Dict[str, Any] = None):
        """Zwiększ postęp o jeden krok"""
        with self._lock:
            self.completed_steps = min(self.completed_steps + 1, self.total_steps)
            if operation:
                self.current_operation = operation
            if details:
                self.details.update(details)
        
        self._notify_progress_callbacks()
    
    def complete_sync(self, success: bool = True, error: str = None):
        """Zakończ tracking synchronizacji"""
        with self._lock:
            self.is_running = False
            self.end_time = datetime.now()
            self.error = error
            if success and not error:
                self.completed_steps = self.total_steps
                self.current_operation = "Completed successfully"
            elif error:
                self.current_operation = f"Failed: {error}"
        
        logger.info(f"Sync completed - Success: {success}, Duration: {self.get_duration()}")
        
        # Notify callbacks
        self._notify_progress_callbacks()
        self._notify_completion_callbacks(success, error)
    
    def get_progress_percent(self) -> int:
        """Zwróć postęp w procentach (0-100)"""
        if self.total_steps == 0:
            return 0
        return int((self.completed_steps / self.total_steps) * 100)
    
    def get_duration(self) -> Optional[float]:
        """Zwróć czas trwania sync'u w sekundach"""
        if not self.start_time:
            return None
        
        end_time = self.end_time or datetime.now()
        return (end_time - self.start_time).total_seconds()
    
    def get_eta(self) -> Optional[float]:
        """Oszacuj pozostały czas w sekundach"""
        duration = self.get_duration()
        if not duration or self.completed_steps == 0:
            return None
        
        if self.completed_steps >= self.total_steps:
            return 0
        
        avg_time_per_step = duration / self.completed_steps
        remaining_steps = self.total_steps - self.completed_steps
        return avg_time_per_step * remaining_steps
    
    def get_status_dict(self) -> Dict[str, Any]:
        """Zwróć pełny status jako słownik"""
        with self._lock:
            return {
                'is_running': self.is_running,
                'progress_percent': self.get_progress_percent(),
                'completed_steps': self.completed_steps,
                'total_steps': self.total_steps,
                'current_operation': self.current_operation,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'duration': self.get_duration(),
                'eta': self.get_eta(),
                'error': self.error,
                'details': self.details.copy()
            }
    
    def _notify_progress_callbacks(self):
        """Wywołaj wszystkie callback'i postępu"""
        status = self.get_status_dict()
        for callback in self.progress_callbacks:
            try:
                callback(status['progress_percent'], self.current_operation, status)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def _notify_completion_callbacks(self, success: bool, error: Optional[str]):
        """Wywołaj wszystkie callback'i zakończenia"""
        for callback in self.completion_callbacks:
            try:
                callback(success, error)
            except Exception as e:
                logger.error(f"Error in completion callback: {e}")

class BatchProgress:
    """Klasa do trackingu postępu operacji batch'owych"""
    
    def __init__(self, batch_name: str, total_items: int):
        self.batch_name = batch_name
        self.total_items = total_items
        self.processed_items = 0
        self.failed_items = 0
        self.skipped_items = 0
        self.start_time = datetime.now()
        self.errors: List[Dict[str, Any]] = []
    
    def process_item(self, success: bool = True, error: str = None, item_id: Any = None):
        """Oznacz element jako przetworzony"""
        if success:
            self.processed_items += 1
        else:
            self.failed_items += 1
            if error:
                self.errors.append({
                    'item_id': item_id,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                })
    
    def skip_item(self, reason: str = None, item_id: Any = None):
        """Oznacz element jako pominięty"""
        self.skipped_items += 1
        if reason:
            self.errors.append({
                'item_id': item_id,
                'error': f"Skipped: {reason}",
                'timestamp': datetime.now().isoformat()
            })
    
    def get_progress_percent(self) -> int:
        """Zwróć postęp w procentach"""
        total_processed = self.processed_items + self.failed_items + self.skipped_items
        if self.total_items == 0:
            return 100
        return int((total_processed / self.total_items) * 100)
    
    def get_summary(self) -> Dict[str, Any]:
        """Zwróć podsumowanie batch'a"""
        duration = (datetime.now() - self.start_time).total_seconds()
        total_processed = self.processed_items + self.failed_items + self.skipped_items
        
        return {
            'batch_name': self.batch_name,
            'total_items': self.total_items,
            'processed_items': self.processed_items,
            'failed_items': self.failed_items,
            'skipped_items': self.skipped_items,
            'remaining_items': self.total_items - total_processed,
            'progress_percent': self.get_progress_percent(),
            'duration_seconds': duration,
            'items_per_second': total_processed / duration if duration > 0 else 0,
            'error_count': len(self.errors),
            'success_rate': (self.processed_items / total_processed * 100) if total_processed > 0 else 0
        }
    
    def is_complete(self) -> bool:
        """Sprawdź czy batch jest ukończony"""
        total_processed = self.processed_items + self.failed_items + self.skipped_items
        return total_processed >= self.total_items

class SyncProgressManager:
    """Manager do obsługi wielu równoczesnych operacji sync'u"""
    
    def __init__(self):
        self.active_syncs: Dict[str, SyncProgress] = {}
        self.active_batches: Dict[str, BatchProgress] = {}
        self._lock = threading.Lock()
    
    def create_sync(self, sync_id: str, total_steps: int, operation: str = "Starting...") -> SyncProgress:
        """Utwórz nowy sync progress"""
        with self._lock:
            sync_progress = SyncProgress()
            sync_progress.start_sync(total_steps, operation)
            self.active_syncs[sync_id] = sync_progress
            return sync_progress
    
    def get_sync(self, sync_id: str) -> Optional[SyncProgress]:
        """Pobierz sync progress po ID"""
        return self.active_syncs.get(sync_id)
    
    def complete_sync(self, sync_id: str, success: bool = True, error: str = None):
        """Zakończ sync i usuń z aktywnych"""
        with self._lock:
            if sync_id in self.active_syncs:
                sync_progress = self.active_syncs[sync_id]
                sync_progress.complete_sync(success, error)
                # Usuń po 5 minutach (żeby UI mogło jeszcze pokazać wynik)
                threading.Timer(300, lambda: self.active_syncs.pop(sync_id, None)).start()
    
    def create_batch(self, batch_id: str, batch_name: str, total_items: int) -> BatchProgress:
        """Utwórz nowy batch progress"""
        with self._lock:
            batch_progress = BatchProgress(batch_name, total_items)
            self.active_batches[batch_id] = batch_progress
            return batch_progress
    
    def get_batch(self, batch_id: str) -> Optional[BatchProgress]:
        """Pobierz batch progress po ID"""
        return self.active_batches.get(batch_id)
    
    def complete_batch(self, batch_id: str):
        """Zakończ batch i usuń z aktywnych"""
        with self._lock:
            if batch_id in self.active_batches:
                # Usuń po 5 minutach
                threading.Timer(300, lambda: self.active_batches.pop(batch_id, None)).start()
    
    def get_all_active(self) -> Dict[str, Any]:
        """Pobierz status wszystkich aktywnych operacji"""
        with self._lock:
            return {
                'syncs': {sid: sync.get_status_dict() for sid, sync in self.active_syncs.items()},
                'batches': {bid: batch.get_summary() for bid, batch in self.active_batches.items()}
            }
    
    def cleanup_completed(self):
        """Wyczyść ukończone operacje starsze niż 5 minut"""
        current_time = datetime.now()
        cutoff_time = 300  # 5 minut
        
        with self._lock:
            # Wyczyść ukończone sync'i
            completed_syncs = []
            for sync_id, sync_progress in self.active_syncs.items():
                if (not sync_progress.is_running and 
                    sync_progress.end_time and 
                    (current_time - sync_progress.end_time).total_seconds() > cutoff_time):
                    completed_syncs.append(sync_id)
            
            for sync_id in completed_syncs:
                self.active_syncs.pop(sync_id, None)
            
            # Wyczyść ukończone batche
            completed_batches = []
            for batch_id, batch_progress in self.active_batches.items():
                if (batch_progress.is_complete() and 
                    (current_time - batch_progress.start_time).total_seconds() > cutoff_time):
                    completed_batches.append(batch_id)
            
            for batch_id in completed_batches:
                self.active_batches.pop(batch_id, None)

# Singleton instances
sync_progress_manager = SyncProgressManager()

def create_console_progress_callback(prefix: str = "Sync"):
    """Factory function dla callback'a wyświetlającego postęp w konsoli"""
    def console_callback(progress_percent: int, operation: str, details: Dict[str, Any]):
        print(f"\r{prefix}: {progress_percent:3d}% - {operation}", end="", flush=True)
        if progress_percent >= 100:
            print()  # Nowa linia po zakończeniu
    return console_callback

def create_file_progress_callback(log_file: str):
    """Factory function dla callback'a logującego postęp do pliku"""
    def file_callback(progress_percent: int, operation: str, details: Dict[str, Any]):
        timestamp = datetime.now().isoformat()
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {progress_percent:3d}% - {operation}\n")
    return file_callback