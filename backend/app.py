from flask import Flask, jsonify, request, send_from_directory, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# =========================
# PATHS
# =========================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

FRONTEND_FOLDER = os.path.join(
    PROJECT_ROOT,
    "frontend"
)

TEMPLATE_FOLDER = os.path.join(
    FRONTEND_FOLDER,
    "templates"
)

STATIC_FOLDER = os.path.join(
    FRONTEND_FOLDER,
    "static"
)

EVIDENCE_FOLDER = os.path.join(
    PROJECT_ROOT,
    "evidence"
)

DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "sentinelai.db"
)


# =========================
# CAMERA
# =========================

from camera_stream import generate_frames


# =========================
# DATABASE CONFIG
# =========================

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + DATABASE_PATH
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Alert(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    type = db.Column(
        db.String(50),
        nullable=False
    )

    confidence = db.Column(
        db.Float,
        nullable=False
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.now
    )


with app.app_context():
    db.create_all()


# =========================
# HOME
# =========================

@app.route("/")
def home():

    return send_from_directory(
        TEMPLATE_FOLDER,
        "index.html"
    )


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    return send_from_directory(
        TEMPLATE_FOLDER,
        "index.html"
    )


# =========================
# STATIC FILES
# =========================

@app.route("/static/<path:filename>")
def static_files(filename):

    return send_from_directory(
        STATIC_FOLDER,
        filename
    )


# =========================
# BACKEND STATUS
# =========================

@app.route("/api/status")
def status():

    return jsonify({
        "status": "online",
        "service": "SentinelAI Backend",
        "project": "SentinelAI"
    })


# =========================
# LIVE CAMERA
# =========================

@app.route("/video_feed")
def video_feed():

    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# =========================
# EVIDENCE IMAGE
# =========================

@app.route("/evidence/<path:filename>")
def evidence_file(filename):

    return send_from_directory(
        EVIDENCE_FOLDER,
        filename
    )


# =========================
# EVIDENCE API
# =========================

@app.route("/api/evidence")
def get_evidence():

    if not os.path.exists(EVIDENCE_FOLDER):

        return jsonify({
            "count": 0,
            "evidence": []
        })

    files = []

    for filename in os.listdir(
        EVIDENCE_FOLDER
    ):

        if filename.lower().endswith(
            (
                ".jpg",
                ".jpeg",
                ".png",
                ".webp"
            )
        ):

            files.append(filename)

    files.sort(
        reverse=True
    )

    return jsonify({

        "count": len(files),

        "evidence": [

            {
                "filename": filename,
                "url": "/evidence/" + filename
            }

            for filename in files

        ]

    })


# =========================
# CREATE ALERT
# =========================

@app.route(
    "/api/alert",
    methods=["POST"]
)
def create_alert():

    data = request.get_json(
        silent=True
    ) or {}

    detection_type = str(
        data.get(
            "type",
            "unknown"
        )
    ).lower()

    try:

        confidence = float(
            data.get(
                "confidence",
                0
            )
        )

    except (
        ValueError,
        TypeError
    ):

        confidence = 0.0


    alert = Alert(

        type=detection_type,

        confidence=confidence

    )

    db.session.add(alert)

    db.session.commit()


    return jsonify({

        "success": True,

        "message": "Alert saved",

        "alert": {

            "id": alert.id,

            "type": alert.type,

            "confidence":
                alert.confidence,

            "timestamp":
                alert.timestamp.isoformat()

        }

    }), 201


# =========================
# GET ALERTS
# =========================

@app.route(
    "/api/alerts",
    methods=["GET"]
)
def get_alerts():

    all_alerts = Alert.query.order_by(
        Alert.timestamp.desc()
    ).all()


    return jsonify({

        "count":
            len(all_alerts),

        "alerts": [

            {

                "id":
                    alert.id,

                "type":
                    alert.type,

                "confidence":
                    alert.confidence,

                "timestamp":
                    alert.timestamp.isoformat()

            }

            for alert in all_alerts

        ]

    })


# =========================
# CLEAR ALERTS
# =========================

@app.route(
    "/api/alerts/clear",
    methods=["DELETE"]
)
def clear_alerts():

    Alert.query.delete()

    db.session.commit()

    return jsonify({

        "success": True,

        "message":
            "All alerts cleared"

    })


# =========================
# ERROR HANDLER
# =========================

@app.errorhandler(404)
def not_found(error):

    return jsonify({

        "error": "Route not found",

        "message":
            "The requested page or API does not exist."

    }), 404


# =========================
# RUN SERVER
# =========================

if __name__ == "__main__":

    print("")
    print("=" * 55)
    print("        SENTINELAI SECURITY COMMAND CENTER")
    print("=" * 55)
    print("")
    print("Backend:  http://127.0.0.1:5000")
    print("Dashboard: http://127.0.0.1:5000/")
    print("API:      http://127.0.0.1:5000/api/status")
    print("")
    print("=" * 55)
    print("")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False
    )