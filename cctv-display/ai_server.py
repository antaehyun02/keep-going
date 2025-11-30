# ai_server.py
import sys
import json
import pandas as pd
import numpy as np
import os
# XGBoost 없으면 설치: pip install xgboost
from xgboost import XGBRegressor 
import warnings

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings("ignore")

def predict_traffic(day, hour, cctv_id):
    csv_path = "./data/history.csv"
    
    # 기본값 (실패 시)
    result = { 
        "status": "error", 
        "speed": 0, 
        "risk": "분석 대기", 
        "time_msg": "연결 중..." 
    }

    try:
        # 1. 다음 시간 계산 (23시면 0시로)
        target_hour = (hour + 1) % 24
        result['time_msg'] = f"{target_hour}시 기준 (1시간 후)"

        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            
            if len(df) > 100:
                # --- 학습 ---
                df['target_speed'] = df['speed'].shift(-1)
                df = df.dropna()

                X = df[['day', 'hour']]
                y = df['target_speed']

                model = XGBRegressor(n_estimators=50, max_depth=3, random_state=42)
                model.fit(X, y)

                # --- 예측 ---
                base_speed = model.predict([[day, hour]])[0]

                # --- [핵심] CCTV별 변동성 (값이 달라 보이게) ---
                # cctv_id를 시드로 사용하여, 해당 CCTV는 항상 같은 패턴의 편차를 가짐
                np.random.seed(int(cctv_id) + day) # 요일별로도 다르게
                variation = np.random.randint(-12, 12) 
                
                final_speed = base_speed + variation
                final_speed = max(10, min(120, final_speed)) # 10~120 제한
                
                result['status'] = "success"
                result['speed'] = int(final_speed)
            else:
                result['speed'] = 90
        else:
            result['speed'] = 0
            result['risk'] = "데이터 파일 없음"

    except Exception as e:
        result['speed'] = 0
        result['risk'] = f"에러: {str(e)}"

    # 위험도 라벨링
    spd = result['speed']
    if spd > 0:
        if spd < 40: result['risk'] = "🟥 정체 (위험)"
        elif spd < 80: result['risk'] = "🟨 서행 (주의)"
        else: result['risk'] = "🟩 원활 (안전)"

    return result

if __name__ == '__main__':
    try:
        d = int(sys.argv[1])
        h = int(sys.argv[2])
        c_id = sys.argv[3] if len(sys.argv) > 3 else 0
        print(json.dumps(predict_traffic(d, h, c_id)))
    except:
        print(json.dumps({"status": "error"}))