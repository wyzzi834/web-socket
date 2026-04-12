"""
WEB SERVER LANJUTAN - VERSI STABIL UNTUK WINDOWS
- Support multiple client dengan threading
- Bisa serve file statis
- Parsing query parameter
- Tidak putus koneksi di browser
"""

import socket
import threading
import os
from urllib.parse import urlparse, parse_qs

HOST = 'localhost'
PORT = 8081
STATIC_DIR = 'www'

# Buat folder www jika belum ada
os.makedirs(STATIC_DIR, exist_ok=True)

def create_sample_files():
    """Membuat file contoh jika belum ada"""
    index_path = os.path.join(STATIC_DIR, 'index.html')
    if not os.path.exists(index_path):
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Advanced Server</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 50px; text-align: center; }
        h1 { color: #27ae60; }
        .nav a { margin: 0 10px; }
    </style>
</head>
<body>
    <h1>Advanced Socket Server</h1>
    <p>Server ini bisa serve file statis dan parsing query parameter!</p>
    <div class="nav">
        <a href="/data?nama=Andi&umur=20">Test Query Parameter</a> |
        <a href="/submit">Test Form POST</a> |
        <a href="/about.html">About Page</a>
    </div>
</body>
</html>""")
    
    about_path = os.path.join(STATIC_DIR, 'about.html')
    if not os.path.exists(about_path):
        with open(about_path, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html>
<head><title>About</title></head>
<body>
    <h1>Tentang Server Ini</h1>
    <p>Ini adalah advanced web server dengan threading support.</p>
    <p>Server ini berjalan di port 8081</p>
    <p><a href="/">Kembali ke Home</a></p>
</body>
</html>""")

def parse_request(request_data):
    """Parse HTTP request menjadi struktur data"""
    try:
        lines = request_data.split('\r\n')
        if not lines:
            return None
        
        # Parse request line
        request_line = lines[0].split(' ')
        if len(request_line) < 2:
            return None
            
        method = request_line[0]
        path = request_line[1]
        version = request_line[2] if len(request_line) > 2 else "HTTP/1.1"
        
        # Parse headers
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, value = line.split(': ', 1)
                headers[key] = value
            elif line == '':
                break
        
        # Parse query string
        parsed_url = urlparse(path)
        path_only = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        # Parse body untuk POST
        body = ''
        if 'Content-Length' in headers:
            try:
                content_length = int(headers['Content-Length'])
                body_parts = request_data.split('\r\n\r\n', 1)
                if len(body_parts) > 1:
                    body = body_parts[1][:content_length]
            except:
                pass
        
        return {
            'method': method,
            'path': path_only if path_only else '/',
            'version': version,
            'headers': headers,
            'query_params': query_params,
            'body': body
        }
    except Exception as e:
        print(f"Error parsing request: {e}")
        return None

def serve_static_file(path):
    """Membaca file statis dari disk"""
    # Prevent directory traversal attack
    safe_path = path.lstrip('/')
    if not safe_path or safe_path == '/':
        safe_path = 'index.html'
    
    full_path = os.path.join(STATIC_DIR, safe_path)
    
    if os.path.exists(full_path) and os.path.isfile(full_path):
        try:
            with open(full_path, 'rb') as f:
                content = f.read()
            
            # Tentukan content type
            if full_path.endswith('.html'):
                content_type = 'text/html; charset=utf-8'
            elif full_path.endswith('.css'):
                content_type = 'text/css'
            elif full_path.endswith('.js'):
                content_type = 'application/javascript'
            else:
                content_type = 'text/plain'
            
            return content, content_type, 200
        except Exception as e:
            print(f"Error reading file: {e}")
            return None, None, 500
    
    return None, None, 404

def send_response(client_socket, status_code, content_type, content):
    """Helper untuk mengirim response HTTP"""
    try:
        # Pastikan content dalam bytes
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        response = f"""HTTP/1.1 {status_code}
Content-Type: {content_type}
Content-Length: {len(content)}
Connection: close

""".encode('utf-8') + content
        
        client_socket.sendall(response)
        return True
    except Exception as e:
        print(f"Error sending response: {e}")
        return False

def handle_client(client_socket, client_address):
    """Menangani satu koneksi client"""
    print(f"[Thread] Menangani {client_address}")
    
    try:
        # Set timeout
        client_socket.settimeout(10)
        
        # Baca request
        request_data = client_socket.recv(4096).decode('utf-8', errors='ignore')
        
        if not request_data:
            print(f"No data from {client_address}")
            client_socket.close()
            return
        
        # Parse request
        parsed = parse_request(request_data)
        if not parsed:
            print(f"Failed to parse request from {client_address}")
            send_response(client_socket, "400 Bad Request", "text/html", "<h1>400 Bad Request</h1>")
            client_socket.close()
            return
        
        print(f"{parsed['method']} {parsed['path']} from {client_address}")
        
        # ROUTING
        # Route 1: Home page
        if parsed['path'] == '/' or parsed['path'] == '/index.html':
            content, content_type, status = serve_static_file('/index.html')
            if content:
                send_response(client_socket, "200 OK", content_type, content)
            else:
                # Fallback HTML jika file tidak ada
                html = """<!DOCTYPE html>
<html>
<head><title>Advanced Server</title></head>
<body>
<h1>Advanced Socket Server</h1>
<p>Server berjalan dengan baik!</p>
<p><a href="/data?nama=Test&umur=20">Coba query parameter</a></p>
<p><a href="/submit">Coba form POST</a></p>
</body>
</html>"""
                send_response(client_socket, "200 OK", "text/html", html)
        
        # Route 2: Data dengan query parameter
        elif parsed['path'] == '/data':
            nama = parsed['query_params'].get('nama', ['Guest'])[0]
            umur = parsed['query_params'].get('umur', ['?'])[0]
            html = f"""<!DOCTYPE html>
<html>
<head><title>Data Parameter</title>
<style>body {{ font-family: Arial; margin: 50px; }}</style>
</head>
<body>
<h1>Data yang Diterima</h1>
<p><strong>Nama:</strong> {nama}</p>
<p><strong>Umur:</strong> {umur}</p>
<p><strong>Method:</strong> {parsed['method']}</p>
<p><strong>Path:</strong> {parsed['path']}</p>
<p><a href="/">← Kembali ke Home</a></p>
</body>
</html>"""
            send_response(client_socket, "200 OK", "text/html", html)
        
        # Route 3: Form submit (GET dan POST)
        elif parsed['path'] == '/submit':
            if parsed['method'] == 'POST':
                # Proses data POST
                body = parsed['body']
                html = f"""<!DOCTYPE html>
<html>
<head><title>POST Received</title>
<style>body {{ font-family: Arial; margin: 50px; }}</style>
</head>
<body>
<h1>Data POST Diterima</h1>
<p><strong>Raw Body:</strong></p>
<pre>{body}</pre>
<p><a href="/">← Kembali ke Home</a></p>
<p><a href="/submit">← Kirim data lagi</a></p>
</body>
</html>"""
                send_response(client_socket, "200 OK", "text/html", html)
            else:
                # Tampilkan form untuk GET request
                html = """<!DOCTYPE html>
<html>
<head><title>Submit Form</title>
<style>
    body { font-family: Arial; margin: 50px; }
    input, textarea { margin: 10px 0; padding: 5px; width: 300px; }
    input[type=submit] { width: auto; cursor: pointer; }
</style>
</head>
<body>
<h1>Form Submit</h1>
<form method="POST">
    <p>Nama: <input type="text" name="nama" placeholder="Masukkan nama"></p>
    <p>Email: <input type="email" name="email" placeholder="email@example.com"></p>
    <p>Pesan: <textarea name="pesan" rows="4" placeholder="Tulis pesan..."></textarea></p>
    <p><input type="submit" value="Kirim Data"></p>
</form>
<p><a href="/">← Kembali ke Home</a></p>
</body>
</html>"""
                send_response(client_socket, "200 OK", "text/html", html)
        
        # Route 4: Serve static files
        else:
            content, content_type, status = serve_static_file(parsed['path'])
            if content:
                send_response(client_socket, "200 OK", content_type, content)
            else:
                # 404 Not Found
                html = f"""<!DOCTYPE html>
<html>
<head><title>404 Not Found</title>
<style>body {{ font-family: Arial; margin: 50px; text-align: center; }}</style>
</head>
<body>
<h1> 404 - Halaman Tidak Ditemukan</h1>
<p>Path: {parsed['path']}</p>
<p>File tidak ditemukan di server.</p>
<p><a href="/">← Kembali ke Home</a></p>
</body>
</html>"""
                send_response(client_socket, "404 Not Found", "text/html", html)
        
    except socket.timeout:
        print(f" Timeout untuk {client_address}")
    except ConnectionResetError:
        print(f"🔌 Koneksi di-reset oleh client {client_address}")
    except Exception as e:
        print(f" Error handling {client_address}: {type(e).__name__}: {e}")
    finally:
        try:
            client_socket.close()
        except:
            pass
        print(f"🔌 Koneksi {client_address} ditutup")

def run_advanced_server():
    """Menjalankan server dengan threading"""
    # Buat file contoh
    create_sample_files()
    
    # Buat socket server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)
    
    print("=" * 60)
    print(" ADVANCED WEB SERVER (SOCKET + THREADING)")
    print("=" * 60)
    print(f" Server: http://{HOST}:{PORT}")
    print(f" Static files directory: {STATIC_DIR}")
    print(" Dengan threading support!")
    print(" Tekan Ctrl+C untuk menghentikan server")
    print("=" * 60)
    print()
    print(" Server siap menerima koneksi...")
    print()
    
    try:
        while True:
            # Terima koneksi
            client_socket, client_address = server_socket.accept()
            print(f" Koneksi baru dari {client_address}")
            
            # Handle di thread terpisah
            client_thread = threading.Thread(
                target=handle_client, 
                args=(client_socket, client_address),
                daemon=True
            )
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\n\n Server dihentikan oleh user")
    finally:
        server_socket.close()
        print(" Socket server ditutup")
        print(" Server berhenti. Terima kasih!")

if __name__ == "__main__":
    run_advanced_server()