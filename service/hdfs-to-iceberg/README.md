# HDFS to Iceberg Converter

HDFS의 JSON 파일을 Spark를 이용하여 Iceberg 테이블에 저장하는 서비스입니다. Reference.md에 명시된 프로세스를 따라 HDFS의 JSON 파일을 읽어서 Iceberg 테이블로 마이그레이션합니다.

## 기능

- **Spark 기반 처리**: PySpark를 사용하여 대용량 데이터 처리
- **RDD 기반 읽기**: `sc.textFile()`로 HDFS의 JSON 파일을 RDD로 읽기
- **DataFrame 변환**: `spark.read.json()`으로 RDD를 DataFrame으로 변환
- **Iceberg 저장**: `df.write().format("iceberg")`로 Iceberg 테이블에 저장
- **웹 인터페이스**: 브라우저를 통한 쉬운 마이그레이션 관리
- **REST API**: 프로그래밍 방식으로 마이그레이션 제어

## 마이그레이션 프로세스

Reference.md에 따라 다음 프로세스를 따릅니다:

1. `sc.textFile("hdfs:///data/.../*.json")` - HDFS의 JSON 파일을 RDD로 읽기
2. `spark.read().json(rdd)` - RDD를 DataFrame으로 변환
3. `df.write().format("iceberg")` - Iceberg 테이블에 적재

## 요구사항

- Python 3.8 이상
- Java 8 (Spark 3.2.0과 호환)
- Spark Cluster (infra 디렉토리의 docker-compose로 실행)
- HDFS (infra 디렉토리의 docker-compose로 실행)
- Hive Metastore (infra 디렉토리의 docker-compose로 실행)
- Iceberg (Spark 패키지로 포함)

## 설치

```bash
pip install -r requirements.txt
```

## 사용 방법

### 🌐 웹서비스 사용 (권장)

#### 1. Docker를 사용한 실행

**전제 조건**: `infra` 디렉토리의 Docker Compose가 실행 중이어야 합니다.

```bash
# infra 서비스 시작 (HDFS, Spark, Hive)
cd ../infra
docker-compose up -d

# HDFS to Iceberg 서비스 시작
cd ../hdfs-to-iceberg
docker-compose up -d
```

#### 2. 로컬에서 직접 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 웹서비스 시작
uvicorn app:app --host 0.0.0.0 --port 8003 --reload
```

#### 3. 웹 인터페이스 접속

브라우저에서 `http://localhost:8003` 접속

- **웹 UI**: 폼을 통해 마이그레이션 작업 시작 및 모니터링
- **API 문서**: `http://localhost:8003/docs` (Swagger UI)
- **대체 문서**: `http://localhost:8003/redoc` (ReDoc)

#### 4. REST API 사용 예시

```bash
# 마이그레이션 시작
curl -X POST "http://localhost:8003/api/migrate" \
  -H "Content-Type: application/json" \
  -d '{
    "hdfs_path": "hdfs://namenode:9000/data/jsonl/*.json",
    "catalog": "spark_catalog",
    "database": "default",
    "table": "nyc_taxi",
    "spark_master": "spark://spark-master:7077"
  }'

# 작업 목록 조회
curl http://localhost:8003/api/jobs

# 특정 작업 조회
curl http://localhost:8003/api/jobs/{job_id}
```

### 📝 명령줄 사용 (CLI)

#### 기본 사용

```bash
python hdfs_to_iceberg.py \
  --hdfs-path "hdfs://namenode:9000/data/jsonl/*.json" \
  --database "default" \
  --table "nyc_taxi"
```

#### 모든 옵션 지정

```bash
python hdfs_to_iceberg.py \
  --hdfs-path "hdfs://namenode:9000/data/jsonl/*.json" \
  --catalog "spark_catalog" \
  --database "default" \
  --table "nyc_taxi" \
  --spark-master "spark://spark-master:7077"
```

## API 엔드포인트

### POST /api/migrate

마이그레이션 작업을 시작합니다.

**요청 본문:**
```json
{
  "hdfs_path": "hdfs://namenode:9000/data/jsonl/*.json",
  "catalog": "spark_catalog",
  "database": "default",
  "table": "nyc_taxi",
  "spark_master": "spark://spark-master:7077"
}
```

**응답:**
```json
{
  "job_id": "uuid-string",
  "status": "pending"
}
```

### GET /api/jobs

모든 작업 목록을 조회합니다.

**응답:**
```json
[
  {
    "job_id": "uuid-string",
    "status": "completed",
    "progress": 100.0,
    "message": "마이그레이션 완료",
    "created_at": "2026-03-13T06:00:00",
    "updated_at": "2026-03-13T06:05:00",
    "result": {
      "success": true,
      "hdfs_path": "hdfs://namenode:9000/data/jsonl/*.json",
      "table_name": "spark_catalog.default.nyc_taxi",
      "total_rows": 1000000,
      "format": "iceberg"
    }
  }
]
```

### GET /api/jobs/{job_id}

특정 작업의 상태를 조회합니다.

**응답:**
```json
{
  "job_id": "uuid-string",
  "status": "running",
  "progress": 50.0,
  "message": "HDFS에서 데이터 읽는 중...",
  "created_at": "2026-03-13T06:00:00",
  "updated_at": "2026-03-13T06:02:30",
  "result": null
}
```

## 작업 상태

- **pending**: 작업이 대기 중
- **running**: 작업이 실행 중
- **completed**: 작업이 성공적으로 완료됨
- **failed**: 작업이 실패함

## Iceberg 테이블 설정

### 카탈로그 설정

기본적으로 `spark_catalog`를 사용하며, Hive Metastore를 통해 관리됩니다.

### 데이터베이스 및 테이블

- **데이터베이스**: 기본값은 `default`
- **테이블**: 사용자가 지정한 테이블 이름

### 테이블 자동 생성

테이블이 존재하지 않으면 자동으로 생성됩니다. 첫 번째 데이터의 스키마를 기반으로 테이블이 생성됩니다.

## Spark 설정

서비스는 다음 Spark 설정을 사용합니다:

- **Spark Master**: `spark://spark-master:7077` (기본값)
- **Driver Memory**: 2GB
- **Executor Memory**: 2GB
- **Iceberg Extension**: `org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions`
- **Iceberg Catalog**: Hive Metastore 기반

## 문제 해결

### Spark 연결 실패

- Spark Master가 실행 중인지 확인: `docker ps | grep spark-master`
- 네트워크 연결 확인: `docker network ls | grep data-migration-network`

### HDFS 접근 실패

- HDFS NameNode가 실행 중인지 확인: `docker ps | grep namenode`
- HDFS 경로가 올바른지 확인: `docker exec -it namenode hdfs dfs -ls /data/jsonl`

### Iceberg 테이블 생성 실패

- Hive Metastore가 실행 중인지 확인: `docker ps | grep hive-metastore`
- 카탈로그 설정이 올바른지 확인

### 메모리 부족

- Spark 메모리 설정을 조정하거나 파일을 더 작은 단위로 나누어 처리

## 파일 구조

```
hdfs-to-iceberg/
├── app.py                 # FastAPI 웹 서비스
├── hdfs_to_iceberg.py     # 핵심 마이그레이션 로직
├── docker-compose.yml     # Docker Compose 설정
├── Dockerfile             # Docker 이미지 빌드 설정
├── requirements.txt       # Python 의존성
└── README.md             # 이 파일
```

## 라이선스

이 프로젝트는 내부 사용을 위한 것입니다.
