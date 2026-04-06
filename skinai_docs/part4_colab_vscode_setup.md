# Part 4 — VSCode + Colab Pro 연동 가이드 (cloudflared SSH)

Colab Pro GPU 환경에 VSCode Remote SSH로 직접 연결해 로컬처럼 터미널·파일탐색기·디버거를 사용하는 방법.

---

## 0. 사전 준비 (로컬 Mac — 최초 1회)

### 필수 설치

```bash
# Remote - SSH 확장 설치 (VSCode)
# VSCode 확장 탭에서 "Remote - SSH" (ms-vscode-remote.remote-ssh) 설치

# cloudflared CLI
brew install cloudflare/cloudflare/cloudflared

# 설치 확인
cloudflared --version
```

### SSH 키 생성

```bash
# Colab 전용 키 생성
ssh-keygen -t ed25519 -C "colab" -f ~/.ssh/colab_key

# 공개 키 확인 (Colab 셀에 붙여넣을 값)
cat ~/.ssh/colab_key.pub
```

---

## 1. Colab 노트북 설정 (매 세션마다 순서대로 실행)

### 셀 1 — Google Drive 마운트

```python
from google.colab import drive
drive.mount('/content/drive')
```

### 셀 2 — SSH 서버 설치 + 키 인증 설정

```bash
%%bash
# 0. SSH 서버 및 폴더 준비
apt-get install -y openssh-server -q
mkdir -p /root/.ssh

# 1. 모든 팀원의 공개키(Public Key)를 한 곳에 모아 등록
# 기존 내용을 덮어쓰지 않고 추가(>>) 하거나, 아래처럼 한 번에 등록합니다.
cat <<EOF > /root/.ssh/authorized_keys
ssh-ed25519 AAAAC3...[kyoe님의 공개키]... colab
ssh-ed25519 AAAAC3...[팀원A의 공개키]... colab
ssh-ed25519 AAAAC3...[팀원B의 공개키]... colab
EOF

# 2. 권한 및 서버 설정
chmod 700 /root/.ssh
chmod 600 /root/.ssh/authorized_keys
chown -R root:root /root/.ssh
echo "PermitRootLogin yes" >> /etc/ssh/sshd_config

service ssh restart
echo "✅ 모든 팀원의 자물쇠 등록 및 SSH 서버 시작 완료"
```

### 셀 3 — cloudflared 설치

```bash
%%bash
curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
cloudflared --version
echo "✅ cloudflared 설치 완료"
```

### 셀 4 — 터널 실행 및 URL 출력 (실행 중 유지 필요)

```python
import subprocess, threading, time, re

LOG = "/tmp/cf_tunnel.log"

def run_tunnel():
    with open(LOG, "w") as f:
        subprocess.run(
            ["/usr/local/bin/cloudflared", "tunnel",
             "--url", "ssh://localhost:22"],
            stdout=f, stderr=f,
        )

# 터널 실행
threading.Thread(target=run_tunnel, daemon=True).start()
time.sleep(5)

with open(LOG) as f:
    content = f.read()

match = re.search(r'https://[a-z0-9\-]+\.trycloudflare\.com', content)
if match:
    hostname = match.group().replace("https://", "")
    print(f"✅ 터널 연결됨 (이 셀을 정지시키지 마세요!)\n")
    print(f"~/.ssh/config 의 HostName을 아래 주소로 업데이트하세요:")
    print(f"👉 {hostname}")

    # 셀이 종료되지 않도록 무한 대기
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n정지됨")
else:
    print("❌ 주소 생성 실패. 로그:")
    print(content[-500:])
```

> ⚠️ 이 셀이 종료되면 터널이 끊김 — 학습 중 실행 상태 유지 필수.

---

## 2. 로컬 Mac SSH 설정

### `~/.ssh/config` 업데이트

셀 4 출력값을 복사해 `~/.ssh/config`에 붙여넣는다.

```
Host colab
    HostName abc-def-123.trycloudflare.com   # ← 셀 4 출력값 (세션마다 변경)
    User root
    IdentityFile ~/.ssh/colab_key
    ProxyCommand cloudflared access ssh --hostname %h
    StrictHostKeyChecking no
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

### 연결 테스트

```bash
ssh colab "nvidia-smi && echo '✅ GPU 확인 완료'"
```

정상 출력 예:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 525.xx     Driver Version: 525.xx    CUDA Version: 12.0         |
+-----------------------------------------------------------------------------+
| GPU  0  Tesla T4      ...                                                   |
✅ GPU 확인 완료
```

---

## 3. VSCode Remote SSH 연결

1. `Ctrl+Shift+P` → `Remote-SSH: Connect to Host`
2. `colab` 선택
3. 새 VSCode 창 열림 → 플랫폼 선택: `Linux`
4. VSCode Server 자동 설치 (~1분)
5. 연결 완료 — 좌하단에 `SSH: colab` 표시

**폴더 열기**: `File → Open Folder → /content/skin_ai`

---

## 4. 프로젝트 환경 셋업 (VSCode 터미널)

### 셀 5 — 프로젝트 복사 + 패키지 설치

VSCode 통합 터미널 또는 Colab 셀에서:

```bash
# Drive → 로컬 디스크 복사 (Drive FUSE 병목 제거, ~5분 소요)
cp -r /content/drive/MyDrive/skin_ai /content/skin_ai

# 이동 후 패키지 설치
cd /content/skin_ai
pip install torch torchvision pandas tqdm Pillow \
    matplotlib seaborn scikit-learn python-dotenv -q

echo "✅ 환경 셋업 완료"
```

### GPU 확인

```python
import torch
print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
```

### 디스크 확인

```bash
df -h /content
# Colab Pro 기준 ~225GB 사용 가능
```

---

## 5. 학습 실행 (VSCode 터미널)

```bash
cd /content/skin_ai

# DenseNet121 (기본)
python -m ai.training.classifier.train \
    --root_dir /content/skin_ai

# EfficientNet-B3
python -m ai.training.classifier.train \
    --backbone efficientnet_b3 \
    --root_dir /content/skin_ai

# 세션 만료 후 재개
python -m ai.training.classifier.train \
    --root_dir /content/skin_ai \
    --resume ai/checkpoints/aihub/best.pth
```

---

## 6. 체크포인트 Drive 동기화

학습 완료 후 또는 세션 종료 전:

```bash
# VSCode 터미널에서
cp -r /content/skin_ai/ai/checkpoints \
      /content/drive/MyDrive/skin_ai/ai/
echo "✅ 체크포인트 Drive 저장 완료"
```

또는 Python:

```python
import shutil
shutil.copytree(
    "/content/skin_ai/ai/checkpoints",
    "/content/drive/MyDrive/skin_ai/ai/checkpoints",
    dirs_exist_ok=True,
)
```

---

## 7. 세션 만료 후 재개 절차

| 순서 | 작업 |
|------|------|
| 1 | Colab 셀 1 재실행 (Drive 마운트) |
| 2 | 셀 2 재실행 (SSH 서버 + 키 설정) |
| 3 | 셀 3 재실행 (cloudflared, 이미 설치됐으면 생략) |
| 4 | 셀 4 재실행 → 새 터널 URL 확인 |
| 5 | `~/.ssh/config`의 `HostName`을 새 URL로 업데이트 |
| 6 | VSCode `Remote-SSH: Connect to Host` → `colab` |
| 7 | 셀 5 재실행 (프로젝트 복사 + 패키지 설치) |
| 8 | `--resume best.pth` 로 학습 재개 |

> 체크포인트를 Drive에 저장해뒀다면 7 완료 후 Drive에서 복사:
> ```bash
> cp -r /content/drive/MyDrive/skin_ai/ai/checkpoints \
>        /content/skin_ai/ai/
> ```

---

## 8. 팁 및 주의사항

| 항목 | 내용 |
|------|------|
| 터널 URL | 세션마다 변경 → `~/.ssh/config` 매번 업데이트 필요 |
| 셀 4 유지 | 터널 실행 셀이 종료되면 SSH 연결 끊김 |
| 비활성 만료 | Colab Pro는 표준보다 길지만 브라우저 탭 유지 권장 |
| 키 인증 | 비밀번호 대신 SSH 키 사용 — 보안 및 편의성 ↑ |
| 자동완성 | VSCode Python 확장 설치 후 Colab VM에서 IntelliSense 동작 |
| 파일 탐색 | VSCode 탐색기에서 `/content/skin_ai` 파일 직접 편집 가능 |
