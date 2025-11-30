# preprocess_all.py (불량 데이터 필터링 버전)
import pandas as pd
import glob
import os
import warnings

warnings.filterwarnings("ignore")

file_list = glob.glob('./data/data_*.csv')
output_file = './data/history.csv'

if not file_list:
    print("❌ 'data' 폴더에 csv 파일이 없습니다.")
    exit()

print(f"🔄 {len(file_list)}개 파일 정밀 전처리 시작...")

all_data = []

for file in file_list:
    try:
        try: df = pd.read_csv(file, encoding='cp949')
        except: df = pd.read_csv(file, encoding='utf-8')

        if '구간' in df.columns: df = df.drop(columns=['구간'])

        id_vars = [col for col in df.columns if '시간' in col or 'hour' in col]
        if id_vars:
            df_melted = df.melt(id_vars=id_vars, var_name='date', value_name='speed')
            df_melted.rename(columns={id_vars[0]: 'hour'}, inplace=True)
            all_data.append(df_melted)
            print(f"  - {os.path.basename(file)} 읽기 완료")
    except Exception as e:
        print(f"⚠️ {file} 에러: {e}")

if all_data:
    final_df = pd.concat(all_data, ignore_index=True)

    # 1. 숫자 변환
    final_df['hour'] = final_df['hour'].astype(str).str.replace('시', '').astype(int)
    final_df['speed'] = final_df['speed'].astype(str).str.replace(' km/h', '').str.replace(',', '')
    
    # 2. 에러 처리 (숫자가 아닌 건 NaN으로)
    final_df['speed'] = pd.to_numeric(final_df['speed'], errors='coerce')

    # ★ [핵심 수정] 속도가 0이거나 NaN인 '쓰레기 데이터' 삭제
    # 고속도로 평균속도가 10km/h 미만인 건 측정 오류일 확률이 높음 -> 제거
    original_len = len(final_df)
    final_df = final_df.dropna(subset=['speed'])
    final_df = final_df[final_df['speed'] > 10] 
    
    print(f"🧹 데이터 클리닝: 불량 데이터 {original_len - len(final_df)}개 제거됨")

    # 3. 날짜 처리
    final_df['date'] = final_df['date'].str.replace('.', '-')
    final_df['day'] = pd.to_datetime(final_df['date'], errors='coerce').dt.dayofweek
    final_df = final_df.dropna(subset=['day'])
    final_df['day'] = final_df['day'].astype(int)

    final_df = final_df.sort_values(by=['date', 'hour'])
    final_df = final_df[['date', 'day', 'hour', 'speed']]
    
    final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print("------------------------------------------------")
    print(f"✅ 학습 데이터 생성 완료: {output_file}")
    print("👉 이제 '새벽에 0km/h'로 학습되는 문제가 해결되었습니다.")
else:
    print("❌ 변환 실패")