from ultralytics import YOLO
import cv2
import os
import time
import requests
import winsound
import threading
from datetime import datetime
from dotenv import load_dotenv
camera_lock = threading.Lock()

load_dotenv()


# =========================================================
# EMAIL CONFIGURATION
# =========================================================

SENTINEL_EMAIL = os.getenv("SENTINEL_EMAIL")
SENTINEL_APP_PASSWORD = os.getenv("SENTINEL_APP_PASSWORD")
ALERT_EMAIL = os.getenv("ALERT_EMAIL")


# =========================================================
# MODEL
# =========================================================

MODEL_PATH = r"C:\runs\detect\runs\detect\sentinelai_fast\weights\best.pt"

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"YOLO model not found: {MODEL_PATH}"
    )

model = YOLO(MODEL_PATH)


# =========================================================
# SETTINGS
# =========================================================

CAMERA_INDEX = 0

IMG_SIZE = 320

CONFIDENCE = 0.50

API_URL = "http://127.0.0.1:5000/api/alert"

ALERT_COOLDOWN = 10


# =========================================================
# EVIDENCE FOLDER
# =========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

EVIDENCE_FOLDER = os.path.join(
    PROJECT_ROOT,
    "evidence"
)

os.makedirs(
    EVIDENCE_FOLDER,
    exist_ok=True
)


# =========================================================
# ALERT CONTROL
# =========================================================

last_alert_time = 0

alert_lock = threading.Lock()


# =========================================================
# EMAIL ALERT
# =========================================================

def send_email_alert(
    alert_type,
    confidence
):

    try:

        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()

        msg["Subject"] = (
            f"SentinelAI Alert: "
            f"{alert_type.upper()}"
        )

        msg["From"] = SENTINEL_EMAIL

        msg["To"] = ALERT_EMAIL

        msg.set_content(
            f"""SentinelAI Emergency Alert

Detection: {alert_type.upper()}
Confidence: {confidence:.2f}

A possible {alert_type} event has been detected by SentinelAI.

Please check the SentinelAI dashboard immediately.
"""
        )

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as server:

            server.login(
                SENTINEL_EMAIL,
                SENTINEL_APP_PASSWORD
            )

            server.send_message(msg)

        print(
            f"Email alert sent: "
            f"{alert_type} "
            f"({confidence:.2f})"
        )

    except Exception as error:

        print(
            "Email alert error:",
            error
        )


# =========================================================
# CREATE ALERT
# =========================================================

def process_alert(
    alert_type,
    confidence,
    annotated_frame
):

    global last_alert_time

    current_time = time.time()


    # -----------------------------------------------------
    # THREAD-SAFE COOLDOWN
    # -----------------------------------------------------

    with alert_lock:

        if (
            current_time - last_alert_time
            < ALERT_COOLDOWN
        ):

            return False

        # Reserve the alert immediately.
        # This prevents another camera stream/thread
        # from creating a duplicate alert.

        last_alert_time = current_time


    # -----------------------------------------------------
    # UNIQUE EVIDENCE FILENAME
    # -----------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    filename = (
        f"alert_{timestamp}.jpg"
    )

    filepath = os.path.join(
        EVIDENCE_FOLDER,
        filename
    )


    # -----------------------------------------------------
    # SAVE EVIDENCE
    # -----------------------------------------------------

    saved = cv2.imwrite(
        filepath,
        annotated_frame
    )

    if saved:

        print(
            f"Evidence saved: "
            f"{filepath}"
        )

    else:

        print(
            "ERROR: Evidence image could not be saved."
        )


    # -----------------------------------------------------
    # SEND BACKEND ALERT
    # -----------------------------------------------------

    backend_success = False

    try:

        response = requests.post(

            API_URL,

            json={
                "type": alert_type,
                "confidence": round(
                    confidence,
                    2
                )
            },

            timeout=2

        )


        if response.status_code in (
            200,
            201
        ):

            backend_success = True

            print(
                f"Backend alert sent: "
                f"{alert_type} "
                f"({confidence:.2f})"
            )

        else:

            print(
                "Backend error:",
                response.status_code
            )

    except Exception as error:

        print(
            "Backend alert error:",
            error
        )


    # -----------------------------------------------------
    # EMAIL
    # -----------------------------------------------------

    if backend_success:

        send_email_alert(
            alert_type,
            confidence
        )


    # -----------------------------------------------------
    # LOCAL BEEP
    # -----------------------------------------------------

    try:

        winsound.Beep(
            1000,
            500
        )

    except Exception as error:

        print(
            "Beep error:",
            error
        )


    return True


# =========================================================
# CAMERA STREAM
# =========================================================

def generate_frames():

    if not camera_lock.acquire(blocking=False):
        print("Camera already in use.")
        return

    camera = cv2.VideoCapture(
        CAMERA_INDEX,
        cv2.CAP_DSHOW
    )

    # -----------------------------------------------------
    # CAMERA CHECK
    # -----------------------------------------------------

    if not camera.isOpened():

        print(
            "ERROR: Camera open nahi ho raha."
        )

        return


    print(
        "Camera started successfully."
    )


    time.sleep(1)


    try:

        while True:


            # ------------------------------------------------
            # READ FRAME
            # ------------------------------------------------

            success, frame = camera.read()


            if (
                not success
                or frame is None
            ):

                print(
                    "WARNING: Camera frame read failed."
                )

                time.sleep(0.1)

                continue


            # ------------------------------------------------
            # YOLO DETECTION
            # ------------------------------------------------

            try:

                results = model(
                    frame,
                    imgsz=IMG_SIZE,
                    conf=CONFIDENCE,
                    verbose=False
                )

                result = results[0]

            except Exception as error:

                print(
                    "YOLO error:",
                    error
                )

                continue


            # ------------------------------------------------
            # DRAW DETECTIONS
            # ------------------------------------------------

            annotated_frame = result.plot()


            # ------------------------------------------------
            # FIND BEST FIRE / SMOKE
            # ------------------------------------------------

            best_confidence = 0.0

            best_class = None


            if (
                result.boxes is not None
                and len(result.boxes) > 0
            ):

                for box in result.boxes:


                    confidence = float(
                        box.conf[0]
                    )


                    class_id = int(
                        box.cls[0]
                    )


                    class_name = result.names.get(
                        class_id,
                        "unknown"
                    )


                    if class_name in (
                        "fire",
                        "smoke"
                    ):

                        if (
                            confidence
                            > best_confidence
                        ):

                            best_confidence = (
                                confidence
                            )

                            best_class = (
                                class_name
                            )


            # ------------------------------------------------
            # ALERT PROCESSING
            # ------------------------------------------------

            if best_class is not None:

                process_alert(
                    best_class,
                    best_confidence,
                    annotated_frame
                )


            # ------------------------------------------------
            # JPEG STREAM
            # ------------------------------------------------

            success, buffer = cv2.imencode(
                ".jpg",
                annotated_frame
            )


            if not success:

                print(
                    "JPEG encoding failed."
                )

                continue


            frame_bytes = (
                buffer.tobytes()
            )


            yield (

                b"--frame\r\n"

                b"Content-Type: image/jpeg\r\n\r\n"

                + frame_bytes

                + b"\r\n"

            )


    except GeneratorExit:

        print(
            "Camera stream disconnected."
        )


    except Exception as error:

        print(
            "Camera stream error:",
            error
        )


    finally:

        camera.release()
        camera_lock.release()

        print(
            "Camera released."
        )