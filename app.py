from flask import Flask, jsonify, request
import requests
import re
import os

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.tiktok.com/",
}

@app.route('/get_user_info', methods=['GET'])
def get_tiktok_info():
    username = request.args.get("username")  # Lấy giá trị của tham số username từ query string

    if not username:
        return jsonify({"error": "Thiếu username!"}), 400

    url = f"https://www.tiktok.com/@{username}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return jsonify({"error": f"Request thất bại! Mã lỗi: {response.status_code}"}), response.status_code

    content = response.text
    count = content.count(username)

    if count == 1:
        return jsonify({"message": "Couldn't find this account"}), 404
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
            return jsonify(user_data)
        else:
            return jsonify({"error": "Không tìm thấy đủ dữ liệu!"}), 500
    else:
        return jsonify({"message": "Không có dữ liệu cần xử lý."}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)