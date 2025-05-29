from flask import Flask, request, jsonify, redirect, url_for, send_from_directory
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='static')

# Configuración de la base de datos
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'oscar.jaramillo123',
    'database': 'mercadomasivo',
    'port': 3306,
    'autocommit': True,
    'charset': 'utf8mb4'
}

def get_db_connection():
    """Obtiene una conexión a la base de datos con manejo de errores mejorado"""
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            print("✅ Conexión exitosa a la base de datos")
            return conn
    except Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return None

def test_database_connection():
    """Prueba la conexión a la base de datos y muestra información"""
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            cursor.execute("SELECT DATABASE()")
            database = cursor.fetchone()
            
            print("="*50)
            print("🔗 CONEXIÓN A BASE DE DATOS")
            print("="*50)
            print(f"✅ Estado: CONECTADO")
            print(f"🏠 Host: {db_config['host']}:{db_config['port']}")
            print(f"👤 Usuario: {db_config['user']}")
            print(f"🗂️  Base de datos: {database[0] if database[0] else 'No seleccionada'}")
            print(f"📊 Versión MySQL: {version[0]}")
            
            # Verificar tablas existentes
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"📋 Tablas encontradas: {len(tables)}")
            for table in tables:
                print(f"   - {table[0]}")
            
            cursor.close()
            conn.close()
            print("="*50)
            return True
    except Exception as e:
        print("="*50)
        print("❌ ERROR DE CONEXIÓN")
        print("="*50)
        print(f"Error: {e}")
        print("="*50)
        return False

# Verificar conexión al iniciar
print("Iniciando servidor Flask...")
test_database_connection()

@app.route('/')
def home():
    return redirect(url_for('serve_login'))

@app.route('/login')
def serve_login():
    return send_from_directory('static', 'login.html')

@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory('static', 'index.html')

@app.route('/api/test-connection')
def test_connection():
    """Endpoint para probar la conexión desde el frontend"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM usuario")
            user_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Conexión exitosa',
                'database': db_config['database'],
                'host': db_config['host'],
                'user_count': user_count
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error en consulta: {str(e)}'
            }), 500
    else:
        return jsonify({
            'success': False,
            'message': 'No se pudo conectar a la base de datos'
        }), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Endpoint de login mejorado"""
    try:
        data = request.get_json()
        print(f"📨 Datos de login recibidos: {data}")
        
        if not data or 'usuario' not in data or 'clave' not in data:
            return jsonify({
                'success': False, 
                'message': 'Datos incompletos. Se requiere usuario y contraseña.'
            }), 400

        usuario_input = data['usuario'].strip()
        clave_input = data['clave'].strip()

        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False, 
                'message': 'Error de conexión con la base de datos'
            }), 500

        cursor = conn.cursor(dictionary=True)
        
        # Buscar usuario por cédula o correo (coincidencia exacta)
        query = """
            SELECT idusuario, cedula, nombre, apellido, cargo, correo, clave, foto, telefono
            FROM usuario 
            WHERE cedula = %s OR correo = %s
            LIMIT 1
        """
        cursor.execute(query, (usuario_input, usuario_input))
        user = cursor.fetchone()

        print(f"🔍 Usuario encontrado: {user['nombre'] if user else 'No encontrado'}")

        if user:
            # Verificar contraseña
            if check_password_hash(user['clave'], clave_input):
                print("✅ Login exitoso")
                return jsonify({
                    'success': True,
                    'message': 'Login exitoso',
                    'usuario': {
                        'id': user['idusuario'],
                        'nombre': user['nombre'],
                        'apellido': user['apellido'],
                        'nombre_completo': f"{user['nombre']} {user['apellido']}",
                        'cargo': user['cargo'],
                        'cedula': user['cedula'],
                        'correo': user['correo'],
                        'foto': user['foto'],
                        'telefono': user['telefono']
                    }
                })
            else:
                print("❌ Contraseña incorrecta")
                return jsonify({
                    'success': False, 
                    'message': 'Contraseña incorrecta'
                }), 401
        else:
            print("❌ Usuario no encontrado")
            return jsonify({
                'success': False, 
                'message': 'Usuario no encontrado'
            }), 401

    except Exception as e:
        print(f"❌ Error en login: {e}")
        return jsonify({
            'success': False, 
            'message': 'Error interno del servidor'
        }), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/register_technician', methods=['POST'])
def register_technician():
    """Endpoint para registrar técnicos"""
    try:
        data = request.get_json()
        print(f"📨 Datos de técnico recibidos: {data}")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False, 
                'message': 'Error de conexión con la base de datos'
            }), 500

        cursor = conn.cursor()

        # Verificar si la cédula ya existe
        cursor.execute("SELECT cedula FROM registroTecnico WHERE cedula = %s", (data['cedula'],))
        if cursor.fetchone():
            return jsonify({
                'success': False, 
                'message': 'Ya existe un técnico con esta cédula'
            }), 400

        # Insertar técnico
        query = """
        INSERT INTO registroTecnico (
            cedula, nombre, apellido, ciudad, telefono,
            idAliado, idSupervisor, idCarpeta, idEstado,
            idSegmento, idInterventor
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            data['cedula'], data['nombre'], data['apellido'], 
            data['ciudad'], data['telefono'],
            data['idAliado'], data['idSupervisor'], data['idCarpeta'], 
            data['idEstado'], data['idSegmento'], data['idInterventor']
        ))
        
        conn.commit()
        print("✅ Técnico registrado exitosamente")
        
        return jsonify({
            'success': True, 
            'message': 'Técnico registrado exitosamente'
        })
    
    except Exception as e:
        print(f"❌ Error al registrar técnico: {e}")
        return jsonify({
            'success': False, 
            'message': f'Error al registrar técnico: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/create_user', methods=['POST'])
def create_user():
    """Endpoint para crear usuarios (para pruebas)"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False, 
                'message': 'Error de conexión con la base de datos'
            }), 500

        cursor = conn.cursor()

        # Verificar si el usuario ya existe
        cursor.execute(
            "SELECT cedula FROM usuario WHERE cedula = %s OR correo = %s", 
            (data['cedula'], data['correo'])
        )
        if cursor.fetchone():
            return jsonify({
                'success': False, 
                'message': 'Ya existe un usuario con esta cédula o correo'
            }), 400

        # Hash de la contraseña
        hashed_password = generate_password_hash(data['clave'])

        # Insertar usuario
        query = """
        INSERT INTO usuario (cedula, nombre, apellido, cargo, correo, telefono, clave)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            data['cedula'], data['nombre'], data['apellido'],
            data['cargo'], data['correo'], data['telefono'], hashed_password
        ))
        
        conn.commit()
        print("✅ Usuario creado exitosamente")
        
        return jsonify({
            'success': True, 
            'message': 'Usuario creado exitosamente'
        })
    
    except Exception as e:
        print(f"❌ Error al crear usuario: {e}")
        return jsonify({
            'success': False, 
            'message': f'Error al crear usuario: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


from werkzeug.security import generate_password_hash
print(generate_password_hash('admin123'))

if __name__ == '__main__':
    print("\n🚀 Iniciando servidor Flask en puerto 5000...")
    print("📱 Accede a: http://localhost:5000")
    print("🔗 Login: http://localhost:5000/login")
    print("📊 Dashboard: http://localhost:5000/dashboard")
    print("🧪 Test DB: http://localhost:5000/api/test-connection")
    app.run(debug=True, port=5000, host='0.0.0.0')