from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
from werkzeug.security import check_password_hash
from flask import send_from_directory
from werkzeug.security import generate_password_hash



app = Flask(__name__)

# Configuración de la base de datos
db_config = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': '',  # Agrega tu contraseña si es necesaria
    'database': 'mercadoMasivo'
}

print(generate_password_hash('tu_contraseña'))

@app.route('/')
def serve_login():
    return send_from_directory('static', 'login.html')

@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory('static', 'index.html')

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    print("Datos recibidos:", data)  # Debug
    
    if not data or 'usuario' not in data or 'clave' not in data:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Error de conexión con la base de datos'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Usuario WHERE cedula = %s", (data['usuario'],))
        user = cursor.fetchone()
        print("Usuario encontrado:", user)  # Debug

        if user:
            # Si la contraseña está hasheada:
            if check_password_hash(user['clave'], data['clave']):
                return jsonify({
                    'success': True,
                    'nombre': f"{user['nombre']} {user['apellido']}",
                    'cargo': user['cargo']
                })
            # Si la contraseña está en texto plano (solo para desarrollo):
            elif user['clave'] == data['clave']:
                print("¡Advertencia! Contraseña en texto plano")  # Debug
                return jsonify({
                    'success': True,
                    'nombre': f"{user['nombre']} {user['apellido']}",
                    'cargo': user['cargo']
                })
        
        return jsonify({'success': False, 'message': 'Credenciales incorrectas'}), 401
    except Error as e:
        print(f"Error en la base de datos: {e}")  # Debug
        return jsonify({'success': False, 'message': 'Error en el servidor'}), 500
    finally:
        if conn.is_connected():
            conn.close()

@app.route('/dashboard')
def dashboard():
    return app.send_static_file('Index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)