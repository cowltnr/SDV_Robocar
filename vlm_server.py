from flask import Flask, request, jsonify
import traceback

app = Flask(__name__)

VALID_WPS = ["wp1", "wp2", "wp3", "wp4", "wp5"]


def select_wp_rule_based(data):
    """
    초기 테스트용 rule-based selector.
    실제 VLM 모델을 붙이기 전, 서버 통신과 route publish 흐름 검증용.
    """

    obstacle = data.get("obstacle")
    image_width = data.get("image_width", 1280)
    candidate_routes = data.get("candidate_routes", VALID_WPS)

    valid_candidates = [wp for wp in candidate_routes if wp in VALID_WPS]
    if not valid_candidates:
        valid_candidates = VALID_WPS

    # 장애물이 없으면 중앙 route를 기본 선택
    if obstacle is None:
        return "wp2", "No obstacle information. Select center route wp2."

    center_x = obstacle.get("center_x", image_width / 2)
    distance = obstacle.get("distance", None)
    angle = obstacle.get("angle", None)

    # 화면 왼쪽에 장애물이 있으면 아래쪽 우회 route 선택
    if center_x < image_width * 0.35:
        selected_wp = "wp5" if "wp5" in valid_candidates else valid_candidates[0]
        reason = (
            f"Obstacle is on the left side of the image. "
            f"center_x={center_x}, distance={distance}, angle={angle}. "
            f"Select lower detour route."
        )

    # 화면 오른쪽에 장애물이 있으면 위쪽 우회 route 선택
    elif center_x > image_width * 0.65:
        selected_wp = "wp4" if "wp4" in valid_candidates else valid_candidates[0]
        reason = (
            f"Obstacle is on the right side of the image. "
            f"center_x={center_x}, distance={distance}, angle={angle}. "
            f"Select upper detour route."
        )

    # 중앙에 있으면 넓은 우회 route를 우선 선택
    else:
        selected_wp = "wp4" if "wp4" in valid_candidates else valid_candidates[0]
        reason = (
            f"Obstacle is near the center of the path. "
            f"center_x={center_x}, distance={distance}, angle={angle}. "
            f"Select wide upper detour route."
        )

    return selected_wp, reason


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "server": "vlm_server",
        "valid_wps": VALID_WPS
    }), 200


@app.route("/select_wp", methods=["POST"])
def select_wp():
    try:
        data = request.get_json(force=True)

        selected_wp, reason = select_wp_rule_based(data)

        if selected_wp not in VALID_WPS:
            return jsonify({
                "selected_wp": None,
                "reason": f"Invalid selected_wp: {selected_wp}"
            }), 200

        print("\n[VLM SERVER] Request received")
        print(f"[VLM SERVER] obstacle={data.get('obstacle')}")
        print(f"[VLM SERVER] candidate_routes={data.get('candidate_routes')}")
        print(f"[VLM SERVER] selected_wp={selected_wp}")
        print(f"[VLM SERVER] reason={reason}")

        return jsonify({
            "selected_wp": selected_wp,
            "reason": reason
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