# 자산 고갈 시뮬레이터 v2

## 기능

### 분석
- **간단/상세 모드** — 3개 항목 빠른 분석 또는 자산별·비용별 상세 분석
- **물가상승률 차등** — 변동비 100%, 고정비 50% 반영
- **동연령 평균 비교** — 2025 가계금융복지조사 기반
- **시나리오 비교** — 현재 계획 vs 저축 강화 vs 은퇴 연장
- **민감도 분석** — 낙관/기본/비관 3가지 경제 시나리오
- **FIRE 지표** — 경제적 자립까지 남은 연수
- **안전 인출액** — 은퇴 후 월 안전 인출 가능 금액

### UX
- **주간/야간 모드** — 우상단 토글
- **프리셋** — 30대 직장인, 40대 맞벌이, 50대 은퇴준비
- **공유 링크** — 입력값을 URL로 인코딩하여 공유
- **금액 한글 표시** — 입력 시 "💰 3억원" 자동 표시
- **모바일 최적화** — 터치 영역, 세로 스택, 차트 최적화

### 저장 & 보고서
- **Google Sheets 자동 저장** — 분석 버튼 클릭 시 전체 기록
- **PDF 보고서** — 차트 이미지 + 테이블 포함
- **CSV 다운로드** — 전체 시뮬레이션 데이터

## 설치

```bash
pip install -r requirements.txt
streamlit run app.py
```

> PDF 차트 이미지에 kaleido 필요: `pip install kaleido`

## Google Sheets 설정

1. Google Cloud Console → 프로젝트 생성
2. Google Sheets API + Google Drive API 활성화
3. 서비스 계정 → JSON 키 다운로드
4. Google Sheets "자산 시뮬레이션 기록" 생성 → 서비스 계정 이메일 공유
5. `.streamlit/secrets.toml` 작성 (secrets.toml.example 참고)

## 배포 (Streamlit Cloud)

1. GitHub push → share.streamlit.io 연결
2. Secrets에 toml 내용 붙여넣기 → Deploy
3. 폰: URL 열기 → 홈 화면에 추가

## 파일 구조

```
├── app.py              # 메인 앱
├── engine.py           # 시뮬레이션 엔진
├── charts.py           # 차트 생성
├── report_pdf.py       # PDF 보고서
├── gsheet.py           # Google Sheets 연동
├── theme.py            # 주간/야간 테마
├── requirements.txt
├── secrets.toml.example
├── README.md
└── .streamlit/config.toml
```
