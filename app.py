from flask import Flask, request, jsonify, redirect, url_for, send_from_directory
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='static')
app.config['SESSION_COOKIE_DOMAIN'] = None

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
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            return conn
    except Error:
        return None

def test_database_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            cursor.execute("SELECT DATABASE()")
            cursor.execute("SHOW TABLES")
            cursor.close()
            conn.close()
            return True
    except Exception:
        return False

# Verificar conexión al iniciar
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
    try:
        data = request.get_json()
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
        query = """
            SELECT idusuario, cedula, nombre, apellido, cargo, correo, clave, foto, telefono
            FROM usuario 
            WHERE cedula = %s OR correo = %s
            LIMIT 1
        """
        cursor.execute(query, (usuario_input, usuario_input))
        user = cursor.fetchone()

        # Unifica el mensaje para usuario o contraseña incorrectos
        if user and check_password_hash(user['clave'], clave_input):
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
            return jsonify({
                'success': False, 
                'message': 'Correo o contraseña incorrectas'
            }), 401

    except Exception:
        return jsonify({
            'success': False, 
            'message': 'Correo o contraseña incorrectas'
        }), 401
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/register_technician', methods=['POST'])
def register_technician():
    try:
        data = request.get_json()
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False, 
                'message': 'Error de conexión con la base de datos'
            }), 500

        cursor = conn.cursor()
        cursor.execute("SELECT cedula FROM registroTecnico WHERE cedula = %s", (data['cedula'],))
        if cursor.fetchone():
            return jsonify({
                'success': False, 
                'message': 'Ya existe un técnico con esta cédula'
            }), 400

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
        return jsonify({
            'success': True, 
            'message': 'Técnico registrado exitosamente'
        })
    
    except Exception as e:
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
    try:
        data = request.get_json()
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False, 
                'message': 'Error de conexión con la base de datos'
            }), 500

        cursor = conn.cursor()
        cursor.execute(
            "SELECT cedula FROM usuario WHERE cedula = %s OR correo = %s", 
            (data['cedula'], data['correo'])
        )
        if cursor.fetchone():
            return jsonify({
                'success': False, 
                'message': 'Ya existe un usuario con esta cédula o correo'
            }), 400

        hashed_password = generate_password_hash(data['clave'])
        query = """
        INSERT INTO usuario (cedula, nombre, apellido, cargo, correo, telefono, clave)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data['cedula'], data['nombre'], data['apellido'],
            data['cargo'], data['correo'], data['telefono'], hashed_password
        ))
        conn.commit()
        return jsonify({
            'success': True, 
            'message': 'Usuario creado exitosamente'
        })
    
    except Exception as e:
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
    app.run(debug=True, port=5000, host='0.0.0.0')