from flask import Flask, Response
import cv2
import numpy as np

app = Flask(__name__)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)


def generate_frames():
    while True:
        success, frame = cap.read()

        if not success:
            break

        height, width = frame.shape[:2]

        center_x = width // 2
        center_y = height // 2

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Yellow HSV range
        lower_yellow = (20, 100, 100)
        upper_yellow = (35, 255, 255)

        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        # Remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            if cv2.contourArea(contour) > 500:

                x, y, w, h = cv2.boundingRect(contour)

                # Draw green box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Center of detected object
                obj_x = x + w // 2
                obj_y = y + h // 2

                # Draw red center dot
                cv2.circle(frame, (obj_x, obj_y), 6, (0, 0, 255), -1)

                # Coordinates
                cv2.putText(frame,
                            f"({obj_x}, {obj_y})",
                            (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 255, 0),

        cv2.circle(frame, (center_x, center_y), 8, (255, 0, 0), -1)

        cv2.line(frame, (center_x, 0), (center_x, height), (255, 0, 0), 2)
        cv2.line(frame, (0, center_y), (width, center_y), (255, 0, 0), 2)

        cv2.putText(frame, "TL", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        cv2.putText(frame, "TR", (width - 50, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        cv2.putText(frame, "BL", (10, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        cv2.putText(frame, "BR", (width - 50, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               frame +
               b'\r\n')
               
@app.route('/')
def index():
    return '''
    <h1>Robot Camera</h1>
    <img src="/video">
    '''

@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

app.run(host='0.0.0.0', port=5000)