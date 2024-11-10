import socket
import threading
import json
import time

class Tracker:
    def __init__(self, host='localhost', port=6881):
        self.host = host
        self.port = port
        self.clients = {}
        threading.Thread(target=self.ping_clients, daemon=True).start()  # Bắt đầu thread ping clients

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Tracker started on {self.host}:{self.port}")
        
        while True:
            client_socket, addr = server_socket.accept()
            print(f"Accepted connection from {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def handle_client(self, client_socket):
        try:
            # Nhận dữ liệu từ client
            data = client_socket.recv(1024).decode('utf-8')
            print(f"Received data: {data}")  # Kiểm tra dữ liệu nhận được

            # Kiểm tra xem dữ liệu có rỗng không
            if not data:
                print("No data received from client.")
                return

            # Giải mã JSON
            request = json.loads(data)
            command = request.get('command')

            if command == 'register':
                self.register_client(request, client_socket)
            elif command == 'discover':
                self.discover_clients(client_socket)
            elif command == 'ping':
                self.ping_client(request, client_socket)
            elif command == 'scrape':
                self.scrape_clients(client_socket)
            elif command == 'sign_out':
                self.logout_client(request, client_socket)
            else:
                print(f"Unknown command: {command}")
        except json.JSONDecodeError:
            print("Error decoding JSON from client data.")
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def register_client(self, request, client_socket):
        peer_id = request['peer_id']
        port = request['port']
        files = request['files']

        # Lưu thông tin máy khách vào từ điển với peer_id
        self.clients[peer_id] = {'ip': self.host, 'port': port, 'files': files}
        print(f"Registered client {peer_id} with files: {files}")
        
        # Gửi phản hồi về client
        response = {'status': 'success', 'message': 'Client registered successfully.'}
        client_socket.sendall(json.dumps(response).encode('utf-8'))

    def discover_clients(self, client_socket):
        response = {'clients': [{'peer_id': peer_id, 'ip': info['ip'], 'port': info['port'], 'files': info['files']} for peer_id, info in self.clients.items()]}
        client_socket.sendall(json.dumps(response).encode('utf-8'))

    def ping_client(self, request, client_socket):
        response = {'status': 'alive'}
        client_socket.sendall(json.dumps(response).encode('utf-8'))

    def scrape_clients(self, client_socket):
        """Xử lý yêu cầu scrape từ client và gửi thông tin về các tệp và peer."""
        response = {
            'status_code': 200,  # Thêm mã trạng thái
            'files': []
        }
        print("Received scrape request from client.")  # Kiểm tra khi nhận yêu cầu

        if not self.clients:  # Kiểm tra xem có client nào không
            response['status_code'] = 404  # Thay đổi mã trạng thái nếu không có client
            response['message'] = 'No clients registered.'
            print("No clients registered.")  # In ra thông báo nếu không có client
        else:
            for peer_id, info in self.clients.items():
                print(f"Registering client {peer_id} with files: {info['files']}")  # Kiểm tra thông tin client
                response['files'].append({
                    'filenames': info['files'],  # Giả định rằng files là danh sách tên tệp
                    'peer_info': {'peer_id': peer_id, 'ip': info['ip'], 'port': info['port']}
                })
        
        print(f"Sending response to client: {response}")  # Kiểm tra phản hồi sẽ gửi
        try:
            client_socket.sendall(json.dumps(response).encode('utf-8'))  # Gửi phản hồi về client
            print("Response sent successfully.")  # Xác nhận gửi thành công
        except Exception as e:
            print(f"Error sending response: {e}")  # In ra lỗi nếu có
            
    def ping_clients(self):
        while True:
            time.sleep(10)  # Chờ 10 giây
            for peer_id, info in list(self.clients.items()):
                try:
                    # Gửi yêu cầu ping tới client
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((info['ip'], info['port']))
                    ping_request = json.dumps({'command': 'ping', 'peer_id': peer_id}).encode('utf-8')
                    client_socket.sendall(ping_request)
                    response = client_socket.recv(1024).decode('utf-8')
                    # print(f"Ping response from {peer_id}: {response}")
                    client_socket.close()
                except (socket.error, OSError):
                    print(f"Client {peer_id} is offline. Removing from list.")
                    del self.clients[peer_id]  # Xóa client khỏi danh sách nếu không còn kết nối
            print(len(self.clients), "available peer(s):", [peer_id for peer_id in self.clients])

    def logout_client(self, request, client_socket):
        peer_id = request['peer_id']
        if peer_id in self.clients:
            del self.clients[peer_id]  # Xóa client khỏi danh sách
            print(f"Client {peer_id} has logged out.")  # Thông báo client đã đăng xuất
            response = {'status': 'success', 'message': 'Client logged out successfully.'}
        else:
            response = {'status': 'error', 'message': 'Client not found.'}
        
        client_socket.sendall(json.dumps(response).encode('utf-8'))  # Gửi phản hồi về client
        self.ping_clients()  # Gọi hàm ping_clients để cập nhật danh sách client


if __name__ == "__main__":
    tracker = Tracker()
    tracker.start()
