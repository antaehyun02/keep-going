# merge_data.py (3개월치 파일 합치기)
import pandas as pd
import glob
import os

# 1. data 폴더에 있는 모든 csv 파일 찾기
all_files = glob.glob("./data/data_*.csv")

if not all_files:
    print("❌ CSV 파일이 없습니다. data 폴더에 파일을 넣어주세요.")
    exit()

print(f"📂 발견된 파일: {all_files}")

# 2. 파일 하나씩 읽어서 리스트에 담기
df_list = []
for filename in all_files:
    try:
        # 엑셀에서 저장할 때 인코딩이 cp949(한글)인 경우가 많음
        df = pd.read_csv(filename, encoding='cp949')
        df_list.append(df)
    except:
        df = pd.read_csv(filename, encoding='utf-8')
        df_list.append(df)

# 3. 위아래로 합치기 (Concat)
# axis=1 (옆으로) 아님, axis=0 (위아래로)인데 데이터 구조가 가로형이라
# 일단 하나로 합친 뒤 전처리해야 함. 하지만 님 데이터는 날짜가 옆으로 늘어난 구조라
# 그냥 전처리 로직을 먼저 돌리고 합치는 게 낫습니다.

print("✅ 파일 병합 로직 대신, 'preprocess.py'에서 한 번에 처리하겠습니다.")