from ultralytics import YOLO
import cv2
import winsound
import os
import requests
from datetime import datetime

# Trained SentinelAI model
model = YOLO(r"C:\runs\detect\runs\detect\sentinelai_fast\weights\best.pt")

# Webcam
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# Evidence folder
evidence_dir = "evidence"
os.makedirs(evidence_dir, exist_ok=True)

# Backend
API_URL = "http://127.0.0.1:5000/api/alert"

# Evidence cooldown
last_evidence_time = 0
evidence_cooldown = 10

# Backend alert cooldown
last_api_alert_time = 0
api_alert_cooldown = 30

# Stable detection protection
stable_detection_frames = 5
stable_detection_count = 0
incident_active = False
incident_miss_count = 0
incident_miss_limit = 15


def send_alert(alert_type, confidence):
    try:
        response = requests.post(
            API_URL,
            json={
                "type": alert_type,
                "confidence": round(confidence, 2)
            },
            timeout=2
        )

        if response.ok:
            print(f"Backend alert sent: {alert_type} ({confidence:.2f})")
        else:
            print(f"Backend error: {response.status_code}")

    except requests.RequestException as error:
        print(f"Backend unavailable: {error}")


while True:
    ret, frame = cap.read()

    if not ret:
        print("Camera open nahi ho raha.")
        break

    results = model(frame, imgsz=320, conf=0.25, verbose=False)

    alert = False
    detected_type = None
    highest_confidence = 0.0

    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = model.names[cls_id]

            if class_name in ["fire", "smoke"] and confidence >= 0.20:
                alert = True

                if confidence > highest_confidence:
                    highest_confidence = confidence
                    detected_type = class_name

                x1, y1, x2, y2 = map(int, box.xyxy[0])

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 0, 255),
                    2
                )

                cv2.putText(
                    frame,
                    f"{class_name} {confidence:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )

    # Require multiple consecutive detection frames
    if alert:
        stable_detection_count += 1
    else:
        stable_detection_count = 0

    confirmed_alert = stable_detection_count >= stable_detection_frames

    if confirmed_alert:
        incident_miss_count = 0
    elif incident_active:
        incident_miss_count += 1
        if incident_miss_count >= incident_miss_limit:
            incident_active = False
            incident_miss_count = 0

    if confirmed_alert and not incident_active:
        current_time = datetime.now().timestamp()

        # Save evidence
        if current_time - last_evidence_time >= evidence_cooldown:
            filename = datetime.now().strftime("alert_%Y%m%d_%H%M%S.jpg")
            filepath = os.path.join(evidence_dir, filename)

            cv2.imwrite(filepath, frame)

            print(f"Evidence saved: {filepath}")

            last_evidence_time = current_time

        # Send alert to backend
        if current_time - last_api_alert_time >= api_alert_cooldown:
            send_alert(detected_type, highest_confidence)
            last_api_alert_time = current_time

        cv2.putText(
            frame,
            "!!! FIRE/SMOKE ALERT !!!",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            3
        )

        winsound.Beep(1000, 500)
        incident_active = True

    cv2.imshow("SentinelAI - Fire & Smoke Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()