1) 전체 흐름 (원하는 요구사항 기준)

NYC Taxi CSV(약 10GB) 수집

CSV → JSONL(한 줄에 한 JSON) 변환

JSONL을 HDFS에 저장 (/data/taxi/json/..)

Java 마이그레이션 프로세스

sc.textFile("hdfs:///data/.../*.json") 로 RDD로 읽고

spark.read().json(rdd) 로 DataFrame 생성(입력은 RDD 기반)

df.writeTo("catalog.db.table").append() 또는 df.write().format("iceberg")...로 Iceberg 테이블에 적재

Spark SQL로 Iceberg 테이블 조회 (Hive metastore + MinIO warehouse)

2) Docker Compose 구성(개발용)

아래는 “동작하는 방향”의 최소 구성입니다. (Hadoop/Hive/Spark 버전은 팀 표준에 맞게 pin 하세요)

docker-compose.yml (골격)
version: "3.8"

services:
  namenode:
    image: bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8
    container_name: namenode
    environment:
      - CLUSTER_NAME=demo
    ports:
      - "9870:9870"
      - "8020:8020"
    volumes:
      - nn_data:/hadoop/dfs/name
    networks: [lake]

  datanode:
    image: bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8
    container_name: datanode
    environment:
      - CORE_CONF_fs_defaultFS=hdfs://namenode:8020
    depends_on: [namenode]
    ports:
      - "9864:9864"
    volumes:
      - dn_data:/hadoop/dfs/data
    networks: [lake]

  postgres:
    image: postgres:15
    container_name: hive-postgres
    environment:
      - POSTGRES_USER=hive
      - POSTGRES_PASSWORD=hive
      - POSTGRES_DB=metastore
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
    networks: [lake]

  hive-metastore:
    image: apache/hive:4.0.0
    container_name: hive-metastore
    environment:
      - SERVICE_NAME=metastore
      - DB_DRIVER=postgres
      - SERVICE_OPTS=
        -Djavax.jdo.option.ConnectionURL=jdbc:postgresql://postgres:5432/metastore
        -Djavax.jdo.option.ConnectionDriverName=org.postgresql.Driver
        -Djavax.jdo.option.ConnectionUserName=hive
        -Djavax.jdo.option.ConnectionPassword=hive
    depends_on: [postgres, namenode, datanode]
    ports:
      - "9083:9083"
    networks: [lake]

  minio:
    image: minio/minio:RELEASE.2024-12-18T00-00-00Z
    container_name: minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minio
      - MINIO_ROOT_PASSWORD=minio123
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    networks: [lake]

  spark:
    image: bitnami/spark:3.5.1
    container_name: spark
    environment:
      - SPARK_MODE=master
    ports:
      - "8080:8080"
      - "4040:4040"
    volumes:
      - ./spark/conf:/opt/bitnami/spark/conf
      - ./spark/jars:/opt/bitnami/spark/jars
      - ./app:/app
    depends_on: [namenode, hive-metastore, minio]
    networks: [lake]

networks:
  lake:

volumes:
  nn_data:
  dn_data:
  pg_data:
  minio_data:

3) Spark에 Iceberg + HiveCatalog + MinIO(S3A) 설정
(A) Spark JAR 준비

spark/jars/에 최소 아래 JAR들을 넣어주세요 (버전은 서로 호환되게 맞추기)

iceberg-spark-runtime-3.5_2.12-<iceberg_ver>.jar

hadoop-aws-<hadoop_ver>.jar

aws-java-sdk-bundle-<compatible>.jar (또는 AWS SDK v2 번들)

필요시 postgresql-<ver>.jar (Hive metastore JDBC가 Spark에서 필요하면)

개발 편의상 “Spark 이미지에 jars 볼륨 마운트”가 가장 단순합니다.

(B) spark/conf/spark-defaults.conf
spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions

# HiveCatalog (metastore 사용)
spark.sql.catalog.lake=org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.lake.type=hive
spark.sql.catalog.lake.uri=thrift://hive-metastore:9083
spark.sql.catalog.lake.warehouse=s3a://warehouse/iceberg

# MinIO (S3A)
spark.hadoop.fs.s3a.endpoint=http://minio:9000
spark.hadoop.fs.s3a.access.key=minio
spark.hadoop.fs.s3a.secret.key=minio123
spark.hadoop.fs.s3a.path.style.access=true
spark.hadoop.fs.s3a.connection.ssl.enabled=false
spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem

# HDFS
spark.hadoop.fs.defaultFS=hdfs://namenode:8020

(C) MinIO에 버킷 생성

콘솔: http://localhost:9001 접속 후 warehouse 버킷 생성
또는 mc로 생성해도 됩니다.

4) 데이터 준비: CSV → JSONL → HDFS 적재
(권장) JSON은 “JSONL(한 줄 한 레코드)”로 만들기

Iceberg 적재할 때 Spark가 훨씬 안정적으로 읽습니다.

예시(로컬 파일을 컨테이너로 넣었다고 가정):

CSV를 JSONL로 변환 (Spark로 변환하는 게 제일 단순)

# spark 컨테이너 내부에서
/opt/bitnami/spark/bin/spark-shell << 'EOF'
val df = spark.read.option("header","true").csv("file:/app/data/taxi.csv")
df.coalesce(8).write.mode("overwrite").json("file:/app/out/taxi_jsonl")
EOF


결과(JSON 파티션 디렉토리)를 HDFS로 업로드

# namenode 컨테이너에서 (또는 hadoop client가 있는 곳에서)
hdfs dfs -mkdir -p /data/taxi/json
hdfs dfs -put -f /app/out/taxi_jsonl/* /data/taxi/json/


10GB면 JSON이 더 커질 수 있어요. 가능하면 JSON 만들 때 필요한 컬럼만 남기고, 파티션(년/월) 컬럼을 미리 만드는 게 좋습니다.

5) Java 마이그레이션 프로세스 (RDD로 읽어서 Iceberg 적재)

핵심은 RDD로 HDFS의 JSON을 읽는 것입니다:

JavaRDD<String> lines = sc.textFile("hdfs:///data/taxi/json/*.json");

Dataset<Row> df = spark.read().json(lines); ← 입력 소스가 RDD

Iceberg 테이블 생성/적재

HdfsJsonToIceberg.java (예시)
import org.apache.spark.api.java.JavaRDD;
import org.apache.spark.sql.*;

public class HdfsJsonToIceberg {
    public static void main(String[] args) {
        // args[0] = hdfs input (e.g. hdfs:///data/taxi/json/*.json)
        // args[1] = iceberg table (e.g. lake.taxi_db.nyc_taxi)
        String input = args.length > 0 ? args[0] : "hdfs:///data/taxi/json/*.json";
        String table = args.length > 1 ? args[1] : "lake.taxi_db.nyc_taxi";

        SparkSession spark = SparkSession.builder()
                .appName("HdfsJsonToIceberg")
                .getOrCreate();

        // 1) 반드시 RDD로 읽기
        JavaRDD<String> jsonLines = spark.sparkContext()
                .textFile(input, 0)
                .toJavaRDD();

        // 2) RDD -> DataFrame
        Dataset<Row> df = spark.read().json(jsonLines);

        // (권장) 스키마/컬럼 정리: 타입 캐스팅, 필요한 컬럼 선택, 파티션 컬럼 생성 등
        // 예: pickup_datetime이 있다면 날짜 파티션 컬럼 생성
        // df = df.withColumn("pickup_date", functions.to_date(df.col("pickup_datetime")));

        // 3) Iceberg DB 생성
        spark.sql("CREATE DATABASE IF NOT EXISTS lake.taxi_db");

        // 4) Iceberg 테이블 생성 (없으면)
        spark.sql(
            "CREATE TABLE IF NOT EXISTS " + table + " (" +
            "  vendor_id string, " +
            "  pickup_datetime string, " +
            "  dropoff_datetime string, " +
            "  passenger_count string, " +
            "  trip_distance string " +
            ") USING iceberg"
        );

        // 5) 적재 (Iceberg로 write)
        // 테이블 스키마와 df 스키마가 다르면 컬럼 매핑/캐스팅을 맞춰야 함
        df.selectExpr(
                "cast(vendor_id as string) as vendor_id",
                "cast(pickup_datetime as string) as pickup_datetime",
                "cast(dropoff_datetime as string) as dropoff_datetime",
                "cast(passenger_count as string) as passenger_count",
                "cast(trip_distance as string) as trip_distance"
        ).writeTo(table).append();

        spark.stop();
    }
}

실행 예시
# spark 컨테이너에서 (jar를 /app에 두었다고 가정)
/opt/bitnami/spark/bin/spark-submit \
  --class HdfsJsonToIceberg \
  --master local[*] \
  /app/migrator.jar \
  "hdfs:///data/taxi/json/*.json" \
  "lake.taxi_db.nyc_taxi"

6) Iceberg 조회 확인

spark-sql 또는 spark-shell에서:

SHOW NAMESPACES IN lake;
SHOW TABLES IN lake.taxi_db;
SELECT count(*) FROM lake.taxi_db.nyc_taxi;
SELECT * FROM lake.taxi_db.nyc_taxi LIMIT 10;

7) 꼭 짚고 넘어갈 포인트 (실무에서 자주 막히는 부분)

JSON은 JSONL로: Spark가 디렉토리 내 여러 파일을 병렬 처리할 때 안정적입니다.

“RDD로 읽어서 Parquet 생성” 요구는
sc.textFile → RDD[String] → spark.read().json(rdd) → Iceberg write로 충족됩니다.
(최종 쓰기는 Iceberg sink가 DataFrame 기반이긴 하지만, 입력이 RDD이면 요구사항 충족으로 보는 게 일반적입니다.)

MinIO endpoint/path-style/access key 설정이 조금이라도 틀리면 warehouse 경로에 파일이 안 써지거나, 써도 Spark/Hive가 못 읽습니다.

HiveCatalog를 쓰면 메타데이터는 Hive(Postgres), **데이터 파일은 MinIO(s3a)**에 저장됩니다.



원하면, 위 구성에서 다음 중 하나로 “바로 개발 가능한 형태”로 더 구체화해서 줄게요.

(1) NYC Taxi에서 10GB 딱 맞춰 받는 월/분량 선택 + 변환/적재 스크립트

(2) Iceberg 테이블을 날짜 파티션(예: pickup_date) + 정렬(z-order 유사)까지 적용

(3) Java 마이그레이터에 체크포인트/재시도/정합성 검증(count 비교, 샘플 해시 비교) 넣기

당신이 원하는 데이터 컬럼(예: yellow taxi / green taxi / fhv 중 무엇인지)만 알려주면, 스키마/파티션까지 포함해서 “그대로 실행 가능한” 버전으로 맞춰드릴게요.