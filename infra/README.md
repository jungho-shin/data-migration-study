# data-migration-study

빅데이터 마이그레이션 스터디를 위한 Docker 기반 인프라 구성

## 포함된 서비스

- **MinIO**: S3 호환 객체 스토리지 (포트: 9002, 9001)
- **HDFS**: Hadoop 분산 파일 시스템
  - NameNode (포트: 9870, 9000)
  - DataNode (포트: 9864)
- **Hive**: 데이터 웨어하우스
  - Metastore (포트: 9083)
  - HiveServer2 (포트: 10000, 10002)
- **PostgreSQL**: Hive Metastore용 데이터베이스 (포트: 5432)
- **Spark**: 빅데이터 처리 엔진
  - Master (포트: 8080, 7077)
  - Worker (포트: 8081)
- **Iceberg**: 테이블 포맷 (Spark와 Hive에서 사용)

## 시작하기

### 서비스 시작
```bash
cd infra
docker-compose up -d
```

### 서비스 중지
```bash
docker-compose down
```

### 데이터 유지하며 중지
```bash
docker-compose down
```

### 데이터 삭제하며 중지
```bash
docker-compose down -v
```

## 접속 정보

### MinIO
- API URL: http://localhost:9002
- Console URL: http://localhost:9001
- Access Key: minioadmin
- Secret Key: minioadmin

### HDFS NameNode
- Web UI: http://localhost:9870

### Spark Master
- Web UI: http://localhost:8080

### Hive
- JDBC URL: jdbc:hive2://localhost:10000
- Beeline 연결 예시:
  ```bash
  docker exec -it hive-server beeline -u jdbc:hive2://localhost:10000
  ```

## Iceberg 사용

Iceberg는 Spark와 Hive에서 테이블 포맷으로 사용할 수 있습니다. Spark에서 Iceberg를 사용하려면 Spark 세션에 Iceberg 라이브러리를 추가해야 합니다.

### Spark에서 Iceberg 사용 예시
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("IcebergExample") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.iceberg.spark.SparkSessionCatalog") \
    .config("spark.sql.catalog.spark_catalog.type", "hive") \
    .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.local.type", "hadoop") \
    .config("spark.sql.catalog.local.warehouse", "hdfs://namenode:9000/warehouse") \
    .getOrCreate()
```

## 주의사항

- 모든 서비스가 정상적으로 시작되기까지 몇 분이 소요될 수 있습니다.
- Healthcheck를 통해 서비스 상태를 확인할 수 있습니다: `docker-compose ps`
- 데이터는 Docker 볼륨에 저장되므로 `docker-compose down -v`를 실행하면 모든 데이터가 삭제됩니다.
