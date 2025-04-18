from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import socketserver

# Dirección del backend (Jellyfin)
BACKEND_HOST = '10.128.0.63'
BACKEND_PORT = 8096
BACKEND_URL = f'http://{BACKEND_HOST}:{BACKEND_PORT}'

class ReverseProxyHandler(BaseHTTPRequestHandler):
    def forward_request(self, method):
        # URL de destino en el backend
        target_url = BACKEND_URL + self.path

        # Cabeceras originales, con 'Host' y 'X-Real-IP'
        headers = {key: val for key, val in self.headers.items()}
        headers['Host'] = self.headers.get('Host', BACKEND_HOST)
        headers['X-Real-IP'] = self.client_address[0]

        # Lee el cuerpo si es necesario
        body = None
        if 'Content-Length' in self.headers:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)

        # Reenvía la solicitud al backend con el mismo método
        response = requests.request(method, target_url, headers=headers, data=body, stream=True)

        # Enviar respuesta al cliente
        self.send_response(response.status_code)
        for key, value in response.headers.items():
            if key.lower() != 'transfer-encoding':
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.content)

    def do_GET(self):
        self.forward_request('GET')

    def do_POST(self):
        self.forward_request('POST')

    def do_PUT(self):
        self.forward_request('PUT')

    def do_DELETE(self):
        self.forward_request('DELETE')

    def do_PATCH(self):
        self.forward_request('PATCH')

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {self.client_address[0]} - {self.command} {self.path}")

def run(port=80):
    server_address = ('', port)
    # Usa Threading para permitir múltiples solicitudes simultáneas
    handler_class = ReverseProxyHandler
    httpd = socketserver.ThreadingTCPServer(server_address, handler_class)
    print(f"Proxy reverso escuchando en puerto {port}, redirigiendo a {BACKEND_URL}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
