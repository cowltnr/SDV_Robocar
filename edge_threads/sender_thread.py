import queue
import requests


def sender_loop(server_url, timeout_post, send_q, stop_evt):
    print("[Sender] 시작")
    while not stop_evt.is_set():
        try:
            data = send_q.get(timeout=0.2)
        except queue.Empty:
            continue

        try:
            response = requests.post(server_url, json=data, timeout=timeout_post)
            if response.status_code != 200:
                print(f"[Sender] 전송 실패: {response.status_code}")
            else:
                print(f"[Sender] 전송 성공: {data.get('timestamp')}")
        except Exception as e:
            print(f"[Sender] 오류: {e}")
        finally:
            send_q.task_done()

    print("[Sender] 종료")
