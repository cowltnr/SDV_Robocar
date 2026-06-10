from flask import Flask, request, jsonify
import requests
import json
import re
import traceback

app = Flask(__name__)

VALID_WPS = ["wp1", "wp2", "wp3", "wp4", "wp5"]

OLLAMA_API = "http://localhost:11434/api/chat"
VLM_MODEL = "qwen2.5vl:3b"

def clean_vlm_text(text):
    if text is None:
        return None

    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    return text

def parse_selected_wp(text):
    """
    VLM 응답에서 wp1~wp5 중 하나만 안전하게 추출한다.
    VLM이 JSON을 반환해도 되고, 일반 문장으로 반환해도 처리한다.
    """
    if text is None:
        return None

    text = clean_vlm_text(text)

    # 1) JSON 응답 우선 처리
    try:
        data = json.loads(text)
        wp = data.get("selected_wp")
        if wp in VALID_WPS:
            return wp
    except Exception:
        pass

    # 2) 일반 텍스트에서 wp 추출
    lower_text = text.lower()
    for wp in VALID_WPS:
        if re.search(rf"\b{wp}\b", lower_text):
            return wp

    return None


def parse_reason(text):
    """
    VLM 응답에서 reason을 가져온다.
    JSON 파싱 실패 시 raw answer를 reason으로 남긴다.
    """
    if text is None:
        return None

    text = clean_vlm_text(text)

    try:
        data = json.loads(text)
        return data.get("reason", "selected by VLM")
    except Exception:
        return text


def build_prompt(data):
    obstacle = data.get("obstacle")
    goal = data.get("goal")
    candidate_routes = data.get("candidate_routes", VALID_WPS)
    image_width = data.get("image_width")
    image_height = data.get("image_height")

    prompt = f"""
You are a waypoint route selector for an indoor mobile robot.

The robot has candidate waypoint routes:
{candidate_routes}

Route meaning:
- wp1: upper short detour route
- wp2: center route
- wp3: lower short detour route
- wp4: upper wide detour route
- wp5: lower wide detour route

User goal point:
{goal}

Camera image size:
width={image_width}, height={image_height}

Detected obstacle information from YOLO and 2D LiDAR:
{obstacle}

Task:
Select the safest waypoint route among the candidate routes.

Rules:
1. Return only one route from the candidate_routes list.
2. Do not select a route that is not in candidate_routes.
3. If the obstacle is near the center of the path, prefer a wider detour route.
4. If the obstacle is on the left side of the image, prefer a route away from the obstacle.
5. If the obstacle is on the right side of the image, prefer a route away from the obstacle.
6. Use the image and obstacle JSON together.

Output format:
Return only raw JSON.
Do not use markdown.
Do not use ```json code fences.
Do not add extra text.

Example:
{{"selected_wp": "wp4", "reason": "Obstacle is near the center, so a wide upper detour is safer."}}
"""
    return prompt.strip()


def call_ollama_vlm(image_b64, prompt):
    payload = {
        "model": VLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64] if image_b64 else []
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 100
        }
    }

    response = requests.post(
        OLLAMA_API,
        json=payload,
        timeout=180.0
    )
    response.raise_for_status()

    result = response.json()
    return result["message"]["content"]


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "server": "vlm_server",
        "model": VLM_MODEL,
        "valid_wps": VALID_WPS
    }), 200


@app.route("/select_wp", methods=["POST"])
def select_wp():
    try:
        data = request.get_json(force=True)

        image_b64 = data.get("image")
        candidate_routes = data.get("candidate_routes", VALID_WPS)

        valid_candidates = [
            wp for wp in candidate_routes
            if wp in VALID_WPS
        ]

        if not valid_candidates:
            return jsonify({
                "selected_wp": None,
                "reason": "No valid candidate routes were provided."
            }), 200

        prompt = build_prompt({
            **data,
            "candidate_routes": valid_candidates
        })

        raw_answer = call_ollama_vlm(
            image_b64=image_b64,
            prompt=prompt
        )

        selected_wp = parse_selected_wp(raw_answer)
        reason = parse_reason(raw_answer)

        if selected_wp not in valid_candidates:
            print("\n[VLM SERVER] Invalid VLM route")
            print(f"[VLM SERVER] candidate_routes={valid_candidates}")
            print(f"[VLM SERVER] raw_answer={raw_answer}")

            return jsonify({
                "selected_wp": None,
                "reason": f"VLM selected invalid route. raw_answer={raw_answer}",
                "raw_answer": raw_answer
            }), 200

        print("\n[VLM SERVER] Request received")
        print(f"[VLM SERVER] model={VLM_MODEL}")
        print(f"[VLM SERVER] obstacle={data.get('obstacle')}")
        print(f"[VLM SERVER] goal={data.get('goal')}")
        print(f"[VLM SERVER] candidate_routes={valid_candidates}")
        print(f"[VLM SERVER] raw_answer={raw_answer}")
        print(f"[VLM SERVER] selected_wp={selected_wp}")
        print(f"[VLM SERVER] reason={reason}")

        return jsonify({
            "selected_wp": selected_wp,
            "reason": reason,
            "raw_answer": raw_answer
        }), 200

    except Exception as e:
        print("[VLM SERVER ERROR]")
        print(traceback.format_exc())

        return jsonify({
            "selected_wp": None,
            "reason": f"server_error: {e}"
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090, threaded=True)