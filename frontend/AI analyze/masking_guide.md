# 이미지 마스킹 & 저장 역할 분리 가이드

---

## 전체 흐름

```
[사용자 폰]                [프론트엔드]              [백엔드]              [Supabase Storage]
    │                          │                        │                        │
    │  이미지 선택              │                        │                        │
    │ ─────────────────────>  │                        │                        │
    │                          │ 1. EXIF 제거           │                        │
    │                          │ 2. 얼굴 외 마스킹       │                        │
    │                          │ 3. 클린 이미지 생성     │                        │
    │                          │ ──────────────────>   │                        │
    │                          │   전처리된 이미지 전송   │                        │
    │                          │                        │ 4. 2차 EXIF 검증       │
    │                          │                        │ 5. 파일 검증           │
    │                          │                        │ 6. Supabase 업로드     │
    │                          │                        │ ─────────────────>    │
    │                          │                        │   저장 완료 URL 반환   │
    │                          │  저장된 이미지 URL 반환 │ <─────────────────    │
    │                          │ <──────────────────   │                        │
    │  분석 결과 표시           │                        │                        │
    │ <─────────────────────  │                        │                        │
```

---

## 프론트엔드가 할 일

### 1. EXIF 메타데이터 제거
Canvas API로 이미지를 다시 그려서 순수 PNG로 변환 → EXIF 자동 제거

```javascript
async function stripExif(file) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      canvas.getContext('2d').drawImage(img, 0, 0);
      canvas.toBlob((blob) => resolve(blob), 'image/png');
      URL.revokeObjectURL(img.src);
    };
    img.src = URL.createObjectURL(file);
  });
}
```

**제거되는 정보:** GPS 위치, 촬영 기기, 촬영 날짜/시간, 환자 병원 정보 등

---

### 2. 식별 영역 마스킹 (블랙박스)
안면부 질환 부위를 제외한 식별 가능 영역을 마스킹

```javascript
function maskIdentityArea(canvas) {
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;

  // 상단 라벨 영역 마스킹 (병원명, 환자명 등)
  ctx.fillStyle = '#000000';
  ctx.fillRect(0, 0, w, Math.floor(h * 0.08));

  // 하단 라벨 영역 마스킹
  ctx.fillRect(0, Math.floor(h * 0.92), w, Math.floor(h * 0.08));

  // 좌우 여백 마스킹 (추후 조정 가능)
  // ctx.fillRect(0, 0, Math.floor(w * 0.05), h);
  // ctx.fillRect(Math.floor(w * 0.95), 0, Math.floor(w * 0.05), h);
}
```

> **주의:** 눈, 코, 입 등 안면 식별 마스킹은 백엔드에서 처리 (프론트에서는 좌표를 알 수 없음)

---

### 3. 서버로 전송 (multipart/form-data)

```javascript
async function uploadImage(cleanBlob) {
  const formData = new FormData();
  formData.append('image', cleanBlob, 'skin_image.png');
  formData.append('userId', currentUser.id);
  formData.append('timestamp', Date.now());

  const res = await fetch('https://yourdomain.com/api/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userToken}`  // JWT 인증
    },
    body: formData
  });

  const data = await res.json();
  return data.imageUrl;  // 저장된 이미지 URL 반환받음
}
```

---

### 프론트 체크리스트

- [x] EXIF 메타데이터 제거 (Canvas API)
- [x] 상하단 라벨 영역 블랙 마스킹
- [x] PNG 변환 (무손실, 메타데이터 없음)
- [ ] JWT 토큰 헤더에 포함해서 전송
- [ ] 업로드 진행률 UI (progress bar)
- [ ] 실패 시 재시도 로직

---

## 백엔드가 할 일

### 1. 2차 EXIF 검증
프론트에서 제거했더라도 백엔드에서 한 번 더 검증

```python
# Python 예시 (FastAPI + Pillow)
from PIL import Image
import piexif

def strip_exif(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    # EXIF 완전 제거
    data = list(img.getdata())
    clean_img = Image.new(img.mode, img.size)
    clean_img.putdata(data)
    return clean_img
```

---

### 2. 파일 검증

```python
ALLOWED_TYPES = ['image/png', 'image/jpeg']
MAX_SIZE_MB = 10

def validate_image(file):
    # 파일 타입 검증
    if file.content_type not in ALLOWED_TYPES:
        raise ValueError("허용되지 않는 파일 형식")
    
    # 파일 크기 검증
    if file.size > MAX_SIZE_MB * 1024 * 1024:
        raise ValueError("파일 크기 초과")
    
    # 실제 이미지인지 확인 (매직 바이트)
    header = file.read(8)
    if not is_valid_image(header):
        raise ValueError("유효하지 않은 이미지")
```

---

### 3. 안면 식별 영역 마스킹 (핵심)
백엔드에서 AI 모델로 눈/코/입 좌표 탐지 후 마스킹

```python
# OpenCV + face_recognition 예시
import cv2
import face_recognition

def mask_facial_features(image_array):
    # 안면 랜드마크 탐지
    landmarks = face_recognition.face_landmarks(image_array)
    
    for face in landmarks:
        # 눈 마스킹
        for eye in ['left_eye', 'right_eye']:
            pts = np.array(face[eye], np.int32)
            cv2.fillPoly(image_array, [pts], (0, 0, 0))
        
        # 코 마스킹 (선택사항 — 질환 부위일 수 있으므로 팀 논의 필요)
        # nose_pts = np.array(face['nose_tip'], np.int32)
        # cv2.fillPoly(image_array, [nose_pts], (0, 0, 0))
    
    return image_array
```

> **팀 논의 필요:** 코/입 주변은 피부 질환 부위일 수 있어서 마스킹 범위를 의료팀과 협의해야 해요

---

### 4. Supabase Storage 업로드

```python
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_to_supabase(clean_image_bytes, user_id):
    # 파일명: 사용자ID + 타임스탬프 (개인정보 없는 랜덤 파일명)
    filename = f"{user_id}/{uuid.uuid4()}.png"
    
    res = supabase.storage.from_('skin-images').upload(
        path=filename,
        file=clean_image_bytes,
        file_options={"content-type": "image/png"}
    )
    
    # 공개 URL 반환
    url = supabase.storage.from_('skin-images').get_public_url(filename)
    return url
```

---

### 5. DB에 메타데이터 저장

```python
# Supabase DB에 이미지 기록 저장
def save_record(user_id, image_url):
    supabase.table('analysis_records').insert({
        'user_id': user_id,
        'image_url': image_url,
        'created_at': datetime.utcnow().isoformat(),
        'status': 'pending'  # AI 분석 대기 상태
    }).execute()
```

---

### 백엔드 체크리스트

- [ ] 2차 EXIF 완전 제거
- [ ] 파일 타입 / 크기 / 무결성 검증
- [ ] 안면 랜드마크 탐지 후 식별 영역 마스킹
- [ ] 마스킹 범위 의료팀과 협의
- [ ] Supabase Storage 업로드
- [ ] DB에 분석 기록 저장
- [ ] JWT 인증 미들웨어
- [ ] 업로드 실패 시 에러 핸들링

---

## 역할 요약

| 작업 | 담당 | 이유 |
|------|------|------|
| EXIF 메타데이터 제거 | **프론트** | Canvas API로 충분, 서버 부하 감소 |
| 상하단 라벨 마스킹 | **프론트** | 즉각적인 UI 피드백 가능 |
| 2차 EXIF 검증 | **백엔드** | 프론트 우회 가능성 차단 |
| 파일 유효성 검증 | **백엔드** | 보안상 서버에서 반드시 검증 |
| 안면 식별 마스킹 (눈 등) | **백엔드** | AI 모델 필요, 좌표 계산 서버에서 |
| Supabase 업로드 | **백엔드** | API 키 노출 방지 |
| DB 기록 저장 | **백엔드** | 데이터 무결성 |
