from flask import Flask, jsonify, request, g
import psycopg2
import psycopg2.extras
import os
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('app_request_count', 'Application Request Count',
                       ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'Application Request Latency',
                          ['method', 'endpoint'])

# Database connection
def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'postgres'),
            database=os.environ.get('DB_NAME', 'appdb'),
            user=os.environ.get('DB_USER', 'app_user'),
            password=os.environ.get('DB_PASSWORD', 'secure_password')
        )
        g.db.autocommit = True
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Middleware for metrics
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    request_latency = time.time() - request.start_time
    REQUEST_LATENCY.labels(request.method, request.path).observe(request_latency)
    REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    return response

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/health')
def health():
    try:
        # Check database connection
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({'status': 'unhealthy', 'database': 'disconnected', 'error': str(e)}), 500

@app.route('/items', methods=['GET'])
def get_all_items():
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('''
            SELECT i.id, i.name, i.description, i.price, 
                   u.username as owner, c.name as category
            FROM items i
            JOIN users u ON i.user_id = u.id
            LEFT JOIN categories c ON i.category_id = c.id
        ''')
        items = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        return jsonify(items), 200
    except Exception as e:
        app.logger.error(f"Error fetching items: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('''
            SELECT i.id, i.name, i.description, i.price, 
                   u.username as owner, c.name as category
            FROM items i
            JOIN users u ON i.user_id = u.id
            LEFT JOIN categories c ON i.category_id = c.id
            WHERE i.id = %s
        ''', (item_id,))
        item = cursor.fetchone()
        cursor.close()
        
        if item:
            return jsonify(dict(item)), 200
        else:
            return jsonify({'error': 'Item not found'}), 404
    except Exception as e:
        app.logger.error(f"Error fetching item {item_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/items', methods=['POST'])
def create_item():
    data = request.json
    required_fields = ['name', 'price', 'user_id']
    
    # Validate request data
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('''
            INSERT INTO items (name, description, price, user_id, category_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        ''', (
            data['name'],
            data.get('description', ''),
            data['price'],
            data['user_id'],
            data.get('category_id')
        ))
        item_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        
        return jsonify({'id': item_id, 'message': 'Item created successfully'}), 201
    except Exception as e:
        app.logger.error(f"Error creating item: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if item exists
        cursor.execute('SELECT id FROM items WHERE id = %s', (item_id,))
        if cursor.fetchone() is None:
            cursor.close()
            return jsonify({'error': 'Item not found'}), 404
        
        # Build the update query dynamically based on provided fields
        update_fields = []
        params = []
        
        if 'name' in data:
            update_fields.append('name = %s')
            params.append(data['name'])
        
        if 'description' in data:
            update_fields.append('description = %s')
            params.append(data['description'])
        
        if 'price' in data:
            update_fields.append('price = %s')
            params.append(data['price'])
        
        if 'category_id' in data:
            update_fields.append('category_id = %s')
            params.append(data['category_id'])
        
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        
        # Execute update if there are fields to update
        if update_fields:
            query = f"UPDATE items SET {', '.join(update_fields)} WHERE id = %s"
            params.append(item_id)
            cursor.execute(query, tuple(params))
            conn.commit()
        
        cursor.close()
        return jsonify({'message': 'Item updated successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error updating item {item_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if item exists
        cursor.execute('SELECT id FROM items WHERE id = %s', (item_id,))
        if cursor.fetchone() is None:
            cursor.close()
            return jsonify({'error': 'Item not found'}), 404
        
        # Delete the item
        cursor.execute('DELETE FROM items WHERE id = %s', (item_id,))
        conn.commit()
        cursor.close()
        
        return jsonify({'message': 'Item deleted successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error deleting item {item_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)