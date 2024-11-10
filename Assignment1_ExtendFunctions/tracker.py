import socket
import threading
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler


class TrackerHTTPRequestHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for fetching client information."""
    def parse_query_params(self, path):
        # Extract the query part of the URL after '?'
        query_string = path.split('?', 1)[-1] if '?' in path else ''
        params = {}
        
        # Split the query string into key=value pairs
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
        return params
    
    def ping_server(self, host, port):
        # Attempt to ping the server on the given host and port
        try:
            start_time = time.time()
            # Create a socket to the server
            with socket.create_connection((host, port), timeout=2):
                end_time = time.time()
                response_time_ms = round((end_time - start_time) * 1000)  # Convert to milliseconds
                return {
                    "ip": host,
                    "port": port,
                    "status": "Connected",
                    "response_time_ms": response_time_ms
                }
        except (socket.timeout, socket.error):
            return {
                "ip": host,
                "port": port,
                "status": "Disconnected",
                "response_time_ms": "N/A"
            }

    def do_GET(self):
        if self.path == '/clients':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")  # CORS header
            self.end_headers()

            # Send the current list of clients as a JSON response
            response = json.dumps({"clients": self.server.tracker_instance.clients})
            self.wfile.write(response.encode('utf-8'))
        elif self.path == '/discover':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")  # CORS header
            self.end_headers()

            # Send the current list of clients as a JSON response
            response = json.dumps({"clients": self.server.tracker_instance.clients})
            self.wfile.write(response.encode('utf-8'))
        elif self.path == '/ping':
            # Parse query parameters
            query_params = self.parse_query_params(self.path)
            host = query_params.get("host", "127.0.0.1")
            port = int(query_params.get("port", 6881))
            
            # Ping the server
            ping_response = self.ping_server(host, port)
            
            # Respond with the ping data in JSON format
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Send the ping response as JSON
            self.wfile.write(json.dumps(ping_response).encode('utf-8'))
        elif self.path == '/publish':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")  # CORS header
            self.end_headers()

            # Send the current list of clients as a JSON response
            response = json.dumps({"clients": self.server.tracker_instance.clients})
            self.wfile.write(response.encode('utf-8'))
        elif self.path == '/fetch':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")  # CORS header
            self.end_headers()

            # Send the current list of clients as a JSON response
            response = json.dumps({"clients": self.server.tracker_instance.clients})
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

class Tracker:
    def __init__(self, host='localhost', port=6881, http_port=8001):
        self.host = host
        self.port = port
        self.http_port = http_port
        self.ping = 0
        self.clients = {}

    def start(self):
        # Start the TCP server for client registrations
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Tracker started on {self.host}:{self.port}")

        # Start the HTTP server for fetching client data
        threading.Thread(target=self.start_http_server, daemon=True).start()
        
        while True:
            client_socket, addr = server_socket.accept()
            print(f"Accepted connection from {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
    
    def start_http_server(self):
        httpd = HTTPServer((self.host, self.http_port), TrackerHTTPRequestHandler)
        httpd.tracker_instance = self  # Pass tracker instance to handler
        print(f"HTTP server for client data running on port {self.http_port}")
        httpd.serve_forever()

    def handle_client(self, client_socket):
        try:
            request = json.loads(client_socket.recv(1024).decode('utf-8'))
            command = request.get('command')

            if command == 'register':
                self.register_client(request)
            elif command == 'discover':
                self.discover_clients(client_socket)
            elif command == 'ping':
                self.ping_client(request, client_socket)
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def register_client(self, request):
        """Đăng ký hoặc cập nhật thông tin client khi sign_in hoặc publish_files"""
        peer_id = request.get('peer_id')
        ip = request.get('ip')
        port = request.get('port')
        status = request.get('status', 'connected')
        files = request.get('files', [])

        if peer_id:
            # Lưu hoặc cập nhật thông tin client
            self.clients[peer_id] = {
                'ip': ip,
                'port': port,
                'status': status,
                'files': files
            }
            print(f"Registered client {peer_id} with files: {files} and status: {status}")
        else:
            print("Error: Peer ID is missing in the registration request.")

    def unregister_client(self, request):
        """Cập nhật trạng thái client thành disconnected khi sign_out"""
        peer_id = request['peer_id']
        
        if peer_id in self.clients:
            self.clients[peer_id]['status'] = 'disconnected'
            print(f"Client {peer_id} disconnected.")
        else:
            print(f"Client {peer_id} not found for disconnection.")

    def discover_clients(self, client_socket):
        """Gửi danh sách tất cả client và trạng thái hiện tại"""
        response = {'clients': [
            {
                'peer_id': peer_id,
                'ip': info['ip'],
                'port': info['port'],
                'status': info['status'],
                'files': info['files']
            }
            for peer_id, info in self.clients.items()
        ], "show-discover": True}
        
        client_socket.sendall(json.dumps(response).encode('utf-8'))

    def ping_client(self, request, client_socket):
        response = {'status': 'alive'}
        client_socket.sendall(json.dumps(response).encode('utf-8'))

if __name__ == "__main__":
    tracker = Tracker()
    tracker.start()