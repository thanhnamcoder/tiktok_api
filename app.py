from flask import Flask, jsonify, request
import requests
import re
import os
import concurrent.futures  # Import thư viện đa luồng

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.tiktok.com/",
}

def fetch_user_info(username):
    """Hàm gửi request đến TikTok và trích xuất thông tin user."""
    url = f"https://www.tiktok.com/@{username}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return {username: f"Request thất bại! Mã lỗi: {response.status_code}"}

    content = response.text
    count = content.count(username)

    if count == 1:
        return {username: "Couldn't find this account"}
    elif count > 2:
        # Dùng regex để tìm thông tin user
        follower_match = re.search(r'"followerCount":(\d+)', content)
        following_match = re.search(r'"followingCount":(\d+)', content)
        heart_match = re.search(r'"heartCount":(\d+)', content)
        uniqueId_match = re.search(r'"uniqueId":"(.*?)"', content)
        nickname_match = re.search(r'"nickname":"(.*?)"', content)
        signature_match = re.search(r'"signature":"(.*?)"', content)

        if all([follower_match, following_match, heart_match, uniqueId_match, nickname_match]):
            user_data = {
                "uniqueId": uniqueId_match.group(1),
                "nickname": nickname_match.group(1),
                "signature": signature_match.group(1) if signature_match else "",
                "followerCount": int(follower_match.group(1)),
                "followingCount": int(following_match.group(1)),
                "heartCount": int(heart_match.group(1))
            }
            return {username: user_data}
        else:
            return {username: "Không tìm thấy đủ dữ liệu!"}
    else:
        return {username: "Không có dữ liệu cần xử lý."}

@app.route('/get_user_info', methods=['GET'])
def get_tiktok_info():
    """API nhận nhiều username và xử lý đa luồng."""
    usernames = request.args.get("username")  # Lấy danh sách username
    if not usernames:
        return jsonify({"error": "Thiếu username!"}), 400

    username_list = usernames.split(",")  # Tách danh sách username bằng dấu phẩy

    # Dùng ThreadPoolExecutor để chạy đa luồng
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch_user_info, username_list))

    # Gộp kết quả thành dictionary
    merged_results = {k: v for result in results for k, v in result.items()}
    
    return jsonify(merged_results)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)  # Bật chế độ threaded
