import time
import requests
import pandas as pd
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 1. Cấu hình quy chuẩn dự án
IMG_WIDTH = 1000
OUTPUT_DIR = "./data/raw/facebook/"

def process_and_save_image(url, img_id):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    
    # Resize theo width=1000, giữ nguyên tỷ lệ
    w_percent = (IMG_WIDTH / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_percent)))
    img = img.resize((IMG_WIDTH, h_size), Image.LANCZOS)
    
    # Convert sang RGB tránh lỗi kênh Alpha
    img = img.convert("RGB")
    
    filename = f"FB_{img_id:03d}.jpg"
    img.save(f"{OUTPUT_DIR}{filename}")
    return filename

# 2. Selenium Scraper (MVP)
def scrape_samsung_fb(limit=10):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://www.facebook.com/SamsungVietnam/photos")
    time.sleep(5) # Đợi load trang

    data_list = []
    # Logic cuộn và lấy các phần tử ảnh/tương tác sẽ nằm ở đây
    # Ví dụ giả lập thu thập 1 item:
    img_url = "https://example.com/samsung-banner.jpg"
    interactions = {"likes": 1200, "comments": 45, "shares": 10}
    
    # Xử lý ảnh và lưu record
    img_name = process_and_save_image(img_url, 1)
    data_list.append({"img_id": img_name, **interactions})
    
    df = pd.DataFrame(data_list)
    df.to_csv(f"{OUTPUT_DIR}metadata.csv", index=False)
    driver.quit()

# Chạy thử
scrape_samsung_fb()