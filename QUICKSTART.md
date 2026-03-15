# SonoCube PoC 빠른 시작 가이드

## 실행 방법

### 1. 의존성 설치 (최초 1회)

터미널에서 프로젝트 루트 디렉토리로 이동 후:

```bash
cd /Users/ohseoyoung/sonocube-poc
pip3 install -r sonocube_poc/requirements.txt
```

또는 가상환경 사용 (권장):

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install -r sonocube_poc/requirements.txt
```

### 2. 애플리케이션 실행

#### 방법 A: 스크립트 사용 (가장 간단)

```bash
./run.sh
```

#### 방법 B: 직접 실행

```bash
cd sonocube_poc
python3 main.py
```

#### 방법 C: 모듈로 실행

```bash
python3 -m sonocube_poc.main
```

### 3. 사용 방법

1. **파일 열기**
   - "Open File" 버튼 클릭
   - 또는 `Cmd+O` (macOS)
   - 또는 파일을 창에 드래그 앤 드롭

2. **분석 시작**
   - "Start Analysis" 버튼 클릭
   - 또는 `Cmd+R`

3. **결과 확인**
   - 좌측: 2D 슬라이스 뷰어 (슬라이더로 프레임 탐색)
   - 우측: 3D 뷰어 (현재는 플레이스홀더)
   - 우측 패널: 분석 결과 메트릭

4. **리포트 생성**
   - "Generate Report" 버튼 클릭
   - 또는 `Cmd+P`

### 4. 지원 파일 형식

- **비디오**: MP4, AVI, MOV, MKV
- **DICOM**: .dcm, .dicom

### 5. 문제 해결

#### 의존성 오류가 발생하는 경우

```bash
# PyQt5 재설치
pip3 install --upgrade PyQt5 PyQt5-Qt5 PyQt5-sip

# 기타 의존성 재설치
pip3 install --upgrade -r sonocube_poc/requirements.txt
```

#### 모듈을 찾을 수 없는 경우

```bash
# 프로젝트 루트에서 실행
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python3 sonocube_poc/main.py
```

### 6. macOS 앱으로 패키징

```bash
cd packaging
pyinstaller sonocube_mac.spec
```

생성된 앱: `dist/SonoCube.app`

