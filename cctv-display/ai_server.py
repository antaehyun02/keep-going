# ai_server.py (진짜 데이터 버전)
import sys
import json
import pandas as pd
import numpy as np
import glob
import os
from sklearn.ensemble import RandomForestRegressor
import warnings

# 경고 무시
warnings.filterwarnings("ignore")

def train_and_predict(day, hour):
    try:
        # 1. 실제 데이터 파일 읽기
        path = "./data/" 
        all_files = glob.glob(os.path.join(path, "*.csv"))
        
        # 파일이 없으면 어쩔 수 없이 가상 데이터 사용 (안전장치)
        if not all_files:
            return {"status": "error", "message": "파일 없음", "speed": 90, "risk": "데이터 없음"}

        # 2. 데이터 전처리 (CSV에서 필요한 것만 뽑기)
        df_list = []
        for f in all_files:
            try:
                # 날짜, 시간, 평균속도만 읽음
                temp = pd.read_csv(f, usecols=['SUM_YRMTHDAT', 'SUM_HR', 'SPD_AVG'])
                df_list.append(temp)
            except: continue
            
        if not df_list:
            return {"status": "error", "message": "데이터 빈값", "speed": 80}

        # 데이터 합치기
        df = pd.concat(df_list, ignore_index=True)
        
        # 날짜(20251001)를 요일(0~6)로 변환
        df['SUM_YRMTHDAT'] = pd.to_datetime(df['SUM_YRMTHDAT'], format='%Y%m%d', errors='coerce')
        df['day_of_week'] = df['SUM_YRMTHDAT'].dt.dayofweek
        
        # 결측치 제거 (속도 없는 데이터 삭제)
        df = df.dropna(subset=['day_of_week', 'SUM_HR', 'SPD_AVG'])

        # 3. AI 모델 학습 (RandomForest)
        # 입력(X): [요일, 시간] -> 정답(y): [평균속도]
        X = df[['day_of_week', 'SUM_HR']]
        y = df['SPD_AVG']
        
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit(X, y)

        # 4. 실시간 예측 (현재 요일, 시간 넣기)
        predicted_speed = model.predict([[day, hour]])[0]
        
        # 5. 위험도 판단 (실제 속도 기준)
        # 고속도로는 80km/h 미만이면 서행, 40km/h 미만이면 정체로 봅니다.
        risk_level = "원활"
        if predicted_speed < 40: risk_level = "정체 (위험)"
        elif predicted_speed < 80: risk_level = "서행 (주의)"
        
        return {
            "status": "success",
            "speed": round(predicted_speed, 1),
            "risk": risk_level,
            "source": "Real Data" # 진짜 데이터임을 표시
        }

    except Exception as e:
        # 에러나면 가상값 반환 (멈춤 방지)
        return {"status": "error", "message": str(e), "speed": 85, "risk": "시스템 오류"}

if __name__ == '__main__':
    try:
        # Node.js에서 요일(d), 시간(h)만 받음 (혼잡도는 CSV에 있으니 필요 없음)
        d = int(sys.argv[1])
        h = int(sys.argv[2])
        
        result = train_and_predict(d, h)
        print(json.dumps(result))
    except:
        print(json.dumps({"status": "error", "speed": 0, "risk": "Error"}))