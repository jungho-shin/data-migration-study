# NYC Taxi Data Collector

뉴욕 택시 운행 데이터를 수집하는 서비스입니다. NYC TLC (Taxi and Limousine Commission)에서 제공하는 공개 데이터를 CSV 형식으로 다운로드합니다.

## 기능

- **다양한 택시 타입 지원**: Yellow Taxi, Green Taxi, For-Hire Vehicle (FHV), High Volume For-Hire Vehicle (FHVHV)
- **기간 지정**: 연도와 월을 지정하여 특정 기간의 데이터 수집
- **크기 제한**: 최대 수집 크기를 지정하여 디스크 공간 관리
- **자동 변환**: Parquet 형식의 데이터를 자동으로 CSV로 변환
- **중복 방지**: 이미 다운로드된 파일은 건너뜀
- **웹 인터페이스**: 브라우저를 통한 쉬운 데이터 수집 관리
- **REST API**: 프로그래밍 방식으로 데이터 수집 제어

## 요구사항

- Python 3.8 이상
- 인터넷 연결 (데이터 다운로드용)

## 설치

```bash
pip install -r requirements.txt
```

## 사용 방법

### 🌐 웹서비스 사용 (권장)

#### 1. Docker를 사용한 실행

```bash
# Docker Compose로 실행
docker-compose up -d

# 또는 Docker로 직접 실행
docker build -t nyc-taxi-collector .
docker run -d -p 8000:8000 -v $(pwd)/data:/app/data nyc-taxi-collector
```

#### 2. 로컬에서 직접 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 웹서비스 시작
python app.py

# 또는 uvicorn으로 직접 실행
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. 웹 인터페이스 접속

브라우저에서 `http://localhost:8000` 접속

- **웹 UI**: 폼을 통해 데이터 수집 작업 시작 및 모니터링
- **API 문서**: `http://localhost:8000/docs` (Swagger UI)
- **대체 문서**: `http://localhost:8000/redoc` (ReDoc)

#### 4. REST API 사용 예시

```bash
# 데이터 수집 작업 시작
curl -X POST "http://localhost:8000/api/collect" \
  -H "Content-Type: application/json" \
  -d '{
    "taxi_type": "yellow",
    "start_year": 2023,
    "start_month": 1,
    "end_year": 2023,
    "end_month": 3,
    "max_size_gb": 5.0
  }'

# 작업 목록 조회
curl http://localhost:8000/api/jobs

# 특정 작업 상태 조회
curl http://localhost:8000/api/jobs/{job_id}

# 수집된 파일 목록 조회
curl http://localhost:8000/api/files

# 헬스 체크
curl http://localhost:8000/health
```

### 📝 명령줄 사용 (CLI)

### 기본 사용 (Yellow Taxi, 2023년 1월 데이터)

```bash
python data_collector.py
```

### 옵션 지정

```bash
# Green Taxi 데이터 수집
python data_collector.py --taxi-type green

# 특정 기간 지정 (2023년 1월 ~ 3월)
python data_collector.py --start-year 2023 --start-month 1 --end-year 2023 --end-month 3

# 최대 크기 제한 (5GB)
python data_collector.py --max-size-gb 5

# 최대 파일 수 제한 (3개)
python data_collector.py --max-files 3

# 출력 디렉토리 지정
python data_collector.py --output-dir /path/to/data
```

### 전체 옵션 예시

```bash
python data_collector.py \
    --taxi-type yellow \
    --start-year 2023 \
    --start-month 1 \
    --end-year 2023 \
    --end-month 6 \
    --max-size-gb 20 \
    --output-dir ./data
```

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/` | 웹 인터페이스 |
| POST | `/api/collect` | 데이터 수집 작업 시작 |
| GET | `/api/jobs` | 모든 작업 목록 조회 |
| GET | `/api/jobs/{job_id}` | 특정 작업 상태 조회 |
| DELETE | `/api/jobs/{job_id}` | 작업 삭제 |
| GET | `/api/files` | 수집된 파일 목록 조회 |
| GET | `/health` | 헬스 체크 |
| GET | `/docs` | Swagger API 문서 |
| GET | `/redoc` | ReDoc API 문서 |

## 명령줄 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--taxi-type` | 택시 타입 (yellow, green, fhv, fhvhv) | yellow |
| `--start-year` | 시작 연도 | 2023 |
| `--start-month` | 시작 월 | 1 |
| `--end-year` | 종료 연도 | 현재 연도 |
| `--end-month` | 종료 월 | 현재 월 |
| `--max-size-gb` | 최대 수집 크기 (GB) | 10.0 |
| `--max-files` | 최대 파일 수 | 제한 없음 |
| `--output-dir` | 출력 디렉토리 | ./data |

## 데이터 형식

### 택시 타입

- **yellow**: Yellow Taxi (일반 택시)
- **green**: Green Taxi (보로 택시)
- **fhv**: For-Hire Vehicle (전세 차량)
- **fhvhv**: High Volume For-Hire Vehicle (대량 전세 차량)

### 파일 형식

- **2022년 이전**: CSV 형식으로 제공
- **2022년 이후**: Parquet 형식으로 제공 (자동으로 CSV로 변환)

### 데이터 크기

각 파일의 크기는 다음과 같습니다:

- **Yellow Taxi**: 월별 약 200MB ~ 1GB
- **Green Taxi**: 월별 약 50MB ~ 200MB
- **FHV/FHVHV**: 월별 약 100MB ~ 500MB

## 출력 구조

```
data/
├── yellow_tripdata_2023-01.csv
├── yellow_tripdata_2023-02.csv
├── green_tripdata_2023-01.csv
└── ...
```

## 데이터 스키마

### Yellow/Green Taxi 데이터 컬럼

- `VendorID`: 벤더 ID
- `tpep_pickup_datetime`: 픽업 시간
- `tpep_dropoff_datetime`: 하차 시간
- `passenger_count`: 승객 수
- `trip_distance`: 이동 거리
- `RatecodeID`: 요금 코드
- `store_and_fwd_flag`: 저장 및 전달 플래그
- `PULocationID`: 픽업 위치 ID
- `DOLocationID`: 하차 위치 ID
- `payment_type`: 결제 유형
- `fare_amount`: 기본 요금
- `extra`: 추가 요금
- `mta_tax`: MTA 세금
- `tip_amount`: 팁
- `tolls_amount`: 통행료
- `improvement_surcharge`: 개선 부과금
- `total_amount`: 총 금액
- `congestion_surcharge`: 혼잡 부과금
- `airport_fee`: 공항 요금

### FHV/FHVHV 데이터 컬럼

- `dispatching_base_num`: 배차 기지 번호
- `pickup_datetime`: 픽업 시간
- `dropoff_datetime`: 하차 시간
- `PULocationID`: 픽업 위치 ID
- `DOLocationID`: 하차 위치 ID
- `SR_Flag`: 공유 승차 플래그 (FHVHV만)

## 예제

### 1. 최근 3개월 Yellow Taxi 데이터 수집 (최대 5GB)

```bash
python data_collector.py \
    --taxi-type yellow \
    --start-month 10 \
    --end-month 12 \
    --max-size-gb 5
```

### 2. 2022년 전체 Green Taxi 데이터 수집

```bash
python data_collector.py \
    --taxi-type green \
    --start-year 2022 \
    --start-month 1 \
    --end-year 2022 \
    --end-month 12
```

### 3. 최근 1개월 데이터만 수집 (테스트용)

```bash
python data_collector.py \
    --start-month 12 \
    --end-month 12 \
    --max-files 1
```

## 주의사항

1. **인터넷 연결**: 대용량 데이터를 다운로드하므로 안정적인 인터넷 연결이 필요합니다.
2. **디스크 공간**: 데이터 파일은 매우 큽니다. 충분한 디스크 공간을 확보하세요.
3. **다운로드 시간**: 파일 크기에 따라 다운로드에 시간이 걸릴 수 있습니다.
4. **서버 부하**: 다운로드 간 1초 대기 시간을 두어 서버 부하를 방지합니다.

## 문제 해결

### Parquet 변환 오류

Parquet 파일을 CSV로 변환하려면 `pandas`와 `pyarrow`가 필요합니다:

```bash
pip install pandas pyarrow
```

### 파일을 찾을 수 없음

일부 오래된 데이터는 더 이상 제공되지 않을 수 있습니다. 최근 데이터부터 시작하는 것을 권장합니다.

### 메모리 부족

대용량 파일을 처리할 때 메모리 부족이 발생할 수 있습니다. 이 경우 더 작은 기간으로 나누어 수집하세요.

## 참고 자료

- [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
- [데이터 사양 문서](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf)

## 라이선스

이 도구는 NYC TLC에서 제공하는 공개 데이터를 사용합니다. 데이터 사용 시 NYC TLC의 이용 약관을 준수해야 합니다.
