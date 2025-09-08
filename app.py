"""
Główna aplikacja Flask - system monitorowania cen z synchronizacją API - POPRAWIONA
"""
from flask import Flask, render_template, request, jsonify
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

# Import sync components
from sync.sync_manager import SyncManager
from sync.sync_integration import patch_data_utils, get_sync_status_for_ui, manual_sync_trigger

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
API_BASE_URL = os.getenv('PRICE_TRACKER_API_URL', 'http://localhost/price-api')
SYNC_ENABLED = os.getenv('ENABLE_SYNC', 'true').lower() == 'true'

# Globalne zmienne
sync_manager = None
startup_sync_completed = False

def ensure_directories():
    """Upewnij się że wszystkie wymagane foldery istnieją"""
    directories = [
        'data', 'logs', 'routes', 'utils', 'static/css', 'static/js'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")

def initialize_sync():
    """Inicjalizuj system synchronizacji"""
    global sync_manager
    
    if not SYNC_ENABLED:
        logger.info("Synchronization is disabled by configuration")
        return
    
    try:
        logger.info(f"Initializing sync manager with API: {API_BASE_URL}")
        
        # Utwórz sync manager
        sync_manager = SyncManager(API_BASE_URL)
        
        # Dodaj callback'i dla UI
        sync_manager.add_status_callback(on_sync_status_change)
        
        # Patch data_utils functions
        patch_data_utils()
        
        logger.info("Sync manager initialized successfully")
        
        # Test połączenia
        if sync_manager.is_online:
            logger.info("✅ API connection successful")
        else:
            logger.warning("⚠️ API connection failed - working in offline mode")
        
    except Exception as e:
        logger.error(f"Failed to initialize sync manager: {e}")
        sync_manager = None

def on_sync_status_change(status: str, details: dict):
    """Callback wywoływany przy zmianie statusu sync'u"""
    global startup_sync_completed
    
    if status == 'syncing':
        sync_type = details.get('type', 'unknown')
        logger.info(f"🔄 Sync started: {sync_type}")
        
    elif status == 'complete':
        sync_type = details.get('type', 'unknown')
        duration = details.get('duration', 0)
        logger.info(f"✅ Sync completed: {sync_type} in {duration:.1f}s")
        
        if sync_type == 'startup':
            startup_sync_completed = True
            
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
ensure_directories()
initialize_sync()

# Rejestracja blueprintów
app.register_blueprint(product_bp)
app.register_blueprint(price_bp)
app.register_blueprint(shop_bp)
app.register_blueprint(basket_bp)
app.register_blueprint(finder_bp)

@app.route('/')
def index():
    """Strona główna z informacjami o sync'u"""
    sync_status = get_sync_status_for_ui() if sync_manager else {
        'status': 'disabled',
        'message': 'Synchronizacja wyłączona',
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
        ui_status = get_sync_status_for_ui()
        
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
        result = manual_sync_trigger()
        return jsonify(result)
        
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
        
    except Exception as e:
        logger.error(f"Error resetting sync state: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return render_template('error.html', error=str(e)), 500

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
        return "Debug mode disabled", 403
    
    debug_info = {
        'sync_manager_initialized': sync_manager is not None,
        'sync_enabled': SYNC_ENABLED,
        'api_url': API_BASE_URL,
        'startup_sync_completed': startup_sync_completed
    }
    
    if sync_manager:
        debug_info.update({
            'sync_status': sync_manager.get_sync_status(),
            'api_info': sync_manager.get_api_info()
        })
    
    return jsonify(debug_info)

@app.route('/debug/test_sync', methods=['POST'])
def debug_test_sync():
    """Debug endpoint - test sync functionality"""
    if not app.debug:
        return "Debug mode disabled", 403
    
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

if __name__ == '__main__':
    # Konfiguracja dla development
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    logger.info(f"Starting Flask application in {'DEBUG' if debug_mode else 'PRODUCTION'} mode")
    logger.info(f"Server will run on {host}:{port}")
    logger.info(f"Sync enabled: {SYNC_ENABLED}")
    
    if SYNC_ENABLED:
        logger.info(f"API URL: {API_BASE_URL}")
    
    app.run(
        debug=debug_mode,
        host=host,
        port=port,
        threaded=True  # Ważne dla background sync
    )