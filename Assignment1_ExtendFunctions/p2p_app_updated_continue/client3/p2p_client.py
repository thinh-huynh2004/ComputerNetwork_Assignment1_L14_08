import socket
import threading
import json
import os

class DHT:
    def __init__(self):
        self.nodes = {}  # Lưu trữ thông tin về các node

    def add_node(self, peer_id, files, ip, port):
        """Thêm node vào DHT với thông tin IP và port."""
        self.nodes[peer_id] = {
            'files': files,
            'ip': ip,
            'port': port
        }

    def find_node(self, filename):
        """Tìm kiếm các node có tệp yêu cầu."""
        return [
            {
                'peer_id': peer_id,
                'ip': info['ip'],
                'port': info['port']
            }
            for peer_id, info in self.nodes.items() if filename in info['files']
        ]

    def get_all_nodes(self):
        """Trả về tất cả các node trong DHT."""
        return self.nodes

    def remove_node(self, peer_id):
        """Xóa node khỏi DHT khi nó không còn hoạt động."""
        if peer_id in self.nodes:
            del self.nodes[peer_id]
            print(f"Node {peer_id} removed from DHT.")

    def update_node_files(self, peer_id, files):
        """Cập nhật danh sách tệp của node."""
        if peer_id in self.nodes:
            self.nodes[peer_id]['files'] = files
            print(f"Node {peer_id} updated with files: {files}")

class Torrent:
    def __init__(self, client, filename, peer_ip, peer_port):
        self.client = client  # Tham chiếu đến đối tượng Client
        self.filename = filename
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.download_thread = None

    def start_download(self):
        self.download_thread = threading.Thread(target=self.download_file)
        self.download_thread.start()

    def download_file(self):
        # Gọi hàm download_file từ lớp Client
        self.client.download_file(self.peer_ip, self.peer_port, self.filename)

class Client:
    def __init__(self, peer_id, tracker_host='localhost', tracker_port=6881):
        self.peer_id = peer_id
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.files = []
        self.connected = True
        self.port = 0  # Cổng của máy khách (sẽ được chọn ngẫu nhiên)
        self.server_socket = None  # Server socket cho kết nối tải tệp
        self.active_downloads = 0  # Biến để theo dõi số lượng tải xuống đang hoạt động
        self.dht = DHT()  # Khởi tạo một đối tượng DHT
    
    def start_file_server(self):
        """Bắt đầu server socket để lắng nghe yêu cầu tải tệp từ các máy khách khác"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', 0))  # Chọn một cổng ngẫu nhiên
        self.server_socket.listen(5)
        self.port = self.server_socket.getsockname()[1]
        print(f"File server started on port {self.port}")
        
        # Bắt đầu một luồng riêng để xử lý các yêu cầu tải tệp
        threading.Thread(target=self.handle_incoming_connections, daemon=True).start()

    def handle_incoming_connections(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            # print(f"Accepted connection from {addr}")
            threading.Thread(target=self.handle_client_request, args=(client_socket,), daemon=True).start()

    def handle_client_request(self, client_socket):
        """Xử lý yêu cầu tải tệp từ một máy khách khác hoặc lệnh từ tracker."""
        try:
            request = json.loads(client_socket.recv(1024).decode('utf-8'))
            command = request.get("command")
            # print(f"Received request: {request}")

            if command == "ping":
                response = self.handle_ping_request(request)
                client_socket.sendall(json.dumps(response).encode('utf-8'))
            elif command == "download":
                filename = request.get("filename")
                print(f"Received request for file: {filename}")

                if filename in self.files:
                    with open(f"./shared_files/{filename}", "rb") as f:
                        data = f.read(1024)
                        while data:
                            client_socket.send(data)
                            data = f.read(1024)
                    print(f"File {filename} sent successfully.")
                else:
                    print(f"File {filename} not found.")
            else:
                print("Invalid command received.")
        except Exception as e:
            print(f"Error handling file request: {e}")
        finally:
            client_socket.close()

    def connect_to_tracker(self):
        print("Connecting to tracker...")
        self.connected = True
        print("Connected to tracker.")
    
    def sign_in(self):
        print("Signing in...")
        self.connect_to_tracker()
        self.publish_files()

    def sign_out(self):
        self.connected = False
        self.notify_sign_out()  # Gọi hàm thông báo khi đăng xuất
        self.send_sign_out_notification()  # Gửi thông báo tới tracker

    def notify_sign_out(self):
        """Thông báo khi client đăng xuất."""
        print(f"Client {self.peer_id} has signed out.")

    def send_sign_out_notification(self):
        """Gửi thông báo đăng xuất tới tracker."""
        response = self.send_request({
            "command": "sign_out",
            "peer_id": self.peer_id
        })
        print("Sign out notification response:", response)

    def publish_files(self):
        self.files = os.listdir('./shared_files')
        
        print("Publishing files...")
        response = self.send_request({
            "command": "register", 
            "peer_id": self.peer_id, 
            "files": self.files, 
            "port": self.port  # Đảm bảo gửi đúng cổng máy khách
        })
        print("Publish response:", response)
    
    def download_file(self, ip, port, filename):
        self.active_downloads += 1  # Tăng số lượng tải xuống
        print(f"Active downloads: {self.active_downloads}")
        print(f"Connecting to {ip}:{port} to download {filename}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                s.sendall(json.dumps({"command": "download", "filename": filename}).encode('utf-8'))
                
                # Đảm bảo thư mục 'shared_files' tồn tại
                if not os.path.exists('./shared_files'):
                    os.makedirs('./shared_files')
                
                # Lưu tệp vào thư mục shared_files của máy khách
                with open(f'./shared_files/{filename}', 'wb') as f:
                    while True:
                        data = s.recv(1024)
                        if not data:
                            break
                        f.write(data)
                print(f"Downloaded {filename} successfully to shared_files.")
                
                # Cập nhật danh sách tệp sau khi tải thành công
                self.files.append(filename)
                
                self.active_downloads -= 1  # Giảm số lượng tải xuống khi hoàn tất
                
        except ConnectionRefusedError:
            print(f"Connection refused when trying to download {filename}. The server might not be running.")
        except Exception as e:
            print(f"Error downloading file: {e}")
    
    def send_request(self, data):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.tracker_host, self.tracker_port))
                s.sendall(json.dumps(data).encode('utf-8'))
                response = json.loads(s.recv(1024).decode('utf-8'))
            return response
        except Exception as e:
            print(f"Error: {e}")
            return {}
    
    def command_shell(self):
        print("Starting command shell...")
        print("Enter commands: 'sign_in', 'sign_out', 'publish', 'fetch <filename1> <filename2>', 'discover', 'ping', 'scrape'")
        while self.connected:
            command = input(">> ").strip().split()
            if not command:
                continue
            if command[0] == 'sign_in':
                self.sign_in()
            elif command[0] == 'sign_out':
                self.sign_out()
                break
            elif command[0] == 'publish':
                self.publish_files()
            elif command[0] == 'fetch' and len(command) > 1:
                self.fetch_files(command[1:])  # Gọi hàm fetch_files với danh sách tên tệp
            elif command[0] == 'discover':
                self.perform_discover()
            elif command[0] == 'ping':
                self.perform_ping()
            elif command[0] == 'scrape':
                self.scrape_tracker()
            else:
                print("Invalid command. Please try again.")

    def perform_discover(self):
        print("Performing discover...")
        peers = self.send_request({"command": "discover"})
        for peer in peers.get('clients', []):
            print(f"Peer ID: {peer['peer_id']}, IP: {peer['ip']}, Port: {peer['port']}, Files: {peer['files']}")

    def perform_ping(self):
        print("Performing ping...")
        response = self.send_request({"command": "ping", "peer_id": self.peer_id})
        print(f"Ping response: {response}")

    def scrape_tracker(self):
        """Gửi yêu cầu scrape đến tracker để nhận thông tin về tệp và các peer."""
        try:
            print("Sending scrape request to tracker...")
            response = self.send_request({
                "command": "scrape",
            })

            if response['status_code'] == 200:
                print("Scrape response:", response)  # Kiểm tra dữ liệu nhận được
                # Xử lý dữ liệu nhận được từ tracker
                self.process_scrape_response(response)

                # Thêm thông tin các peer vào DHT
                for peer in response.get('files', []):
                    peer_id = peer['peer_info']['peer_id']
                    files = peer['filenames']
                    peer_ip = peer['peer_info']['ip']
                    peer_port = peer['peer_info']['port']
                    self.dht.add_node(peer_id, files, peer_ip , peer_port)  # Thêm peer vào DHT
                    print(f"Added peer {peer_id} with files {files} to DHT.")
                
                print(self.dht.get_all_nodes())  # In ra tất cả các node trong DHT
            else:
                print(f"Failed to scrape tracker: {response['status_code']}")  # In ra mã trạng thái
        except Exception as e:
            print(f"Error during scrape: {e}")  # In ra lỗi nếu có

    def process_scrape_response(self, data):
        """Xử lý phản hồi từ tracker sau khi scrape."""
        # Giả định rằng dữ liệu trả về chứa thông tin về các tệp và peer
        for peer in data.get('files', []):
            print(f"File(s): {peer['filenames']}, Peer Info: {peer['peer_info']}")

    def fetch_files(self, filenames):
        print(f"Fetching files: {filenames}")
        
        for filename in filenames:
            print(f"Fetching file: {filename}")
            
            # Tìm kiếm trong DHT trước
            peers = self.dht.find_node(filename)
            if peers:
                print("Found peers in DHT:")
                for peer in peers:
                    print(f"Attempting to download {filename} from peer {peer['peer_id']} at {peer['ip']}:{peer['port']}")
                    torrent = Torrent(self, filename, peer['ip'], peer['port'])
                    torrent.start_download()
                    break  # Kết thúc sau khi bắt đầu tải từ DHT
            else:
                # Nếu không tìm thấy trong DHT, tìm kiếm qua tracker
                print("File not found in DHT, searching through tracker...")
                peers = self.send_request({"command": "discover"})["clients"]
                for peer in peers:
                    if filename in peer["files"] and peer["peer_id"] != self.peer_id:
                        peer_ip = peer["ip"]
                        peer_port = peer["port"]
                        print(f"Attempting to download {filename} from {peer_ip}:{peer_port} via tracker")
                        torrent = Torrent(self, filename, peer_ip, peer_port)
                        torrent.start_download()
                        break
                else:
                    print(f"File {filename} not found on any connected peers.")

    def handle_ping_request(self, request):
        """Xử lý yêu cầu ping từ tracker."""
        peer_id = request.get("peer_id")
        # print(f"Received ping from tracker")
        return {"status": "pong"}

if __name__ == "__main__":
    peer_id = input("Enter a unique peer ID for this client: ")
    client = Client(peer_id=peer_id)
    client.start_file_server()  # Bắt đầu server để lắng nghe yêu cầu tải tệp
    client.command_shell()
