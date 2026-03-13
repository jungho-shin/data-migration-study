#!/usr/bin/env python3
"""
JSONL to HDFS Converter
JSONL 파일을 Spark를 이용하여 HDFS에 저장하는 유틸리티
"""

import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
import sys


class JSONLToHDFSConverter:
    """JSONL을 HDFS로 변환하는 클래스"""
    
    def __init__(self, input_dir: str, hdfs_path: str, spark_master: str = "spark://spark-master:7077"):
        """
        Args:
            input_dir: 입력 JSONL 파일 디렉토리
            hdfs_path: HDFS 저장 경로 (예: hdfs://namenode:9000/data/jsonl)
            spark_master: Spark Master URL
        """
        self.input_dir = Path(input_dir)
        self.hdfs_path = hdfs_path
        self.spark_master = spark_master
        
    def _create_spark_session(self):
        """Spark 세션 생성"""
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
            
            spark = SparkSession.builder \
                .appName("JSONLToHDFS") \
                .master(self.spark_master) \
                .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
                .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
                .config("spark.hadoop.dfs.client.use.datanode.hostname", "true") \
                .config("spark.network.timeout", "600s") \
                .config("spark.executor.heartbeatInterval", "60s") \
                .config("spark.sql.execution.arrow.pyspark.enabled", "false") \
                .getOrCreate()
            
            return spark
        except ImportError:
            raise ImportError("pyspark가 설치되지 않았습니다. pip install pyspark로 설치하세요.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise Exception(f"Spark 세션 생성 실패: {str(e)}")
    
    def upload_file(self, jsonl_file: Path, hdfs_output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        단일 JSONL 파일을 HDFS에 업로드
        
        Args:
            jsonl_file: 업로드할 JSONL 파일 경로
            hdfs_output_path: HDFS 출력 경로 (None이면 자동 생성)
        
        Returns:
            업로드 결과 정보
        """
        if not jsonl_file.exists():
            return {
                "success": False,
                "input_file": jsonl_file.name,
                "error": f"파일을 찾을 수 없습니다: {jsonl_file}"
            }
        
        try:
            spark = self._create_spark_session()
            
            # HDFS 출력 경로 설정
            if hdfs_output_path is None:
                hdfs_output_path = f"{self.hdfs_path}/{jsonl_file.stem}"
            
            print(f"JSONL 파일 읽기: {jsonl_file}")
            
            # 로컬 파일 경로를 명시적으로 지정 (file:// 프로토콜 사용)
            local_file_path = str(jsonl_file.resolve())
            if not local_file_path.startswith("file://"):
                local_file_path = f"file://{local_file_path}"
            
            # JSONL 파일 읽기 (각 줄이 JSON 객체)
            df = spark.read.json(local_file_path, multiLine=False)
            
            row_count = df.count()
            print(f"읽은 행 수: {row_count}")
            
            # HDFS에 Parquet 형식으로 저장
            print(f"HDFS에 저장 중: {hdfs_output_path}")
            df.write.mode("overwrite").parquet(hdfs_output_path)
            
            print(f"저장 완료: {hdfs_output_path}")
            
            spark.stop()
            
            return {
                "success": True,
                "input_file": jsonl_file.name,
                "hdfs_path": hdfs_output_path,
                "total_rows": row_count,
                "format": "parquet"
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "input_file": jsonl_file.name,
                "error": str(e)
            }
    
    def upload_all(self, pattern: str = "*.jsonl") -> Dict[str, Any]:
        """
        디렉토리 내 모든 JSONL 파일을 HDFS에 업로드
        
        Args:
            pattern: 파일 패턴 (기본: "*.jsonl")
        
        Returns:
            업로드 결과 요약
        """
        jsonl_files = list(self.input_dir.glob(pattern))
        
        if not jsonl_files:
            return {
                "success": False,
                "message": f"JSONL 파일을 찾을 수 없습니다: {self.input_dir}/{pattern}",
                "uploaded": 0,
                "failed": 0
            }
        
        results = []
        success_count = 0
        failed_count = 0
        
        for jsonl_file in jsonl_files:
            print(f"업로드 중: {jsonl_file.name}...")
            result = self.upload_file(jsonl_file)
            results.append(result)
            
            if result["success"]:
                success_count += 1
                print(f"  ✓ 완료: {result['hdfs_path']} ({result['total_rows']} 행)")
            else:
                failed_count += 1
                print(f"  ✗ 실패: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "total_files": len(jsonl_files),
            "uploaded": success_count,
            "failed": failed_count,
            "results": results
        }


def main():
    parser = argparse.ArgumentParser(description='JSONL to HDFS Converter')
    parser.add_argument('--input-dir', type=str, default='../data_json',
                       help='입력 JSONL 파일 디렉토리 (기본: ../data_json)')
    parser.add_argument('--hdfs-path', type=str, default='hdfs://namenode:9000/data/jsonl',
                       help='HDFS 저장 경로 (기본: hdfs://namenode:9000/data/jsonl)')
    parser.add_argument('--spark-master', type=str, default='spark://spark-master:7077',
                       help='Spark Master URL (기본: spark://spark-master:7077)')
    parser.add_argument('--file', type=str, default=None,
                       help='특정 파일만 업로드 (전체 업로드 시 생략)')
    parser.add_argument('--pattern', type=str, default='*.jsonl',
                       help='파일 패턴 (기본: *.jsonl)')
    
    args = parser.parse_args()
    
    converter = JSONLToHDFSConverter(
        input_dir=args.input_dir,
        hdfs_path=args.hdfs_path,
        spark_master=args.spark_master
    )
    
    if args.file:
        # 단일 파일 업로드
        jsonl_file = Path(args.input_dir) / args.file
        result = converter.upload_file(jsonl_file)
        
        if result["success"]:
            print(f"\n업로드 완료!")
            print(f"  입력: {result['input_file']}")
            print(f"  HDFS 경로: {result['hdfs_path']}")
            print(f"  행 수: {result['total_rows']}")
            sys.exit(0)
        else:
            print(f"\n업로드 실패: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    else:
        # 전체 파일 업로드
        summary = converter.upload_all(pattern=args.pattern)
        
        if summary["success"]:
            print(f"\n업로드 완료!")
            print(f"  전체 파일: {summary['total_files']}개")
            print(f"  성공: {summary['uploaded']}개")
            print(f"  실패: {summary['failed']}개")
            sys.exit(0)
        else:
            print(f"\n오류: {summary.get('message', 'Unknown error')}")
            sys.exit(1)


if __name__ == '__main__':
    main()
