# ai_server.py (새벽 시간 보정 로직 추가)
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
    
    result = { 
        "status": "error", "speed": 0,
        "current_normal": 0, "future_pred": 0, "forecast": [],
        "risk": "분석 중", "time_msg": "" 
    }

    try:
        target_hour = (hour + 1) % 24
        result['time_msg'] = f"{target_hour}시 기준 (1시간 후)"

        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            
            if len(df) > 50:
                X = df[['day', 'hour']]
                y = df['speed']
                model = XGBRegressor(n_estimators=100, max_depth=5, random_state=42)
                model.fit(X, y)

                # 현재, 미래 기본 예측
                base_current = model.predict([[day, hour]])[0]
                
                nxt_day = day if target_hour != 0 else (day + 1) % 7
                base_future = model.predict([[nxt_day, target_hour]])[0]

                # ★ [보정] 새벽 시간(22~06)엔 고속도로 특성상 속도가 높아야 정상
                if 22 <= hour or hour <= 6: base_current = max(90, base_current)
                if 22 <= target_hour or target_hour <= 6: base_future = max(90, base_future)

                # 변동성 적용
                np.random.seed(int(cctv_id) + day)
                var = np.random.randint(-10, 10) # 변동폭을 조금 줄임 (안정적 그래프 위해)

                result['current_normal'] = int(max(10, min(120, base_current + var)))
                result['future_pred'] = int(max(10, min(120, base_future + var)))
                result['speed'] = result['future_pred']
                result['status'] = "success"

                # 12시간 예보 생성
                forecast_list = []
                for i in range(12):
                    f_hour = (hour + i) % 24
                    f_day = day
                    if (hour + i) >= 24: f_day = (day + 1) % 7
                    
                    pred = model.predict([[f_day, f_hour]])[0]
                    
                    # 새벽 시간 보정 (그래프가 V자로 꺾이는 것 방지)
                    if 22 <= f_hour or f_hour <= 6:
                        pred = max(95, pred) # 새벽엔 최소 95 보장
                    
                    final = int(max(10, min(120, pred + var)))
                    forecast_list.append({"time": f"{f_hour}시", "speed": final})
                
                result['forecast'] = forecast_list

                # 위험도
                if result['speed'] < 40: result['risk'] = "🟥 정체 예상"
                elif result['speed'] < 80: result['risk'] = "🟨 서행 예상"
                else: result['risk'] = "🟩 원활 예상"
            else:
                result['risk'] = "데이터 부족"
        else:
            result['risk'] = "파일 없음"

    except Exception as e:
        result['risk'] = "AI 에러"

    return result

if __name__ == '__main__':
    try:
        d = int(sys.argv[1])
        h = int(sys.argv[2])
        c_id = sys.argv[3] if len(sys.argv) > 3 else 0
        print(json.dumps(predict_traffic(d, h, c_id)))
    except:
        print(json.dumps({"status": "error"}))