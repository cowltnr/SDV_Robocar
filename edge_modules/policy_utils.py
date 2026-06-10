import yaml


def allow_send_distance(policy_file):
    try:
        with open(policy_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        action = data["i2nsf-security-policy"]["rules"]["action"]["packet-action"]["ingress-action"]
        return action == "pass"
    except Exception as e:
        print(f"[Policy ERROR] YAML 파싱 실패 또는 필드 없음: {e}")
        return False
