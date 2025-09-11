"""
Główna aplikacja Flask - system monitorowania cen z synchronizacją API - NAPRAWIONA Z LOGAMI
"""
from flask import Flask, render_template, request, jsonify, redirect, flash
import os
import logging
import atexit
from datetime import datetime

# Import blueprintów
from routes.product_routes import product_bp
from routes.price_routes import price_bp  
from routes.shop_routes import shop_bp
from routes.basket_routes import basket_bp
from routes.product_finder_routes import finder_bp

# Stwórz katalogi przed konfiguracją logowania
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Konfiguracja synchronizacji
API_BASE_URL = os.getenv('PRICE_TRACKER_API_URL', 'http://serwer327940.lh.pl/price-api')
SYNC_ENABLED = os.getenv('ENABLE_SYNC', 'true').lower() == 'true'

# Globalne zmienne
sync_manager = None
startup_sync_completed = False

logger.info(f"=== APPLICATION STARTUP ===")
logger.info(f"SYNC_ENABLED: {SYNC_ENABLED}")
logger.info(f"API_BASE_URL: {API_BASE_URL}")

def ensure_directories():
    """Upewnij się że wszystkie wymagane foldery istnieją"""
    directories = [
        'data', 'logs', 'routes', 'utils', 'static/css', 'static/js', 'templates'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")

def initialize_sync():
    """Inicjalizuj system synchronizacji - NAPRAWIONA WERSJA Z LOGAMI"""
    global sync_manager
    
    logger.info("=== SYNC INITIALIZATION START ===")
    
    if not SYNC_ENABLED:
        logger.info("Synchronization is disabled by configuration")
        return
    
    try:
        logger.info(f"Initializing sync manager with API: {API_BASE_URL}")
        
        # Import komponentów sync
        logger.info("Importing sync components...")
        from sync.sync_manager import SyncManager
        from sync.sync_integration import patch_data_utils, get_sync_status_for_ui, manual_sync_trigger, set_sync_manager
        logger.info("Sync components imported successfully")
        
        # Utwórz sync manager
        logger.info("Creating SyncManager instance...")
        sync_manager = SyncManager(API_BASE_URL)
        logger.info(f"SyncManager created: {sync_manager}")
        logger.info(f"SyncManager is_online: {getattr(sync_manager, 'is_online', 'UNKNOWN')}")
        
        # Dodaj callback'i dla UI
        logger.info("Adding status callbacks...")
        sync_manager.add_status_callback(on_sync_status_change)
        logger.info("Status callbacks added")
        
        # Patch data_utils functions
        logger.info("Patching data_utils functions...")
        patch_success = patch_data_utils()
        logger.info(f"Patch result: {patch_success}")
        
        if not patch_success:
            logger.error("Failed to patch data_utils functions")
            return
        
        # POPRAWKA: Ustaw sync manager TUTAJ (po stworzeniu i patch'owaniu)
        logger.info("Setting sync manager in integration wrapper...")
        set_sync_manager(sync_manager)
        logger.info("Sync manager set in wrapper successfully")
        
        # Sprawdź czy wrapper ma sync manager
        try:
            from sync.sync_integration import _sync_wrapper
            if _sync_wrapper:
                has_manager = _sync_wrapper.sync_manager is not None
                logger.info(f"Wrapper has sync_manager: {has_manager}")
                if has_manager:
                    logger.info(f"Wrapper sync_manager: {_sync_wrapper.sync_manager}")
                    logger.info(f"Wrapper sync_enabled: {getattr(_sync_wrapper.sync_manager, 'sync_enabled', 'MISSING')}")
            else:
                logger.warning("_sync_wrapper is None")
        except Exception as e:
            logger.error(f"Error checking wrapper status: {e}")
        
        logger.info("Sync manager initialized successfully")
        
        # Test połączenia
        if hasattr(sync_manager, 'is_online') and sync_manager.is_online:
            logger.info("✅ API connection successful")
        else:
            logger.warning("⚠️ API connection failed - working in offline mode")
        
        logger.info("=== SYNC INITIALIZATION COMPLETE ===")
        
    except Exception as e:
        logger.error(f"Failed to initialize sync manager: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sync_manager = None

def on_sync_status_change(status: str, details: dict):
    """Callback wywoływany przy zmianie statusu sync'u"""
    global startup_sync_completed
    
    logger.info(f"SYNC STATUS CHANGE: {status}, details: {details}")
    
    if status == 'syncing':
        sync_type = details.get('type', 'unknown')
        logger.info(f"🔄 Sync started: {sync_type}")
        
    elif status == 'complete':
        sync_type = details.get('type', 'unknown')
        duration = details.get('duration', 0)
        logger.info(f"✅ Sync completed: {sync_type} in {duration:.1f}s")
        
        if sync_type == 'startup':
            startup_sync_completed = True
            logger.info("Startup sync marked as completed")
            
    elif status == 'error':
        error = details.get('error', 'Unknown error')
        logger.error(f"❌ Sync failed: {error}")

def cleanup_on_exit():
    """Funkcja wywoływana przy zamykaniu aplikacji"""
    logger.info("Application shutdown initiated")
    
    if sync_manager:
        try:
            sync_manager.shutdown()
            logger.info("Sync manager shut down successfully")
        except Exception as e:
            logger.error(f"Error during sync manager shutdown: {e}")

# Rejestracja funkcji cleanup
atexit.register(cleanup_on_exit)

# Tworzenie folderów i inicjalizacja
logger.info("Creating directories...")
ensure_directories()

logger.info("Initializing sync...")
initialize_sync()

logger.info("Registering blueprints...")
# Rejestracja blueprintów
app.register_blueprint(product_bp)
app.register_blueprint(price_bp)
app.register_blueprint(shop_bp)
app.register_blueprint(basket_bp)
app.register_blueprint(finder_bp)
logger.info("Blueprints registered")

@app.route('/')
def index():
    """Strona główna z informacjami o sync'u"""
    try:
        from sync.sync_integration import get_sync_status_for_ui
        sync_status = get_sync_status_for_ui() if sync_manager else {
            'status': 'disabled',
            'message': 'Synchronizacja wyłączona',
            'icon': 'offline',
            'color': 'gray'
        }
    except ImportError:
        sync_status = {
            'status': 'disabled',
            'message': 'Synchronizacja niedostępna',
            'icon': 'offline',
            'color': 'gray'
        }
    
    return render_template('index.html', 
                         sync_status=sync_status,
                         sync_enabled=SYNC_ENABLED,
                         api_url=API_BASE_URL if SYNC_ENABLED else None)

@app.route('/links')
def links():
    """Strona z linkami"""
    return render_template('links.html')

# =============================================================================
# API ENDPOINTS dla synchronizacji
# =============================================================================

@app.route('/api/sync/status')
def sync_status_api():
    """API endpoint - status synchronizacji"""
    try:
        if not sync_manager:
            return jsonify({
                'success': False,
                'error': 'Sync manager not initialized'
            })
        
        status = sync_manager.get_sync_status()
        
        try:
            from sync.sync_integration import get_sync_status_for_ui
            ui_status = get_sync_status_for_ui()
        except ImportError:
            ui_status = {'status': 'disabled', 'message': 'Sync integration not available'}
        
        return jsonify({
            'success': True,
            'status': status,
            'ui_status': ui_status,
            'startup_completed': startup_sync_completed
        })
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/sync/trigger', methods=['POST'])
def trigger_manual_sync():
    """API endpoint - wyzwól ręczną synchronizację"""
    try:
        from sync.sync_integration import manual_sync_trigger
        result = manual_sync_trigger()
        return jsonify(result)
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Sync integration not available'
        })
    except Exception as e:
        logger.error(f"Error triggering manual sync: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/sync/queue')
def sync_queue_status():
    """API endpoint - status kolejki offline"""
    try:
        from sync.sync_integration import get_offline_queue_info
        queue_info = get_offline_queue_info()
        
        return jsonify({
            'success': True,
            'queue': queue_info
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Sync integration not available'
        })
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/sync/recovery', methods=['POST'])
def sync_recovery():
    """API endpoint - odzyskiwanie po błędach sync'u"""
    try:
        from sync.sync_integration import recover_from_sync_error
        success = recover_from_sync_error()
        
        return jsonify({
            'success': success,
            'message': 'Recovery completed' if success else 'Recovery failed'
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Sync integration not available'
        })
    except Exception as e:
        logger.error(f"Error in sync recovery: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/sync/reset', methods=['POST'])
def sync_reset():
    """API endpoint - reset stanu sync'u"""
    try:
        from sync.sync_integration import reset_sync_state
        success = reset_sync_state()
        
        return jsonify({
            'success': success,
            'message': 'State reset completed' if success else 'State reset failed'
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Sync integration not available'
        })
    except Exception as e:
        logger.error(f"Error resetting sync state: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

# =============================================================================
# ERROR HANDLERS - UPROSZCZONE (bez templates)
# =============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """Obsługa błędu 404 bez template"""
    return jsonify({
        'error': '404 Not Found',
        'message': 'Strona nie została znaleziona',
        'path': request.path
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Obsługa błędu 500 bez template"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': '500 Internal Server Error',
        'message': 'Błąd wewnętrzny serwera',
        'details': str(error) if app.debug else 'Skontaktuj się z administratorem'
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Obsługa wszystkich innych wyjątków"""
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({
        'error': 'Unexpected Error',
        'message': 'Wystąpił nieoczekiwany błąd',
        'details': str(e) if app.debug else 'Skontaktuj się z administratorem'
    }), 500

# =============================================================================
# CONTEXT PROCESSORS - globalne zmienne dla templates
# =============================================================================

@app.context_processor
def inject_sync_info():
    """Wstrzyknij informacje o sync'u do wszystkich templates"""
    return {
        'sync_enabled': SYNC_ENABLED,
        'sync_manager_available': sync_manager is not None,
        'app_version': '1.0-sync',
        'build_time': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

# =============================================================================
# DEVELOPMENT HELPERS
# =============================================================================

@app.route('/debug/sync')
def debug_sync():
    """Debug endpoint - szczegółowe informacje o sync'u"""
    if not app.debug:
        return jsonify({'error': 'Debug mode disabled'}), 403
    
    debug_info = {
        'sync_manager_initialized': sync_manager is not None,
        'sync_enabled': SYNC_ENABLED,
        'api_url': API_BASE_URL,
        'startup_sync_completed': startup_sync_completed
    }
    
    if sync_manager:
        try:
            debug_info.update({
                'sync_status': sync_manager.get_sync_status(),
                'api_info': sync_manager.get_api_info()
            })
        except Exception as e:
            debug_info['sync_error'] = str(e)
    
    # Dodaj informacje o wrapper'ze
    try:
        from sync.sync_integration import _sync_wrapper, _patched
        debug_info.update({
            'wrapper_exists': _sync_wrapper is not None,
            'wrapper_has_manager': _sync_wrapper.sync_manager is not None if _sync_wrapper else False,
            'functions_patched': _patched
        })
        
        if _sync_wrapper and _sync_wrapper.sync_manager:
            debug_info['wrapper_manager_online'] = getattr(_sync_wrapper.sync_manager, 'is_online', 'UNKNOWN')
    except ImportError:
        debug_info['wrapper_import_error'] = True
    
    return jsonify(debug_info)

@app.route('/debug/test_sync', methods=['POST'])
def debug_test_sync():
    """Debug endpoint - test sync functionality"""
    if not app.debug:
        return jsonify({'error': 'Debug mode disabled'}), 403
    
    if not sync_manager:
        return jsonify({'error': 'Sync manager not available'})
    
    try:
        # Test dodania produktu
        test_product_name = f"Test Product {datetime.now().strftime('%H:%M:%S')}"
        result = sync_manager.add_product_with_sync(test_product_name, "")
        
        return jsonify({
            'success': True,
            'test_result': result,
            'message': f'Test product "{test_product_name}" added'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/debug/patch_status')
def debug_patch_status():
    """Debug endpoint - status patch'owania data_utils"""
    if not app.debug:
        return jsonify({'error': 'Debug mode disabled'}), 403
    
    try:
        from sync.sync_integration import _patched, _original_functions, _sync_wrapper
        
        wrapper_info = {}
        if _sync_wrapper:
            wrapper_info = {
                'sync_enabled': _sync_wrapper.sync_enabled,
                'sync_manager_exists': _sync_wrapper.sync_manager is not None,
                'fallback_to_local': _sync_wrapper.fallback_to_local
            }
            
            if _sync_wrapper.sync_manager:
                wrapper_info['manager_sync_enabled'] = getattr(_sync_wrapper.sync_manager, 'sync_enabled', 'MISSING')
                wrapper_info['manager_is_online'] = getattr(_sync_wrapper.sync_manager, 'is_online', 'MISSING')
        
        return jsonify({
            'patched': _patched,
            'original_functions_available': len(_original_functions),
            'original_functions': list(_original_functions.keys()),
            'wrapper_exists': _sync_wrapper is not None,
            'wrapper_info': wrapper_info
        })
        
    except ImportError:
        return jsonify({
            'error': 'Sync integration not available'
        })

# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test podstawowych funkcji
        from utils.data_utils import load_products
        products = load_products()
        
        health_status = {
            'status': 'OK',
            'timestamp': datetime.now().isoformat(),
            'products_count': len(products),
            'sync_enabled': SYNC_ENABLED,
            'sync_available': sync_manager is not None
        }
        
        if sync_manager:
            try:
                sync_status = sync_manager.get_sync_status()
                health_status['sync_online'] = sync_status.get('is_online', False)
            except Exception:
                health_status['sync_online'] = False
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # Konfiguracja dla development
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    logger.info("=== FLASK APPLICATION STARTUP ===")
    logger.info(f"Starting Flask application in {'DEBUG' if debug_mode else 'PRODUCTION'} mode")
    logger.info(f"Server will run on {host}:{port}")
    logger.info(f"Sync enabled: {SYNC_ENABLED}")
    
    if SYNC_ENABLED:
        logger.info(f"API URL: {API_BASE_URL}")
        
        # POPRAWKA: Usuń podwójne ustawienie - sync manager jest już ustawiony w initialize_sync()
        logger.info("Sync manager already set during initialization")
        
        # Dodatkowa weryfikacja
        try:
            from sync.sync_integration import _sync_wrapper
            if _sync_wrapper and _sync_wrapper.sync_manager:
                logger.info("✅ Sync wrapper has sync manager - ready to go!")
            else:
                logger.warning("⚠️ Sync wrapper missing sync manager")
        except Exception as e:
            logger.error(f"Error checking sync wrapper: {e}")
    
    logger.info("=== STARTING FLASK SERVER ===")
    
    app.run(
        debug=debug_mode,
        host=host,
        port=port,
        threaded=True  # Ważne dla background sync
    )