from flask import Flask, jsonify, request
import requests
import re
import os
import json
import time
import concurrent.futures

app = Flask(__name__)

CACHE_FILE = "cache.json"
CACHE_EXPIRY = 600  # 10 phút

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.tiktok.com/",
}

# Tối ưu hóa session để giảm tải kết nối HTTP
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=3)
session.mount("https://", adapter)


def load_cache():
    """Tải cache từ file JSON."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_cache(cache_data):
    """Lưu cache vào file JSON."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=4)


def get_cached_user(username):
    """Kiểm tra cache và trả về nếu dữ liệu còn hạn."""
    cache = load_cache()
    if username in cache:
        cached_time = cache[username].get("timestamp", 0)
        if time.time() - cached_time < CACHE_EXPIRY:
            return cache[username]["data"]
    return None


def fetch_user_info(username):
    """Gửi request đến TikTok và trích xuất thông tin user."""
    url = f"https://www.tiktok.com/@{username}"

    try:
        response = session.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
    except requests.RequestException as e:
        return {username: f"Lỗi request: {str(e)}"}

    content = response.text
    count = content.count(username)

    if count == 1:
        return {username: "Không tìm thấy tài khoản"}
    elif count > 2:
        # Dùng regex để tìm thông tin user
        follower_match = re.search(r'"followerCount":(\d+)', content)
        following_match = re.search(r'"followingCount":(\d+)', content)
        heart_match = re.search(r'"heart":(\d+)', content)
        uniqueId_match = re.search(r'"uniqueId":"(.*?)"', content)
        nickname_match = re.search(r'"nickname":"(.*?)"', content)

        user_data = {
            "uniqueId": uniqueId_match.group(1) if uniqueId_match else "",
            "nickname": nickname_match.group(1) if nickname_match else "",
            "followerCount": int(follower_match.group(1)) if follower_match else 0,
            "followingCount": int(following_match.group(1)) if following_match else 0,
            "heart": int(heart_match.group(1)) if heart_match else 0
        }

        # Lưu cache
        cache = load_cache()
        cache[username] = {"timestamp": time.time(), "data": user_data}
        save_cache(cache)

        return {username: user_data}
    else:
        return {username: "Không có dữ liệu cần xử lý."}


@app.route('/get_user_info', methods=['GET'])
def get_tiktok_info():
    """API nhận nhiều username, check cache trước khi gửi request."""
    usernames = request.args.get("username")
    if not usernames:
        return jsonify({"error": "Thiếu username!"}), 400

    username_list = usernames.split(",")
    num_users = len(username_list)

    start_time = time.time()

    results = {}
    usernames_to_fetch = []

    # Kiểm tra cache trước
    for username in username_list:
        cached_data = get_cached_user(username)
        if cached_data:
            results[username] = cached_data
        else:
            usernames_to_fetch.append(username)

    # Fetch những username chưa có trong cache
    if usernames_to_fetch:
        max_workers = min(5, num_users)  # Giới hạn luồng để tránh quá tải RAM
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            fetched_results = list(executor.map(fetch_user_info, usernames_to_fetch))
            for result in fetched_results:
                results.update(result)

    print(f"Xử lý {num_users} users trong {time.time() - start_time:.2f}s")

    return jsonify(results)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
