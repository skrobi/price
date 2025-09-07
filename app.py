"""
Główna aplikacja Flask - system monitorowania cen
"""
from flask import Flask, render_template
import os

# Import blueprintów
from routes.product_routes import product_bp
from routes.price_routes import price_bp  
from routes.shop_routes import shop_bp
from routes.basket_routes import basket_bp
from routes.product_finder_routes import finder_bp

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Tworzenie folderu data jeśli nie istnieje
if not os.path.exists('data'):
    os.makedirs('data')

# Tworzenie folderów dla modułów
for folder in ['routes', 'utils', 'static/css', 'static/js']:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Rejestracja blueprintów
app.register_blueprint(product_bp)
app.register_blueprint(price_bp)
app.register_blueprint(shop_bp)
app.register_blueprint(basket_bp)
app.register_blueprint(finder_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/links')
def links():
    return render_template('links.html')


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)