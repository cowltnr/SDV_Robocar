IMO_BASE = "http://192.168.50.17"
CLOUD_BASE = "http://localhost"

STREAM_URL = f"{IMO_BASE}:8000/video"
ODOM_URL = f"{IMO_BASE}:8000/odometry"
LIDAR_URL = f"{IMO_BASE}:8000/lidar"
SERVER_URL = f"{CLOUD_BASE}:8080/inference"
DIST_API = f"{IMO_BASE}:8001/control/distance"
CMD_API = f"{IMO_BASE}:8001/control/cmd_vel"
VLM_SELECT_API = f"{CLOUD_BASE}:8090/select_wp"

POLICY_FILE = "received_policy.yaml"

INFER_HZ = 10.0
SEND_INTERVAL = 1.0
JPEG_QUALITY = 70
TIMEOUT_GET = 0.3
TIMEOUT_POST = 0.5

LIDAR_HZ = 10.0
LIDAR_TO = 0.5

BASE_LAT = 37.501000
BASE_LON = 127.036000

STOP_TRIGGER = 5.0
K_TIME = 2.0
TURN_ANG = 0.35
STRAIGHT_ANG = 0.0
FORWARD_SPEED = 0.8

VALID_WPS = ["wp1", "wp2", "wp3", "wp4", "wp5"]
ROUTE_SELECT_TRIGGER = 6.0    # 4m 이하: VLM에게 우회 wp 선택 요청
EMERGENCY_STOP_TRIGGER = 1.2    # 1.2m 이하: VLM 판단과 관계없이 무조건 정지

USER_INTENT_TOPIC = "/user_intent_goal"
INTENT_FEEDBACK_TOPIC = "/intent_feedback"
SELECTED_ROUTE_TOPIC = "/selected_route"

GOAL_MATCH_TOLERANCE = 0.5