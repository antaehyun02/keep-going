# preprocess_all.py (최종 수정: 방향별 ID 자동 분류)
import pandas as pd
import glob
import os
import warnings

warnings.filterwarnings("ignore")

# 1. 파일 목록 가져오기
file_list = glob.glob('./data/*.csv')
output_file = './data/history.csv'

if not file_list:
    print("❌ 'data' 폴더에 csv 파일이 없습니다.")
    exit()

print(f"🔄 {len(file_list)}개 파일 통합 및 라벨링 시작...")

all_data = []

for file in file_list:
    try:
        filename = os.path.basename(file)
        
        # --- [핵심] 파일명에 따른 구간 ID 분류 ---
        # ID 0: 하행선 (안성->천안) / 비교적 원활
        # ID 1: 상행선 (북천안->안성, 천안->안성) / 아침 출근 정체
        # ID 2: 하행선 (수원신갈->기흥, 남사진위->안성) / 상습 정체 구간
        
        section_id = 0 # 기본값
        
        if "북천안" in filename and "안성" in filename: # 북천안->안성 (상행)
            section_id = 1
        elif "수원신갈" in filename or "남사진위" in filename: # 수원/남사 (하행 상습정체)
            section_id = 2
        else:
            section_id = 0 # 나머지 (기존 안성->북천안 하행)

        print(f"  - 읽는 중: {filename} (ID: {section_id})")

        # 파일 읽기 (인코딩 처리)
        try: df = pd.read_csv(file, encoding='cp949')
        except: df = pd.read_csv(file, encoding='utf-8')

        # 전처리
        if '구간' in df.columns: df = df.drop(columns=['구간'])
        
        id_vars = [col for col in df.columns if '시간' in col or 'hour' in col]
        if id_vars:
            df_melted = df.melt(id_vars=id_vars, var_name='date', value_name='speed')
            df_melted.rename(columns={id_vars[0]: 'hour'}, inplace=True)
            
            # 구간 ID 추가
            df_melted['section'] = section_id
            all_data.append(df_melted)

    except Exception as e:
        print(f"⚠️ 에러 ({file}): {e}")

if all_data:
    final_df = pd.concat(all_data, ignore_index=True)

    # 데이터 정제
    final_df['hour'] = final_df['hour'].astype(str).str.replace('시', '').astype(int)
    final_df['speed'] = final_df['speed'].astype(str).str.replace(' km/h', '').str.replace(',', '')
    final_df['speed'] = pd.to_numeric(final_df['speed'], errors='coerce')
    
    # 노이즈 제거 (5km/h 이하는 측정 오류로 간주)
    final_df = final_df.dropna(subset=['speed'])
    final_df = final_df[final_df['speed'] > 5]

    # 날짜 처리
    final_df['date'] = final_df['date'].str.replace('.', '-')
    final_df['day'] = pd.to_datetime(final_df['date'], errors='coerce').dt.dayofweek
    final_df = final_df.dropna(subset=['day'])
    final_df['day'] = final_df['day'].astype(int)

    # 저장
    final_df = final_df[['section', 'date', 'day', 'hour', 'speed']]
    final_df.sort_values(by=['section', 'date', 'hour'], inplace=True)
    
    final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print("------------------------------------------------")
    print(f"✅ 학습 데이터 생성 완료: {output_file}")
    print("👉 ID 0: 하행선 (비교적 원활)")
    print("👉 ID 1: 상행선 (아침 출근 정체)")
    print("👉 ID 2: 수원/남사권 (상습 정체)")
else:
    print("❌ 변환 실패")