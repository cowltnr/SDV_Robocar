from flask import Flask, request, jsonify
import datetime
import os
import json

app = Flask(__name__)

# 결과를 저장할 디렉토리
LOG_DIR = "inference_logs"
os.makedirs(LOG_DIR, exist_ok=True)

@app.route('/inference', methods=['POST'])
def receive_inference():
    try:
        # 클라이언트에서 JSON 수신
        data = request.get_json(force=True)

        # 필수 필드 점검
        if "objects" not in data:
            return jsonify({"error": "Missing 'objects' field"}), 400

        # timestamp가 존재하면 사용, 없으면 현재 시각
        timestamp = data.get("timestamp", datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

        # 로그 파일 저장 경로
        filename = f"{timestamp}.json"
        filepath = os.path.join(LOG_DIR, filename)

        # JSON 파일로 저장
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        print(f"[{timestamp}] 수신 완료 | 객체 수: {len(data.get('objects', []))}")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"에러 발생: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
