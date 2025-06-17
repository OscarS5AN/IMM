from flask import Flask, request, jsonify, redirect, url_for, send_from_directory, session
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='static')
app.config['SESSION_COOKIE_DOMAIN'] = None
app.secret_key = 'clave-super-secreta-mercado-masivo'  # Necesario para usar sesiones

# ------------------- CONEXIÓN A BASE DE DATOS -------------------
db_config = {
    'host': '186.81.194.142',
    'user': 'root',
    'password': 'Database',
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
            cursor.execute("SHOW TABLES")
            cursor.close()
            conn.close()
            return True
    except Exception:
        return False

test_database_connection()

# ------------------- RUTAS -------------------
@app.route('/')
def home():
    return redirect(url_for('serve_login'))

@app.route('/login')
def serve_login():
    return send_from_directory('static', 'login.html')

@app.route('/dashboard')
def serve_dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('serve_login'))
    return send_from_directory('static', 'index.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('serve_login'))

# ------------------- API -------------------
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'usuario' not in data or 'clave' not in data:
            return jsonify({'success': False, 'message': 'Datos incompletos.'}), 400

        usuario_input = data['usuario'].strip()
        clave_input = data['clave'].strip()

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500

        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT idusuario, cedula, nombre, apellido, cargo, correo, clave, foto, telefono
            FROM usuario 
            WHERE cedula = %s OR correo = %s
            LIMIT 1
        """
        cursor.execute(query, (usuario_input, usuario_input))
        user = cursor.fetchone()

        if user and check_password_hash(user['clave'], clave_input):
            # Guardar sesión
            session['usuario_id'] = user['idusuario']
            session['nombre'] = user['nombre']
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
            return jsonify({'success': False, 'message': 'Correo o contraseña incorrectas'}), 401

    except Exception:
        return jsonify({'success': False, 'message': 'Error en el servidor'}), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/parametros', methods=['GET'])
def obtener_parametros():
    tipo = request.args.get('tipo')
    if not tipo:
        return jsonify({'success': False, 'message': 'Parámetro tipo requerido'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Error de conexión'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        tablas = {
            'Ciudad': ('SELECT id, nombre as nombre_parametro FROM ciudad', 'id'),
            'Aliado': ('SELECT id, nombre as nombre_parametro FROM aliado', 'id'),
            'Supervisor': ('SELECT id, nombre as nombre_parametro FROM supervisor', 'id'),
            'Carpeta': ('SELECT id, nombre as nombre_parametro FROM carpeta', 'id'),
            'Estado': ('SELECT id, nombre as nombre_parametro FROM estado', 'id'),
            'Segmento': ('SELECT id, nombre as nombre_parametro FROM segmento', 'id'),
            'Interventor': ('SELECT id, nombre as nombre_parametro FROM interventor', 'id')
        }

        if tipo not in tablas:
            return jsonify({'success': False, 'message': 'Tipo inválido'}), 400

        query, id_field = tablas[tipo]
        cursor.execute(query)
        resultados = cursor.fetchall()
        parametros = [{'nombre_parametro': r['nombre_parametro'], 'id_parametro': r[id_field]} for r in resultados]
        return jsonify({'success': True, 'data': parametros})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/register_technician', methods=['POST'])
def register_technician():
    try:
        data = request.get_json()
        required_fields = ['cedula', 'nombre', 'apellido', 'idCiudad', 'telefono',
                           'idAliado', 'idSupervisor', 'idCarpeta', 'idEstado',
                           'idSegmento', 'idInterventor']
        missing = [f for f in required_fields if f not in data or not data[f]]
        if missing:
            return jsonify({'success': False, 'message': f'Faltan campos: {", ".join(missing)}'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Sin conexión DB'}), 500

        cursor = conn.cursor()
        cursor.execute("SELECT cedula FROM registrotecnico WHERE cedula = %s", (data['cedula'],))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Cédula ya registrada'}), 400

        query = """
            INSERT INTO registrotecnico (
                cedula, nombre, apellido, telefono,
                idAliado, idSupervisor, idCarpeta, idEstado,
                idSegmento, idInterventor, idCiudad
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data['cedula'], data['nombre'].upper(), data['apellido'].upper(),
            data['telefono'],
            data['idAliado'], data['idSupervisor'], data['idCarpeta'],
            data['idEstado'], data['idSegmento'], data['idInterventor'],
            data['idCiudad']
        ))
        conn.commit()
        return jsonify({'success': True, 'message': 'Técnico registrado correctamente'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


# ------------------- NUEVAS RUTAS PARA HERRAMIENTAS -------------------
@app.route('/api/get_technician', methods=['GET'])
def get_technician():
    cedula = request.args.get('cedula')
    if not cedula:
        return jsonify({'success': False, 'message': 'Cédula requerida'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Error de conexión'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT r.idregistroTecnico, r.nombre, r.apellido, r.telefono,
                   c.nombre as ciudad, a.nombre as aliado, s.nombre as supervisor
            FROM registrotecnico r
            LEFT JOIN ciudad c ON r.idCiudad = c.id
            LEFT JOIN aliado a ON r.idAliado = a.id
            LEFT JOIN supervisor s ON r.idSupervisor = s.id
            WHERE r.cedula = %s
            LIMIT 1
        """
        cursor.execute(query, (cedula,))
        technician = cursor.fetchone()

        if technician:
            return jsonify({
                'success': True,
                'technician': technician
            })
        else:
            return jsonify({'success': False, 'message': 'Técnico no encontrado'}), 404

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/get_tools_by_group', methods=['GET'])
def get_tools_by_group():
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Error de conexión'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM herramientas ORDER BY grupo, herramienta"
        cursor.execute(query)
        herramientas = cursor.fetchall()

        return jsonify({
            'success': True,
            'herramientas': herramientas
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/get_tools_status', methods=['GET'])
def get_tools_status():
    tecnicoId = request.args.get('tecnicoId')
    carpeta = request.args.get('carpeta')
    
    if not tecnicoId or not carpeta:
        return jsonify({'success': False, 'message': 'Parámetros requeridos'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Error de conexión'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT idherramienta, estado 
            FROM R_HI 
            WHERE idregistroTecnico = %s AND carpeta = %s
        """
        cursor.execute(query, (tecnicoId, carpeta))
        estados = cursor.fetchall()

        return jsonify({
            'success': True,
            'estados': estados
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/save_tools', methods=['POST'])
def save_tools():
    try:
        data = request.get_json()
        if not data or 'idregistroTecnico' not in data or 'herramientas' not in data or 'carpeta' not in data:
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

        idregistroTecnico = data['idregistroTecnico']
        herramientas = data['herramientas']
        carpeta = data['carpeta']
        
        # Obtener el ID de usuario de la sesión o usar un valor por defecto
        idusuario = session.get('usuario_id')
        if not idusuario:
            return jsonify({'success': False, 'message': 'Usuario no autenticado'}), 401

        if not herramientas:
            return jsonify({'success': False, 'message': 'No hay herramientas para guardar'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500

        cursor = conn.cursor()
        
        # Primero eliminamos registros existentes para este técnico y carpeta
        cursor.execute("""
            DELETE FROM R_HI 
            WHERE idregistroTecnico = %s AND carpeta = %s
        """, (idregistroTecnico, carpeta))
        
        # Insertamos los nuevos registros con todos los campos requeridos
        for herramienta in herramientas:
            query = """
                INSERT INTO R_HI (
                    idregistroTecnico, 
                    idherramienta, 
                    estado, 
                    carpeta, 
                    idusuario, 
                    fecha
                ) VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(query, (
                idregistroTecnico,
                herramienta['idherramienta'],
                herramienta['estado'],
                carpeta,
                idusuario
            ))
        
        conn.commit()
        return jsonify({
            'success': True, 
            'message': 'Herramientas guardadas correctamente',
            'details': {
                'tecnico': idregistroTecnico,
                'carpeta': carpeta,
                'herramientas_guardadas': len(herramientas),
                'usuario': idusuario
            }
        })

    except Exception as e:
        return jsonify({
            'success': False, 
            'message': 'Error al guardar herramientas',
            'error': str(e)
        }), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ------------------- PREVENCIÓN DE CACHÉ -------------------
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# ------------------- MAIN -------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
