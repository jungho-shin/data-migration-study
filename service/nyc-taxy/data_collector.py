#!/usr/bin/env python3
"""
NYC Taxi Trip Data Collector
뉴욕 택시 운행 데이터를 수집하는 서비스
"""

import os
import sys
import requests
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import time

class NYCTaxiDataCollector:
    """NYC 택시 데이터 수집기"""
    
    # NYC TLC 공식 데이터 URL 패턴
    BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
    
    # 택시 타입별 URL 패턴
    TAXI_TYPES = {
        'yellow': 'yellow_tripdata',
        'green': 'green_tripdata',
        'fhv': 'fhv_tripdata',
        'fhvhv': 'fhvhv_tripdata'
    }
    
    def __init__(self, output_dir='./data', max_size_gb=10):
        """
        Args:
            output_dir: 데이터 저장 디렉토리
            max_size_gb: 최대 수집 크기 (GB)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_gb = max_size_gb
        self.max_size_bytes = max_size_gb * 1024 * 1024 * 1024
        self.collected_size = 0
        
    def get_file_url(self, taxi_type, year, month):
        """파일 URL 생성"""
        if taxi_type not in self.TAXI_TYPES:
            raise ValueError(f"Unknown taxi type: {taxi_type}")
        
        month_str = f"{month:02d}"
        filename = f"{self.TAXI_TYPES[taxi_type]}_{year}-{month_str}.parquet"
        
        # 2022년 이후는 parquet, 이전은 csv
        if year >= 2022:
            return f"{self.BASE_URL}/{filename}"
        else:
            filename_csv = filename.replace('.parquet', '.csv')
            return f"{self.BASE_URL}/{filename_csv}"
    
    def get_file_size(self, url):
        """파일 크기 확인 (HEAD 요청)"""
        try:
            response = requests.head(url, timeout=10)
            if response.status_code == 200:
                size = int(response.headers.get('Content-Length', 0))
                return size
        except Exception as e:
            print(f"Warning: Could not get file size for {url}: {e}")
        return 0
    
    def download_file(self, url, output_path):
        """파일 다운로드"""
        print(f"Downloading: {url}")
        print(f"Destination: {output_path}")
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 진행률 표시
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rProgress: {percent:.1f}% ({downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB)", end='')
            
            print()  # 줄바꿈
            return downloaded
            
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {url}: {e}")
            if output_path.exists():
                output_path.unlink()
            return 0
    
    def convert_parquet_to_csv(self, parquet_path, csv_path):
        """Parquet 파일을 CSV로 변환"""
        try:
            import pandas as pd
            print(f"Converting {parquet_path.name} to CSV...")
            df = pd.read_parquet(parquet_path)
            df.to_csv(csv_path, index=False)
            print(f"Converted to CSV: {csv_path}")
            return csv_path.stat().st_size
        except ImportError:
            print("Error: pandas and pyarrow are required for parquet conversion")
            print("Install with: pip install pandas pyarrow")
            return 0
        except Exception as e:
            print(f"Error converting parquet: {e}")
            return 0
    
    def collect_data(self, taxi_type='yellow', start_year=2023, start_month=1, 
                     end_year=None, end_month=None, max_files=None):
        """
        데이터 수집
        
        Args:
            taxi_type: 택시 타입 (yellow, green, fhv, fhvhv)
            start_year: 시작 연도
            start_month: 시작 월
            end_year: 종료 연도 (None이면 현재까지)
            end_month: 종료 월 (None이면 현재까지)
            max_files: 최대 파일 수 (None이면 크기 제한만 적용)
        """
        if end_year is None:
            end_year = datetime.now().year
        if end_month is None:
            end_month = datetime.now().month
        
        print(f"Starting data collection...")
        print(f"Taxi Type: {taxi_type}")
        print(f"Period: {start_year}-{start_month:02d} to {end_year}-{end_month:02d}")
        print(f"Max Size: {self.max_size_gb} GB")
        print(f"Output Directory: {self.output_dir}")
        print("-" * 60)
        
        file_count = 0
        
        for year in range(start_year, end_year + 1):
            start_m = start_month if year == start_year else 1
            end_m = end_month if year == end_year else 12
            
            for month in range(start_m, end_m + 1):
                if max_files and file_count >= max_files:
                    print(f"Reached max files limit: {max_files}")
                    break
                
                if self.collected_size >= self.max_size_bytes:
                    print(f"Reached max size limit: {self.max_size_gb} GB")
                    break
                
                url = self.get_file_url(taxi_type, year, month)
                file_size = self.get_file_size(url)
                
                if file_size == 0:
                    print(f"Skipping {year}-{month:02d}: File not found or inaccessible")
                    continue
                
                if self.collected_size + file_size > self.max_size_bytes:
                    print(f"File {year}-{month:02d} would exceed size limit. Stopping.")
                    break
                
                # 파일명 생성
                if year >= 2022:
                    filename = f"{self.TAXI_TYPES[taxi_type]}_{year}-{month:02d}.parquet"
                    output_path = self.output_dir / filename
                    csv_path = self.output_dir / filename.replace('.parquet', '.csv')
                else:
                    filename = f"{self.TAXI_TYPES[taxi_type]}_{year}-{month:02d}.csv"
                    output_path = self.output_dir / filename
                    csv_path = output_path
                
                # 이미 다운로드된 파일 확인
                if csv_path.exists():
                    size = csv_path.stat().st_size
                    print(f"Skipping {filename}: Already exists ({size / (1024*1024):.1f} MB)")
                    self.collected_size += size
                    file_count += 1
                    continue
                
                # 다운로드
                downloaded = self.download_file(url, output_path)
                
                if downloaded > 0:
                    # Parquet 파일인 경우 CSV로 변환
                    if output_path.suffix == '.parquet':
                        csv_size = self.convert_parquet_to_csv(output_path, csv_path)
                        if csv_size > 0:
                            output_path.unlink()  # Parquet 파일 삭제
                            self.collected_size += csv_size
                        else:
                            self.collected_size += downloaded
                    else:
                        self.collected_size += downloaded
                    
                    file_count += 1
                    print(f"Collected: {self.collected_size / (1024*1024*1024):.2f} GB / {self.max_size_gb} GB")
                    print("-" * 60)
                
                time.sleep(1)  # 서버 부하 방지
        
        print(f"\nCollection completed!")
        print(f"Total files: {file_count}")
        print(f"Total size: {self.collected_size / (1024*1024*1024):.2f} GB")
        print(f"Output directory: {self.output_dir}")


def main():
    parser = argparse.ArgumentParser(description='NYC Taxi Trip Data Collector')
    parser.add_argument('--taxi-type', type=str, default='yellow',
                       choices=['yellow', 'green', 'fhv', 'fhvhv'],
                       help='Taxi type to collect (default: yellow)')
    parser.add_argument('--start-year', type=int, default=2023,
                       help='Start year (default: 2023)')
    parser.add_argument('--start-month', type=int, default=1,
                       help='Start month (default: 1)')
    parser.add_argument('--end-year', type=int, default=None,
                       help='End year (default: current year)')
    parser.add_argument('--end-month', type=int, default=None,
                       help='End month (default: current month)')
    parser.add_argument('--max-size-gb', type=float, default=10.0,
                       help='Maximum collection size in GB (default: 10)')
    parser.add_argument('--max-files', type=int, default=None,
                       help='Maximum number of files to collect')
    parser.add_argument('--output-dir', type=str, default='./data',
                       help='Output directory (default: ./data)')
    
    args = parser.parse_args()
    
    collector = NYCTaxiDataCollector(
        output_dir=args.output_dir,
        max_size_gb=args.max_size_gb
    )
    
    collector.collect_data(
        taxi_type=args.taxi_type,
        start_year=args.start_year,
        start_month=args.start_month,
        end_year=args.end_year,
        end_month=args.end_month,
        max_files=args.max_files
    )


if __name__ == '__main__':
    main()
