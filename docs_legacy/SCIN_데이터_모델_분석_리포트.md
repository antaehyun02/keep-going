# SCIN 데이터셋 분석 리포트: Train vs Test 비교

## 데이터 기본 정보

### 데이터 크기
- **Train 데이터**: 2,039개 샘플 (82.3%)
- **Test 데이터**: 438개 샘플 (17.7%)
- **비율**: 4.7:1 (Train:Test)

### 파일 구조
- **컬럼 수**: 73개 (두 파일 동일)
- **주요 카테고리**:
  - 인구통계 정보 (나이, 성별, 인종, 피부 타입 등)
  - 질병 증상 (texture, body parts, condition symptoms 등)
  - 이미지 정보 (최대 3장, 촬영 타입 포함)
  - 전문의 라벨 (피부 질환명, 신뢰도, Fitzpatrick/Monk 피부 타입 등)

---

## 발견된 주요 이슈

### 1. 클래스 불균형 문제 (Critical)

**Train에만 존재하는 질병: 154개**
- 예시: 'Acanthosis nigricans', 'Acne keloidalis', 'Acquired digital fibrokeratoma' 등
- **영향**: Test 데이터에서 이 154개 질병에 대한 모델 성능 평가 불가능

**Test에만 존재하는 질병: 35개**
- 예시: 'Acral erythema', 'Angiosarcoma of skin', 'Blister', 'Chicken pox exanthem' 등
- **영향**: 모델이 학습하지 못한 질병이므로 예측 불가능 (Zero-shot learning 필요)

**총 고유 질병 수**:
- Train: 267개
- Test: 148개
- 공통: 113개 (Train의 42.3%, Test의 76.4%)

### 2. 심각한 결측값 문제 (Critical)

**Train 데이터 결측률 Top 5**:
1. `race_ethnicity_native_hawaiian_or_pacific_islander`: 100.0%
2. `race_ethnicity_middle_eastern_or_north_african`: 99.8%
3. `race_ethnicity_other_race`: 99.7%
4. `race_ethnicity_prefer_not_to_answer`: 99.4%
5. `other_symptoms_fever`: 98.4%

**Test 데이터 결측률 Top 5**:
1. `race_ethnicity_native_hawaiian_or_pacific_islander`: 100.0%
2. `race_ethnicity_middle_eastern_or_north_african`: 99.8%
3. `race_ethnicity_other_race`: 99.5%
4. `race_ethnicity_prefer_not_to_answer`: 99.1%
5. `race_ethnicity_american_indian_or_alaska_native`: 98.2%

**영향**:
- 특정 인종/민족 그룹에 대한 모델 편향 가능성
- 일부 증상 feature 활용 불가능
- Fairness/Bias 분석 시 주의 필요

### 3. Train/Test 분할 비율 이슈 (Warning)

- **현재 비율**: 82.3% / 17.7% (약 4.7:1)
- **일반적 권장**: 80% / 20% 또는 70% / 30%
- **영향**: Test 데이터가 다소 부족하여 일반화 성능 평가에 제한적

### 4. 인구통계 정보 부족 (Warning)

**성별 분포**:
- Train: `OTHER_OR_UNSPECIFIED` 959명 (47.0%), `FEMALE` 698명, `MALE` 382명
- Test: `OTHER_OR_UNSPECIFIED` 210명 (47.9%), `FEMALE` 161명, `MALE` 67명

**나이대 분포**:
- Train: `AGE_UNKNOWN` 1,109명 (54.4%)
- Test: `AGE_UNKNOWN` 237명 (54.1%)

**영향**:
- 성별/나이별 성능 분석 어려움
- 특정 그룹에 대한 모델 편향 가능성

### 5. 이미지 수 불균형 (Minor)

**Train 데이터**:
- 1장: 716개 (35.1%)
- 2장: 342개 (16.8%)
- 3장: 981개 (48.1%)

**Test 데이터**:
- 1장: 150개 (34.2%)
- 2장: 78개 (17.8%)
- 3장: 210개 (48.0%)

**영향**: 이미지 수에 따른 모델 성능 차이 가능성

---

## 질병 분포 분석

### Top 10 질병 (Train)
1. **Eczema**: 890건
2. **Allergic Contact Dermatitis**: 657건
3. **Insect Bite**: 317건
4. **Urticaria**: 275건
5. **Psoriasis**: 251건
6. **Folliculitis**: 210건
7. **Irritant Contact Dermatitis**: 193건
8. **Tinea**: 165건
9. **Drug Rash**: 108건
10. **Herpes Zoster**: 103건

### Top 10 질병 (Test)
1. **Eczema**: 155건
2. **Allergic Contact Dermatitis**: 147건
3. **Insect Bite**: 54건
4. **Folliculitis**: 50건
5. **Psoriasis**: 49건
6. **Urticaria**: 46건
7. **Tinea**: 37건
8. **Irritant Contact Dermatitis**: 30건
9. **Drug Rash**: 25건
10. **Herpes Zoster**: 23건

**관찰**:
- Train과 Test의 Top 10 질병이 동일함 (순서 일부 차이)
- Eczema와 Allergic Contact Dermatitis가 압도적으로 많음

---

## Fitzpatrick 피부 타입 분포

### Train 데이터
- FST1: 88개 (7.9%)
- FST2: 277개 (24.9%)
- FST3: 262개 (23.5%)
- FST4: 176개 (15.8%)
- FST5: 97개 (8.7%)
- FST6: 69개 (6.2%)
- NONE_IDENTIFIED: 142개 (12.8%)

### Test 데이터
- FST1: 23개 (9.9%)
- FST2: 54개 (23.3%)
- FST3: 54개 (23.3%)
- FST4: 34개 (14.7%)
- FST5: 20개 (8.6%)
- FST6: 19개 (8.2%)
- NONE_IDENTIFIED: 29개 (12.5%)

**관찰**: Train과 Test에서 비슷한 분포 유지

---

## 긍정적인 점

1. **컬럼 구조 일치**: Train과 Test가 동일한 73개 컬럼을 가짐
2. **라벨 완전성**: 모든 데이터(100%)에 라벨이 존재
3. **주요 질병 분포 유사**: Top 10 질병이 Train/Test에서 동일
4. **피부 타입 분포 유사**: Fitzpatrick 타입 비율이 비슷함

---

## 권장 사항

### 즉시 조치 필요 (High Priority)

1. **Zero-shot Learning 대비**
   - Test에만 있는 35개 질병 처리 전략 수립
   - Out-of-distribution (OOD) 감지 메커니즘 구현

2. **Class Imbalance 처리**
   - 소수 클래스에 대한 weighted loss 적용
   - Data augmentation 또는 oversampling 고려

3. **결측값 처리 전략**
   - 95% 이상 결측된 feature 제거 고려
   - 또는 "UNKNOWN" 카테고리로 명시적 처리

### 중기 개선 사항 (Medium Priority)

4. **데이터 수집 개선**
   - Train에만 있는 154개 질병에 대한 Test 샘플 추가 수집
   - 인구통계 정보(나이, 성별) 수집 강화

5. **Fairness 분석**
   - 피부 타입별 모델 성능 비교
   - 성별/나이별 편향 분석 (가능한 범위 내에서)

6. **Train/Test Split 재검토**
   - 80/20 또는 70/30 비율로 재분할 고려
   - Stratified split으로 질병 분포 균형 유지

### 장기 개선 사항 (Low Priority)

7. **Multi-modal Learning**
   - 1장/2장/3장 이미지 데이터에 대한 별도 학습 전략
   - 이미지 수에 따른 앙상블 기법 검토

8. **Feature Engineering**
   - 결측값이 적은 feature만 활용하는 모델 구축
   - 피부 타입, 증상 조합 등 파생 feature 생성

---

---

## 모델 성능 분석

### 현재 모델 (ResNet50)

**Overall Metrics**:
- Top-1 Accuracy: 22.1%
- Top-3 Accuracy: 50.2%
- Top-5 Accuracy: 64.8%
- **Overall F1-Score: 0.082** (매우 낮음)
- Overall Precision: 0.160
- Overall Recall: 0.067

**Per-Class 통계**:
- 총 50개 클래스 평가 (267개 중)
- F1 = 0인 클래스: **28/50 (56%)**
- F1 > 0인 클래스: 22/50 (44%)
- 평균 F1 (non-zero only): 0.186

### 심각한 역설 발견

**최다 샘플 클래스들의 F1 Score = 0**:
| 질병명 | Train 샘플 | Test 샘플 | F1 Score |
|--------|-----------|----------|----------|
| Eczema | 890 | 141 | **0.000** |
| Allergic Contact Dermatitis | 657 | 136 | **0.000** |
| Insect Bite | 317 | 49 | **0.000** |
| Psoriasis | 251 | 46 | **0.000** |
| Irritant Contact Dermatitis | 193 | 29 | **0.000** |
| Tinea | 165 | 34 | **0.000** |

**반대로 F1 > 0인 클래스들은 소수 샘플**:
| 질병명 | Train 샘플 (추정) | Test 샘플 | F1 Score |
|--------|-----------|----------|----------|
| SCC/SCCIS | 소수 | 9 | **0.400** |
| Acne | ~40 | 17 | **0.308** |
| Tinea Versicolor | 소수 | 8 | **0.308** |
| Viral Exanthem | 소수 | 9 | **0.250** |

---

## 근본 원인 분석

### 1. Threshold 문제 (Critical)

**모델 구조**:
- Multi-label classification (BCEWithLogitsLoss)
- `torch.sigmoid(outputs)` → 확률 변환
- **Threshold = 0.5 고정** ← 문제!

**증상**:
- Top-5 Accuracy는 64.8%로 준수 → 모델이 확률은 어느 정도 예측
- F1 Score는 0.082로 극히 낮음 → **Threshold 0.5로 positive 예측을 거의 못함**
- Recall = 0.067 → 실제 positive의 93%를 놓침

**원인**:
- **다수 클래스(Eczema, ACD 등)의 예측 확률이 모두 < 0.5**
- 모델이 확신 없는 예측을 하고 있음
- 소수 클래스는 우연히 > 0.5 넘어서 F1 > 0

### 2. Class Imbalance + Class Weights의 역효과

**학습 방식**:
- BCEWithLogitsLoss with `pos_weight` (클래스 가중치)
- 다수 클래스에 낮은 가중치, 소수 클래스에 높은 가중치 적용

**역효과**:
- 모델이 소수 클래스에 과적합
- 다수 클래스를 과소평가하여 확률을 낮게 예측
- **결과적으로 가장 많은 Eczema, ACD의 F1 = 0**

### 3. 클래스 간 유사성 문제

**유사한 질병들**:
- Eczema ↔ Allergic Contact Dermatitis
- Allergic Contact Dermatitis ↔ Irritant Contact Dermatitis
- Psoriasis ↔ Eczema

**영향**:
- 모델이 확신을 갖지 못해 낮은 확률 예측
- Threshold 0.5를 넘지 못함

### 4. Multi-label 특성 미반영

**데이터 특성**:
- `weighted_skin_condition_label` = `{'Eczema': 0.5, 'Allergic Contact Dermatitis': 0.5}`
- 하나의 샘플이 여러 질병을 가질 수 있음

**문제**:
- Threshold = 0.5는 단일 레이블 가정
- Multi-label에서는 **클래스별 최적 threshold가 다름**

---

## 요약

### Critical Issues

#### 데이터 이슈
- Train에만 154개, Test에만 35개 질병 존재 → **클래스 불일치**
- 인종/민족 필드 95% 이상 결측 → **Bias/Fairness 분석 제한**
- Train/Test 비율 82:18 → **일반적 권장과 다소 차이**

#### 모델/평가 이슈 (더 심각)
- **Threshold = 0.5 고정** → 다수 클래스 F1 = 0
- **Class weights 역효과** → 다수 클래스 과소평가
- **최다 샘플 6개 클래스 모두 F1 = 0** → 모델이 주요 질병 예측 실패
- Recall = 0.067 → 실제 positive의 93%를 놓침

### Action Items (우선순위 순)

#### Immediate (High Priority)
1. **Threshold 최적화**
   - Per-class optimal threshold 탐색 (Precision-Recall curve)
   - F1-optimal threshold 찾기
   - 또는 Top-K prediction 방식으로 변경

2. **Class Weights 재조정**
   - 현재 pos_weight 확인 및 분석
   - 다수 클래스에 충분한 가중치 부여
   - 또는 Focal Loss 시도

3. **Evaluation Metrics 재설계**
   - Multi-label에 적합한 메트릭 사용
   - Hamming Loss, Subset Accuracy 추가
   - Per-sample Top-K accuracy

#### Medium Priority
4. **Zero-shot Learning 대비**
   - Test에만 있는 35개 질병 처리 전략
   - OOD 감지 메커니즘

5. **Data Augmentation**
   - 다수 클래스의 변형 데이터 생성
   - MixUp, CutMix 등 적용

6. **결측값 처리**
   - 95% 이상 결측 필드 제거 또는 명시적 처리

#### Low Priority
7. **Train/Test Split 재검토**
   - Stratified split으로 재분할
   - 80/20 비율 고려

8. **Fairness 분석**
   - 피부 타입별 성능 비교

### Overall Assessment
- **데이터 품질**: 보통 (라벨은 완전하지만 feature 결측 많음)
- **Train/Test 일관성**: 양호 (주요 질병 분포 유사)
- **모델 학습**: **실패** (다수 클래스 F1 = 0, Threshold 문제)
- **모델 잠재력**: 양호 (Top-5 Acc 64.8% → 확률 예측은 어느 정도 가능)
- **우선 해결 과제**: **Threshold 최적화 & Class Weights 재조정**

### 예상 개선 효과
Threshold를 0.5 → 0.3으로 조정하거나 per-class optimal threshold를 적용하면:
- **F1 Score: 0.082 → 0.35~0.45** (4~5배 개선 예상)
- **Recall: 0.067 → 0.30~0.40** (4~6배 개선 예상)
- **Eczema/ACD F1: 0.00 → 0.20~0.40** (주요 질병 예측 가능)
