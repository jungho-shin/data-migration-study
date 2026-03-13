#!/usr/bin/env python3
"""
HDFS to Iceberg Converter
HDFS의 JSON 파일을 Spark를 이용하여 Iceberg 테이블에 저장하는 유틸리티
"""

import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
import sys


class HDFSToIcebergConverter:
    """HDFS의 JSON을 Iceberg 테이블로 변환하는 클래스"""
    
    def __init__(
        self, 
        hdfs_path: str,
        catalog_name: str,
        database_name: str,
        table_name: str,
        spark_master: str = "spark://spark-master:7077"
    ):
        """
        Args:
            hdfs_path: HDFS에서 읽을 JSON 파일 경로 (예: hdfs://namenode:9000/data/jsonl/*.json)
            catalog_name: Iceberg 카탈로그 이름
            database_name: 데이터베이스 이름
            table_name: 테이블 이름
            spark_master: Spark Master URL
        """
        self.hdfs_path = hdfs_path
        self.catalog_name = catalog_name
        self.database_name = database_name
        self.table_name = table_name
        self.spark_master = spark_master
        
    def _create_spark_session(self):
        """Spark 세션 생성 (Iceberg 지원)"""
        try:
            from pyspark.sql import SparkSession
            import time
            
            # 기존 SparkContext가 있으면 정리
            try:
                from pyspark import SparkContext
                sc = SparkContext._active_spark_context
                if sc is not None:
                    sc.stop()
            except:
                pass
            
            # 잠시 대기 (SparkContext 정리 시간)
            time.sleep(1)
            
            # Iceberg 패키지 포함
            spark = SparkSession.builder \
                .appName("HDFSToIceberg") \
                .master(self.spark_master) \
                .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
                .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
                .config("spark.hadoop.dfs.client.use.datanode.hostname", "true") \
                .config("spark.network.timeout", "600s") \
                .config("spark.executor.heartbeatInterval", "60s") \
                .config("spark.sql.execution.arrow.pyspark.enabled", "false") \
                .config("spark.driver.memory", "2g") \
                .config("spark.executor.memory", "2g") \
                .config("spark.driver.maxResultSize", "1g") \
                .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
                .config("spark.sql.catalog.spark_catalog", "org.apache.iceberg.spark.SparkCatalog") \
                .config("spark.sql.catalog.spark_catalog.type", "hive") \
                .config("spark.sql.catalog.spark_catalog.uri", "thrift://hive-metastore:9083") \
                .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.2_2.12:1.4.2,org.apache.hadoop:hadoop-client:3.2.1") \
                .getOrCreate()
            
            return spark
        except ImportError:
            raise ImportError("pyspark가 설치되지 않았습니다. pip install pyspark로 설치하세요.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise Exception(f"Spark 세션 생성 실패: {str(e)}")
    
    def migrate_to_iceberg(self) -> Dict[str, Any]:
        """
        HDFS의 JSON 파일을 읽어서 Iceberg 테이블에 저장
        
        Returns:
            마이그레이션 결과 정보
        """
        try:
            spark = self._create_spark_session()
            
            print(f"HDFS에서 JSON 파일 읽기: {self.hdfs_path}")
            
            # Reference.md에 따라: sc.textFile()로 RDD 읽기
            sc = spark.sparkContext
            rdd = sc.textFile(self.hdfs_path)
            
            print(f"RDD 생성 완료, 파티션 수: {rdd.getNumPartitions()}")
            
            # RDD를 DataFrame으로 변환 (spark.read.json() 사용)
            # RDD를 임시 파일로 저장 후 읽기
            temp_hdfs_path = f"{self.hdfs_path}/_temp_rdd"
            
            # RDD를 HDFS에 저장 (JSON 형식 유지)
            rdd.saveAsTextFile(temp_hdfs_path)
            
            # 저장된 파일을 JSON으로 읽기
            df = spark.read.json(temp_hdfs_path, multiLine=False)
            
            row_count = df.count()
            print(f"읽은 행 수: {row_count}")
            
            if row_count == 0:
                return {
                    "success": False,
                    "error": "읽은 데이터가 없습니다."
                }
            
            # Iceberg 테이블 경로 구성
            full_table_name = f"{self.catalog_name}.{self.database_name}.{self.table_name}"
            
            print(f"Iceberg 테이블에 저장 중: {full_table_name}")
            
            # Iceberg 테이블에 저장 (append 모드)
            # Reference.md에 따라: df.writeTo("catalog.db.table").append() 또는 df.write().format("iceberg")...
            try:
                # 먼저 테이블이 존재하는지 확인하고, 없으면 생성
                spark.sql(f"CREATE DATABASE IF NOT EXISTS {self.database_name}")
                
                # Iceberg 테이블에 데이터 저장
                df.write \
                    .format("iceberg") \
                    .mode("append") \
                    .saveAsTable(full_table_name)
                
                print(f"저장 완료: {full_table_name}")
                
            except Exception as e:
                # 테이블이 없으면 생성 후 저장
                print(f"테이블이 없어서 생성 중... (오류: {e})")
                
                # 첫 번째 행으로 스키마 추론
                sample_df = df.limit(1)
                sample_df.write \
                    .format("iceberg") \
                    .mode("overwrite") \
                    .saveAsTable(full_table_name)
                
                # 나머지 데이터 append
                df.write \
                    .format("iceberg") \
                    .mode("append") \
                    .saveAsTable(full_table_name)
                
                print(f"테이블 생성 및 저장 완료: {full_table_name}")
            
            # 임시 파일 삭제
            try:
                hadoop_fs = spark.sparkContext._jvm.org.apache.hadoop.fs.FileSystem.get(
                    spark.sparkContext._jsc.hadoopConfiguration()
                )
                temp_path = spark.sparkContext._jvm.org.apache.hadoop.fs.Path(temp_hdfs_path)
                if hadoop_fs.exists(temp_path):
                    hadoop_fs.delete(temp_path, True)
                    print(f"임시 파일 삭제 완료: {temp_hdfs_path}")
            except Exception as e:
                print(f"임시 파일 삭제 실패 (무시): {e}")
            
            spark.stop()
            
            return {
                "success": True,
                "hdfs_path": self.hdfs_path,
                "table_name": full_table_name,
                "total_rows": row_count,
                "format": "iceberg"
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }


def main():
    parser = argparse.ArgumentParser(description='HDFS to Iceberg Converter')
    parser.add_argument('--hdfs-path', type=str, required=True,
                       help='HDFS에서 읽을 JSON 파일 경로 (예: hdfs://namenode:9000/data/jsonl/*.json)')
    parser.add_argument('--catalog', type=str, default='spark_catalog',
                       help='Iceberg 카탈로그 이름 (기본: spark_catalog)')
    parser.add_argument('--database', type=str, required=True,
                       help='데이터베이스 이름')
    parser.add_argument('--table', type=str, required=True,
                       help='테이블 이름')
    parser.add_argument('--spark-master', type=str, default='spark://spark-master:7077',
                       help='Spark Master URL (기본: spark://spark-master:7077)')
    
    args = parser.parse_args()
    
    converter = HDFSToIcebergConverter(
        hdfs_path=args.hdfs_path,
        catalog_name=args.catalog,
        database_name=args.database,
        table_name=args.table,
        spark_master=args.spark_master
    )
    
    result = converter.migrate_to_iceberg()
    
    if result["success"]:
        print(f"\n마이그레이션 완료!")
        print(f"  HDFS 경로: {result['hdfs_path']}")
        print(f"  테이블: {result['table_name']}")
        print(f"  행 수: {result['total_rows']}")
        sys.exit(0)
    else:
        print(f"\n마이그레이션 실패: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
