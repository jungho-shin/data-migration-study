# JSONL to HDFS Converter

JSONL 파일을 Spark를 이용하여 HDFS에 저장하는 서비스입니다. `./service/data_json` 디렉토리의 JSONL 파일을 읽어서 HDFS에 Parquet 형식으로 저장합니다.

## 기능

- **Spark 기반 처리**: PySpark를 사용하여 대용량 데이터 처리
- **배치 업로드**: 디렉토리 내 모든 JSONL 파일을 한 번에 업로드
- **단일 파일 업로드**: 특정 파일만 선택하여 업로드
- **Parquet 형식**: HDFS에 효율적인 Parquet 형식으로 저장
- **웹 인터페이스**: 브라우저를 통한 쉬운 업로드 관리
- **REST API**: 프로그래밍 방식으로 업로드 제어

## 요구사항

- Python 3.8 이상
- Java 11 이상 (Spark 실행용)
- Spark Cluster (infra 디렉토리의 docker-compose로 실행)
- HDFS (infra 디렉토리의 docker-compose로 실행)
- JSONL 파일 (입력)

## 설치

```bash
pip install -r requirements.txt
```

## 사용 방법

### 🌐 웹서비스 사용 (권장)

#### 1. Docker를 사용한 실행

**전제 조건**: `infra` 디렉토리의 Docker Compose가 실행 중이어야 합니다.

```bash
# infra 서비스 시작 (HDFS, Spark)
cd ../infra
docker-compose up -d

# JSONL to HDFS 서비스 시작
cd ../jsonl-to-hdfs
docker-compose up -d
```

#### 2. 로컬에서 직접 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 웹서비스 시작
python app.py

# 또는 uvicorn으로 직접 실행
uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

#### 3. 웹 인터페이스 접속

브라우저에서 `http://localhost:8002` 접속

- **웹 UI**: 폼을 통해 업로드 작업 시작 및 모니터링
- **API 문서**: `http://localhost:8002/docs` (Swagger UI)
- **대체 문서**: `http://localhost:8002/redoc` (ReDoc)

#### 4. REST API 사용 예시

```bash
# 전체 파일 업로드
curl -X POST "http://localhost:8002/api/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "hdfs_path": "hdfs://namenode:9000/data/jsonl"
  }'

# 특정 파일만 업로드
curl -X POST "http://localhost:8002/api/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "files": ["yellow_tripdata_2023-01.jsonl"],
    "hdfs_path": "hdfs://namenode:9000/data/jsonl"
  }'

# 작업 목록 조회
curl http://localhost:8002/api/jobs

# 파일 목록 조회
curl http://localhost:8002/api/files
```

### 📝 명령줄 사용 (CLI)

#### 기본 사용 (전체 파일 업로드)

```bash
python jsonl_to_hdfs.py
```

#### 옵션 지정

```bash
# 특정 파일만 업로드
python jsonl_to_hdfs.py --file yellow_tripdata_2023-01.jsonl

# HDFS 경로 지정
python jsonl_to_hdfs.py --hdfs-path hdfs://namenode:9000/data/jsonl

# Spark Master URL 지정
python jsonl_to_hdfs.py --spark-master spark://spark-master:7077

# 입력 디렉토리 지정
python jsonl_to_hdfs.py --input-dir /path/to/jsonl
```

## API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/` | 웹 인터페이스 |
| POST | `/api/upload` | 업로드 작업 시작 |
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
| `--input-dir` | 입력 JSONL 파일 디렉토리 | ../data_json |
| `--hdfs-path` | HDFS 저장 경로 | hdfs://namenode:9000/data/jsonl |
| `--spark-master` | Spark Master URL | spark://spark-master:7077 |
| `--file` | 특정 파일만 업로드 | None (전체 업로드) |
| `--pattern` | 파일 패턴 | *.jsonl |

## HDFS 저장 형식

JSONL 파일은 HDFS에 **Parquet 형식**으로 저장됩니다:

- **형식**: Parquet (컬럼 기반 저장 형식)
- **압축**: 자동 압축 (Parquet 기본)
- **경로 구조**: `{hdfs_path}/{파일명}/` (Parquet 파일들이 디렉토리 내에 저장)

### HDFS 경로 예시

```
hdfs://namenode:9000/data/jsonl/yellow_tripdata_2023-01/
├── part-00000-xxx.parquet
├── part-00001-xxx.parquet
└── ...
```

## 예제

### 1. 전체 파일 업로드

```bash
python jsonl_to_hdfs.py
```

### 2. 특정 파일만 업로드

```bash
python jsonl_to_hdfs.py --file yellow_tripdata_2023-01.jsonl
```

### 3. 커스텀 HDFS 경로로 업로드

```bash
python jsonl_to_hdfs.py --hdfs-path hdfs://namenode:9000/my_data/taxi
```

### 4. 웹서비스를 통한 업로드

1. 브라우저에서 `http://localhost:8002` 접속
2. JSONL 파일 목록에서 업로드할 파일 선택 (체크박스)
3. HDFS 저장 경로 입력
4. "선택한 파일 HDFS 업로드" 버튼 클릭
5. 작업 목록에서 진행 상황 확인

## HDFS 데이터 확인

### HDFS 명령어로 확인

```bash
# HDFS에 접속
docker exec -it namenode bash

# 파일 목록 확인
hdfs dfs -ls /data/jsonl

# 특정 디렉토리 내용 확인
hdfs dfs -ls /data/jsonl/yellow_tripdata_2023-01

# 파일 크기 확인
hdfs dfs -du -h /data/jsonl
```

### Spark로 데이터 읽기

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("ReadHDFSData") \
    .master("spark://spark-master:7077") \
    .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
    .getOrCreate()

# Parquet 파일 읽기
df = spark.read.parquet("hdfs://namenode:9000/data/jsonl/yellow_tripdata_2023-01")

# 데이터 확인
df.show()
df.printSchema()
df.count()
```

## 주의사항

1. **Spark Cluster 필요**: 이 서비스는 Spark Cluster가 실행 중이어야 합니다.
2. **HDFS 연결**: HDFS NameNode에 접근 가능해야 합니다.
3. **네트워크**: Docker 네트워크에서 Spark와 HDFS에 접근할 수 있어야 합니다.
4. **메모리**: 대용량 파일 처리 시 충분한 메모리가 필요합니다.
5. **Java**: Spark 실행을 위해 Java 11 이상이 필요합니다.

## 문제 해결

### Spark 연결 실패

Spark Master가 실행 중인지 확인:

```bash
docker ps | grep spark-master
```

### HDFS 연결 실패

HDFS NameNode가 실행 중인지 확인:

```bash
docker ps | grep namenode
```

### Java 오류

Java가 설치되어 있는지 확인:

```bash
java -version
```

### 네트워크 문제

Docker 네트워크가 올바르게 설정되었는지 확인:

```bash
docker network ls
docker network inspect root_data-migration-network
```

## 참고 자료

- [PySpark 문서](https://spark.apache.org/docs/latest/api/python/)
- [HDFS 명령어 가이드](https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-common/FileSystemShell.html)
- [Parquet 형식](https://parquet.apache.org/)
