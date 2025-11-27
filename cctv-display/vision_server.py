# vision_server.py
import sys
import json
import cv2
from ultralytics import YOLO
import logging

# 불필요한 로그 끄기
logging.getLogger("ultralytics").setLevel(logging.CRITICAL)

def analyze_video(video_url):
    try:
        # 1. YOLOv8 모델 로드 (처음 실행 시 자동으로 다운로드됨 - 약 6MB)
        # 'yolov8n.pt'는 가장 가볍고 빠른 모델입니다.
        model = YOLO('yolov8n.pt') 

        # 2. 영상 스트림 열기
        cap = cv2.VideoCapture(video_url)
        
        if not cap.isOpened():
            return {"status": "error", "msg": "영상 접속 실패", "count": 0}

        # 3. 프레임 하나 읽기 (스냅샷)
        ret, frame = cap.read()
        if not ret:
            return {"status": "error", "msg": "프레임 캡처 실패", "count": 0}
        
        cap.release() # 자원 해제

        # 4. AI 추론 (차량 인식)
        # classes=[2, 5, 7] -> 2:Car, 5:Bus, 7:Truck (COCO 데이터셋 기준)
        results = model(frame, classes=[2, 5, 7], verbose=False)
        
        # 5. 결과 분석
        # 감지된 박스 개수 세기
        vehicle_count = len(results[0].boxes)
        
        # 6. 혼잡도 판단 로직 (화면 내 차량 대수 기준)
        status = "원활"
        score = 0
        
        if vehicle_count >= 15:
            status = "정체 (매우 혼잡)"
            score = 90
        elif vehicle_count >= 8:
            status = "서행 (차량 많음)"
            score = 50
        else:
            status = "원활 (여유)"
            score = 10

        return {
            "status": "success",
            "count": vehicle_count,
            "risk_label": status,
            "risk_score": score
        }

    except Exception as e:
        return {"status": "error", "msg": str(e), "count": 0}

if __name__ == '__main__':
    # Node.js에서 영상 주소를 받음
    # python vision_server.py "http://cctv.url..."
    if len(sys.argv) > 1:
        url = sys.argv[1]
        result = analyze_video(url)
        print(json.dumps(result))
    else:
        print(json.dumps({"status": "error", "msg": "URL 없음"}))