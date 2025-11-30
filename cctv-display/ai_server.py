import sys
import json
import pandas as pd
import numpy as np
import os
from xgboost import XGBRegressor
import warnings

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings("ignore")

def predict_traffic(day, hour, cctv_id):
    csv_path = "./data/history.csv"
    
    # 기본값 설정
    result = { 
        "status": "error", 
        "speed": 0,           # ★ 핵심: 웹사이트가 찾는 변수명
        "current_normal": 0, 
        "future_pred": 0, 
        "risk": "분석 중", 
        "time_msg": "" 
    }

    try:
        target_hour = (hour + 1) % 24
        result['time_msg'] = f"{target_hour}시 기준 (1시간 후)"

        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            
            if len(df) > 50:
                X = df[['day', 'hour']]
                y = df['speed']

                model = XGBRegressor(n_estimators=100, max_depth=4, random_state=42)
                model.fit(X, y)

                # 1. 평소 속도
                base_current = model.predict([[day, hour]])[0]
                
                # 2. 미래 속도
                next_day = day if target_hour != 0 else (day + 1) % 7
                base_future = model.predict([[next_day, target_hour]])[0]

                # 변동성 적용
                np.random.seed(int(cctv_id) + day)
                variation = np.random.randint(-15, 15)

                pred_val = int(max(10, min(120, base_future + variation)))
                curr_val = int(max(10, min(120, base_current + variation)))

                # 결과 담기
                result['status'] = "success"
                result['future_pred'] = pred_val
                result['current_normal'] = curr_val
                
                # ★ [수정] 웹사이트가 'speed'를 찾으므로 여기에 미래 예측값을 넣어줌
                result['speed'] = pred_val 

                # 위험도 라벨링
                if pred_val < 40: result['risk'] = "🟥 정체 예상"
                elif pred_val < 80: result['risk'] = "🟨 서행 예상"
                else: result['risk'] = "🟩 원활 예상"
            else:
                result['risk'] = "데이터 부족"
                result['speed'] = 0
        else:
            result['risk'] = "CSV 없음"
            result['speed'] = 0

    except Exception as e:
        result['risk'] = "AI 에러"
        result['speed'] = 0

    return result

if __name__ == '__main__':
    try:
        d = int(sys.argv[1])
        h = int(sys.argv[2])
        c_id = sys.argv[3] if len(sys.argv) > 3 else 0
        print(json.dumps(predict_traffic(d, h, c_id)))
    except:
        print(json.dumps({"status": "error", "speed": 0, "risk": "오류"}))