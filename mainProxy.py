from flask import Flask, request, Response, abort
import requests
from urllib.parse import urljoin
import logging
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
import time

# Configuración básica
TARGET_URL = "http://10.128.0.63:8096"  # Servidor Jellyfin
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB (para streams grandes)
TIMEOUT = 30  # segundos
WHITELIST_IPS = ['10.128.0.0/24']  # Solo permitir tráfico de la red interna

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Helpers
def check_ip_allowed(ip):
    """Verifica si la IP está en la whitelist"""
    from ipaddress import ip_address, ip_network
    client_ip = ip_address(ip.split(',')[0].strip())
    for network in WHITELIST_IPS:
        if client_ip in ip_network(network):
            return True
    return False

def log_request(f):
    """Decorador para logging de requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Incoming request: {request.method} {request.url}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        try:
            response = f(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            logger.info(f"Request completed in {duration:.2f}ms - Status: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise

    return decorated_function

# Middlewares
@app.before_request
def before_request():
    """Validaciones antes de procesar el request"""
    # Verificar tamaño del contenido
    if request.content_length and request.content_length > MAX_CONTENT_LENGTH:
        abort(413)
    
    # Validar IP (comentar si no se necesita)
    if not check_ip_allowed(request.remote_addr):
        logger.warning(f"Acceso denegado desde IP: {request.remote_addr}")
        abort(403)

# Handlers
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@log_request
def proxy(path):
    """Maneja todas las solicitudes y las redirige al servidor Jellyfin"""
    # Construye la URL destino
    target_url = urljoin(TARGET_URL, path)
    if request.query_string:
        target_url += f"?{request.query_string.decode()}"

    # Headers a enviar (filtramos algunos)
    headers = {
        key: value for key, value in request.headers
        if key.lower() not in ['host', 'connection', 'x-forwarded-for']
    }
    
    # Manejo de métodos HTTP
    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            stream=True,
            timeout=TIMEOUT
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con Jellyfin: {str(e)}")
        abort(502)

    # Construye la respuesta
    response = Response(
        resp.iter_content(chunk_size=8192),
        status=resp.status_code
    )

    # Copia headers relevantes (filtramos algunos)
    excluded_headers = [
        'content-encoding', 'content-length', 
        'transfer-encoding', 'connection'
    ]
    for key, value in resp.headers.items():
        if key.lower() not in excluded_headers:
            response.headers[key] = value

    return response

@app.errorhandler(404)
def not_found(e):
    return "404 - Recurso no encontrado", 404

@app.errorhandler(500)
def server_error(e):
    return "500 - Error interno del servidor", 500

@app.errorhandler(502)
def bad_gateway(e):
    return "502 - No se pudo conectar con el servidor Jellyfin", 502

if __name__ == '__main__':
    from waitress import serve
    logger.info("Iniciando proxy reverso Flask...")
    serve(app, host="0.0.0.0", port=80)