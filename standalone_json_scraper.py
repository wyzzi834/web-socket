import os
import json
import requests
from bs4 import BeautifulSoup
import time

MAL_TOP_ANIME_URL = "https://myanimelist.net/topanime.php"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

def scrape_to_json(limit=0):
    print(f"[*] Melakukan scraping data anime ranking {limit + 1} - {limit + 50}...")
    target_url = f"{MAL_TOP_ANIME_URL}?limit={limit}"
    
    max_retries = 3
    response = None
    for attempt in range(max_retries):
        try:
            response = requests.get(target_url, headers=HEADERS, timeout=15)
            break
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[!] Gagal mengambil data: {e}")
                return
            time.sleep(2)
            
    if not response or response.status_code != 200:
        print(f"[!] Gagal mengambil web, status: {response.status_code if response else 'T/A'}")
        return
        
    soup = BeautifulSoup(response.text, 'html.parser')
    anime_rows = soup.select('tr.ranking-list')
    
    if not anime_rows:
        print("[!] Tidak dapat menemukan data di MyAnimeList.")
        return
        
    scraped_data = []
    
    for count, row in enumerate(anime_rows):
        rank_el = row.select_one('.rank span')
        rank = rank_el.text.strip() if rank_el else str(limit + count + 1)
        
        title_el = row.select_one('.anime_ranking_h3 a')
        title = title_el.text.strip() if title_el else "Unknown Title"
        
        score_el = row.select_one('.score span')
        score = score_el.text.strip() if score_el else "N/A"
        
        scraped_data.append({
            "rank": rank,
            "title": title,
            "score": score
        })
        
    # Logika Simpan JSON
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(BASE_DIR, "standalone_anime_data.json")
    existing_data = []
    
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except Exception:
            pass
            
    # Menggabungkan data tanpa duplikat
    data_dict = {str(item.get('rank', '')): item for item in existing_data if isinstance(item, dict) and 'rank' in item}
    for item in scraped_data:
        data_dict[str(item['rank'])] = item
        
    # Mengurutkan lalu menyimpan
    final_data = list(data_dict.values())
    final_data.sort(key=lambda x: int(x['rank']) if str(x['rank']).isdigit() else 99999)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
        
    print(f"[+] Selesai! {len(scraped_data)} anime ditarik. \n[+] Total isi file sekarang: {len(final_data)} rekaman di '{os.path.basename(filename)}'\n")

if __name__ == "__main__":
    print("=== MyAnimeList JSON Scraper CLI ===")
    print("Program ini khusus untuk menarik data dalam format JSON.\n")
    current_limit = 0
    scrapes_count = 0
    while True:
        pilihan = input(f"Tekan ENTER untuk scrape peringkat {current_limit+1}-{current_limit+50} (atau ketik 'keluar' untuk stop): ")
        if pilihan.lower() in ['keluar', 'exit', 'stop', 'q']:
            print("Sampai jumpa!")
            break
        
        scrape_to_json(current_limit)
        current_limit += 50
        scrapes_count += 1
