import pandas as pd
import glob
import os

# 1. 파일 목록 가져오기
file_list = glob.glob('./data/data_*.csv') # data_8, data_9, data_10
output_file = './data/history.csv'

if not file_list:
    print("❌ 데이터 파일이 없습니다. data 폴더에 data_8.csv 등을 넣어주세요.")
    exit()

all_data = []

print("🔄 데이터 변환 및 통합 시작...")

for file in file_list:
    try:
        # 파일 읽기
        try:
            df = pd.read_csv(file, encoding='cp949')
        except:
            df = pd.read_csv(file, encoding='utf-8')

        # '구간' 같은 불필요한 컬럼 삭제 (첫 번째 컬럼이 구간일 수 있음)
        if '구간' in df.columns:
            df = df.drop(columns=['구간'])

        # 가로(날짜) -> 세로(행) 변환 (Melt)
        # '시간' 또는 'hour' 컬럼을 기준으로 녹임
        id_vars = [col for col in df.columns if '시간' in col or 'hour' in col]
        if not id_vars: continue # 시간 컬럼 없으면 패스
        
        df_melted = df.melt(id_vars=id_vars, var_name='date', value_name='speed')
        
        # 컬럼명 통일 ('시간' -> 'hour')
        df_melted.rename(columns={id_vars[0]: 'hour'}, inplace=True)

        all_data.append(df_melted)
        print(f"  - {os.path.basename(file)} 처리 완료")

    except Exception as e:
        print(f"⚠️ {file} 에러: {e}")

# 2. 전체 병합
if all_data:
    final_df = pd.concat(all_data, ignore_index=True)

    # 3. 데이터 클리닝
    # '00시' -> 0
    final_df['hour'] = final_df['hour'].astype(str).str.replace('시', '').astype(int)
    
    # '100.5 km/h' -> 100
    final_df['speed'] = final_df['speed'].astype(str).str.replace(' km/h', '').str.replace(',', '')
    final_df['speed'] = pd.to_numeric(final_df['speed'], errors='coerce').fillna(0).astype(int)

    # 날짜 포맷 통일 (2025.08.01 -> 2025-08-01)
    final_df['date'] = final_df['date'].str.replace('.', '-')
    
    # 요일 추가 (0:월 ~ 6:일)
    final_df['day'] = pd.to_datetime(final_df['date'], errors='coerce').dt.dayofweek
    
    # 날짜 에러난 행 제거
    final_df = final_df.dropna(subset=['day'])
    final_df['day'] = final_df['day'].astype(int)

    # 4. 정렬 및 저장
    final_df = final_df.sort_values(by=['date', 'hour'])
    final_df = final_df[['date', 'day', 'hour', 'speed']] # 컬럼 순서 정리
    
    final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"🎉 성공! 3개월치 데이터가 '{output_file}'로 통합되었습니다.")
    print(f"📊 총 데이터 개수: {len(final_df)}개")
else:
    print("❌ 변환할 데이터가 없습니다.")