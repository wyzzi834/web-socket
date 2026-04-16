import asyncio
import websockets
import json
import requests
import os
from bs4 import BeautifulSoup

# The URL to scrape
MAL_TOP_ANIME_URL = "https://myanimelist.net/topanime.php"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

async def scrape_myanimelist(websocket, offset=0):
    """
    Function to scrape 50 anime records starting from the given offset.
    """
    await websocket.send(json.dumps({
        "type": "status",
        "message": f"Mulai melakukan proses scraping untuk ranking {offset + 1} - {offset + 50}..."
    }))
    
    try:
        loop = asyncio.get_event_loop()
        anime_count = 0
        
        target_url = f"{MAL_TOP_ANIME_URL}?limit={offset}"
        
        # Tambahkan sistem otomatis coba ulang (retry) 3 kali jika koneksi terputus
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                # Tambahkan timeout 15 detik untuk menghindari hang
                response = await loop.run_in_executor(
                    None, 
                    lambda url=target_url: requests.get(url, headers=HEADERS, timeout=15)
                )
                break # Jika sukses, keluar dari loop retry
            except Exception as req_err:
                if attempt == max_retries - 1:
                    raise req_err # Jika sudah 3 kali masih gagal, lempar errornya
                # Tunggu 2 detik sebelum mencoba lagi ke MyAnimeList
                await asyncio.sleep(2)
        
        if response.status_code != 200:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Gagal mengambil data pada offset {offset}. Status {response.status_code}"
            }))
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        anime_rows = soup.select('tr.ranking-list')
        
        if not anime_rows:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Tidak dapat menemukan data pada offset {offset}."
            }))
            return
            
        scraped_data = []
        
        for row in anime_rows:
            # Peringkat bisa didapat dari elemen atau berdasar offset
            rank_el = row.select_one('.rank span')
            rank = rank_el.text.strip() if rank_el else str(offset + anime_count + 1)
            
            title_el = row.select_one('.anime_ranking_h3 a')
            title = title_el.text.strip() if title_el else "Unknown Title"
            
            score_el = row.select_one('.score span')
            score = score_el.text.strip() if score_el else "N/A"
            
            item_data = {
                "rank": rank,
                "title": title,
                "score": score
            }
            scraped_data.append(item_data)
            
            await websocket.send(json.dumps({
                "type": "data",
                "data": item_data
            }))
            anime_count += 1

        await websocket.send(json.dumps({
            "type": "status",
            "message": f"Selesai! {anime_count} anime telah berhasil ditarik."
        }))
        
    except Exception as e:
        await websocket.send(json.dumps({
            "type": "error",
            "message": f"Terjadi kesalahan saat scraping: {str(e)}"
        }))

async def handler(websocket):
    """
    WebSocket connection handler
    """
    client_address = websocket.remote_address
    print(f"[SERVER] Client baru terhubung: {client_address}")
    
    try:
        async for message in websocket:
            print(f"[SERVER] Menerima pesan dari {client_address}: {message}")
            if message.startswith("start_scraping:"):
                # Menangkap offset dari klien, e.g., "start_scraping:50"
                try:
                    offset = int(message.split(":")[1])
                except ValueError:
                    offset = 0
                await scrape_myanimelist(websocket, offset)
            else:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Pesan tidak dikenali."
                }))
    except websockets.exceptions.ConnectionClosed as e:
        print(f"[SERVER] Client {client_address} terputus.")

async def main():
    HOST = "localhost"
    PORT = 8765
    print(f"=== Memulai WebSocket Server di ws://{HOST}:{PORT} ===")
    print(f"Buka file 'mal_websocket_client.html' di browser Anda untuk mencoba!")
    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
