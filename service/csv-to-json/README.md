# CSV to JSON Converter

CSV 파일을 JSON 형식으로 변환하는 서비스입니다. `./service/data` 디렉토리의 CSV 파일을 읽어서 `./service/data_json` 디렉토리에 JSON 파일로 저장합니다.

## 기능

- **배치 변환**: 디렉토리 내 모든 CSV 파일을 한 번에 변환
- **단일 파일 변환**: 특정 파일만 선택하여 변환
- **다양한 JSON 형식**: Array 형식 또는 Objects 형식 선택
- **대용량 파일 지원**: 청크 단위로 분할하여 변환 가능
- **웹 인터페이스**: 브라우저를 통한 쉬운 변환 관리
- **REST API**: 프로그래밍 방식으로 변환 제어

## 요구사항

- Python 3.8 이상
- CSV 파일 (입력)

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
docker build -t csv-to-json .
docker run -d -p 8001:8001 \
  -v $(pwd)/../data:/app/data \
  -v $(pwd)/../data_json:/app/data_json \
  csv-to-json
```

#### 2. 로컬에서 직접 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 웹서비스 시작
python app.py

# 또는 uvicorn으로 직접 실행
uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

#### 3. 웹 인터페이스 접속

브라우저에서 `http://localhost:8001` 접속

- **웹 UI**: 폼을 통해 변환 작업 시작 및 모니터링
- **API 문서**: `http://localhost:8001/docs` (Swagger UI)
- **대체 문서**: `http://localhost:8001/redoc` (ReDoc)

#### 4. REST API 사용 예시

```bash
# 전체 파일 변환
curl -X POST "http://localhost:8001/api/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "format_type": "array"
  }'

# 특정 파일만 변환
curl -X POST "http://localhost:8001/api/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "file": "yellow_tripdata_2023-01.csv",
    "format_type": "array"
  }'

# 청크 단위로 변환 (10,000행씩)
curl -X POST "http://localhost:8001/api/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "format_type": "array",
    "chunk_size": 10000
  }'

# 작업 목록 조회
curl http://localhost:8001/api/jobs

# 파일 목록 조회
curl http://localhost:8001/api/files
```

### 📝 명령줄 사용 (CLI)

#### 기본 사용 (전체 파일 변환)

```bash
python csv_to_json.py
```

#### 옵션 지정

```bash
# 특정 파일만 변환
python csv_to_json.py --file yellow_tripdata_2023-01.csv

# JSON 형식 지정
python csv_to_json.py --format objects

# 청크 단위로 변환 (10,000행씩)
python csv_to_json.py --chunk-size 10000

# 입력/출력 디렉토리 지정
python csv_to_json.py --input-dir /path/to/csv --output-dir /path/to/json
```

## JSON 형식

### Array 형식 (기본)

각 행이 객체인 배열 형식:

```json
[
  {
    "column1": "value1",
    "column2": "value2"
  },
  {
    "column1": "value3",
    "column2": "value4"
  }
]
```

### Objects 형식

메타데이터를 포함한 객체 형식:

```json
{
  "rows": [
    {
      "column1": "value1",
      "column2": "value2"
    }
  ],
  "count": 1,
  "columns": ["column1", "column2"]
}
```

## 청크 분할

대용량 CSV 파일의 경우 `chunk_size` 옵션을 사용하여 여러 개의 JSON 파일로 분할할 수 있습니다:

```bash
python csv_to_json.py --chunk-size 10000
```

이 경우 다음과 같은 파일들이 생성됩니다:
- `filename_chunk_1.json`
- `filename_chunk_2.json`
- `filename_chunk_3.json`
- ...

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/` | 웹 인터페이스 |
| POST | `/api/convert` | 변환 작업 시작 |
| GET | `/api/jobs` | 모든 작업 목록 조회 |
| GET | `/api/jobs/{job_id}` | 특정 작업 상태 조회 |
| DELETE | `/api/jobs/{job_id}` | 작업 삭제 |
| GET | `/api/files` | 파일 목록 조회 |
| GET | `/health` | 헬스 체크 |
| GET | `/docs` | Swagger API 문서 |
| GET | `/redoc` | ReDoc API 문서 |

## 명령줄 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--input-dir` | 입력 CSV 파일 디렉토리 | ../data |
| `--output-dir` | 출력 JSON 파일 디렉토리 | ../data_json |
| `--format` | JSON 형식 (array, objects) | array |
| `--chunk-size` | 청크 크기 (대용량 파일 분할) | None |
| `--file` | 특정 파일만 변환 | None (전체 변환) |
| `--pattern` | 파일 패턴 | *.csv |

## 출력 구조

```
service/data_json/
├── yellow_tripdata_2023-01.json
├── yellow_tripdata_2023-02.json
├── yellow_tripdata_2023-01_chunk_1.json
├── yellow_tripdata_2023-01_chunk_2.json
└── ...
```

## 예제

### 1. 전체 파일 변환 (Array 형식)

```bash
python csv_to_json.py --format array
```

### 2. 특정 파일만 변환 (Objects 형식)

```bash
python csv_to_json.py --file yellow_tripdata_2023-01.csv --format objects
```

### 3. 대용량 파일 청크 분할

```bash
python csv_to_json.py --chunk-size 50000
```

### 4. 웹서비스를 통한 변환

1. 브라우저에서 `http://localhost:8001` 접속
2. JSON 형식 선택
3. (선택) 특정 파일명 입력
4. (선택) 청크 크기 입력
5. "변환 시작" 버튼 클릭
6. 작업 목록에서 진행 상황 확인

## 주의사항

1. **메모리 사용량**: 대용량 CSV 파일을 변환할 때는 충분한 메모리가 필요합니다.
2. **디스크 공간**: JSON 파일은 일반적으로 CSV 파일보다 크므로 충분한 디스크 공간을 확보하세요.
3. **인코딩**: UTF-8 인코딩을 사용합니다. 다른 인코딩의 CSV 파일은 변환 전에 UTF-8로 변환해야 합니다.
4. **청크 분할**: 대용량 파일의 경우 청크 분할을 사용하여 메모리 사용량을 줄일 수 있습니다.

## 문제 해결

### 메모리 부족 오류

대용량 파일을 변환할 때 메모리 부족이 발생하면 `--chunk-size` 옵션을 사용하세요:

```bash
python csv_to_json.py --chunk-size 10000
```

### 파일을 찾을 수 없음

입력 디렉토리 경로를 확인하세요:

```bash
python csv_to_json.py --input-dir /path/to/csv/files
```

### 인코딩 오류

CSV 파일이 UTF-8이 아닌 경우, 변환 전에 인코딩을 변경하세요:

```bash
# Windows PowerShell
Get-Content input.csv -Encoding Default | Set-Content output.csv -Encoding UTF8
```

## 참고 자료

- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [CSV 모듈 문서](https://docs.python.org/3/library/csv.html)
- [JSON 모듈 문서](https://docs.python.org/3/library/json.html)
