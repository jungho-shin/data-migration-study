#!/usr/bin/env python3
"""
CSV to JSON Converter
CSV 파일을 JSON 형식으로 변환하는 유틸리티
"""

import csv
import json
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
import sys
import shutil


class CSVToJSONConverter:
    """CSV를 JSON으로 변환하는 클래스"""
    
    def __init__(self, input_dir: str, output_dir: str, backup_dir: Optional[str] = None):
        """
        Args:
            input_dir: 입력 CSV 파일 디렉토리
            output_dir: 출력 JSON 파일 디렉토리
            backup_dir: 백업 디렉토리 (변환 완료된 CSV 파일 이동)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.backup_dir = Path(backup_dir) if backup_dir else None
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.backup_dir:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def move_to_backup(self, csv_file: Path):
        """변환 완료된 CSV 파일을 백업 디렉토리로 이동"""
        if not self.backup_dir:
            print(f"백업 디렉토리가 설정되지 않았습니다.")
            return False
        
        try:
            # Path 객체로 변환
            csv_file = Path(csv_file)
            
            # 절대 경로가 아니면 input_dir 기준으로 변환
            if not csv_file.is_absolute():
                csv_file = self.input_dir / csv_file
            
            # 정규화 (상대 경로 해결)
            csv_file = csv_file.resolve()
            
            if not csv_file.exists():
                print(f"백업 이동 실패: 파일이 존재하지 않습니다 - {csv_file}")
                return False
            
            backup_path = self.backup_dir.resolve() / csv_file.name
            
            # 백업 디렉토리가 존재하는지 확인
            if not self.backup_dir.exists():
                self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 이미 존재하는 경우 덮어쓰기
            if backup_path.exists():
                backup_path.unlink()
            
            # 파일 이동 (다른 파일 시스템 간 이동을 위해 shutil.move 사용)
            shutil.move(str(csv_file), str(backup_path))
            print(f"백업 이동 완료: {csv_file.name} -> {backup_path}")
            return True
        except Exception as e:
            import traceback
            print(f"백업 이동 실패: {csv_file} - {str(e)}")
            traceback.print_exc()
            return False
    
    def convert_file(self, csv_file: Path, output_file: Optional[Path] = None, 
                    format_type: str = "array", chunk_size: Optional[int] = None) -> Dict[str, Any]:
        """
        단일 CSV 파일을 JSON으로 변환
        
        Args:
            csv_file: 변환할 CSV 파일 경로
            output_file: 출력 JSON 파일 경로 (None이면 자동 생성)
            format_type: JSON 형식 ("array" 또는 "objects")
            chunk_size: 청크 크기 (None이면 전체 변환)
        
        Returns:
            변환 결과 정보
        """
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_file}")
        
        if output_file is None:
            output_file = self.output_dir / f"{csv_file.stem}.json"
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                # CSV 파일 읽기
                reader = csv.DictReader(f)
                
                if format_type == "array":
                    # 배열 형식: [{row1}, {row2}, ...]
                    data = list(reader)
                    
                    if chunk_size:
                        # 청크 단위로 저장
                        total_chunks = (len(data) + chunk_size - 1) // chunk_size
                        saved_files = []
                        
                        for i in range(0, len(data), chunk_size):
                            chunk = data[i:i + chunk_size]
                            chunk_file = self.output_dir / f"{csv_file.stem}_chunk_{i // chunk_size + 1}.json"
                            
                            with open(chunk_file, 'w', encoding='utf-8') as out_f:
                                json.dump(chunk, out_f, ensure_ascii=False, indent=2)
                            
                            saved_files.append(chunk_file.name)
                        
                        return {
                            "success": True,
                            "input_file": csv_file.name,
                            "output_files": saved_files,
                            "total_rows": len(data),
                            "total_chunks": total_chunks,
                            "format": format_type
                        }
                    else:
                        # 전체 파일 저장
                        with open(output_file, 'w', encoding='utf-8') as out_f:
                            json.dump(data, out_f, ensure_ascii=False, indent=2)
                        
                        return {
                            "success": True,
                            "input_file": csv_file.name,
                            "output_file": output_file.name,
                            "total_rows": len(data),
                            "format": format_type
                        }
                
                elif format_type == "objects":
                    # 객체 형식: {"rows": [{row1}, {row2}, ...], "count": N}
                    data = list(reader)
                    result = {
                        "rows": data,
                        "count": len(data),
                        "columns": list(data[0].keys()) if data else []
                    }
                    
                    with open(output_file, 'w', encoding='utf-8') as out_f:
                        json.dump(result, out_f, ensure_ascii=False, indent=2)
                    
                    return {
                        "success": True,
                        "input_file": csv_file.name,
                        "output_file": output_file.name,
                        "total_rows": len(data),
                        "format": format_type
                    }
                
                else:
                    raise ValueError(f"지원하지 않는 형식: {format_type}")
        
        except Exception as e:
            return {
                "success": False,
                "input_file": csv_file.name,
                "error": str(e)
            }
    
    def convert_all(self, format_type: str = "array", chunk_size: Optional[int] = None,
                   pattern: str = "*.csv", move_to_backup: bool = True) -> Dict[str, Any]:
        """
        디렉토리 내 모든 CSV 파일 변환
        
        Args:
            format_type: JSON 형식 ("array" 또는 "objects")
            chunk_size: 청크 크기 (None이면 전체 변환)
            pattern: 파일 패턴 (기본: "*.csv")
            move_to_backup: 변환 완료 후 백업 디렉토리로 이동 여부
        
        Returns:
            변환 결과 요약
        """
        csv_files = list(self.input_dir.glob(pattern))
        
        if not csv_files:
            return {
                "success": False,
                "message": f"CSV 파일을 찾을 수 없습니다: {self.input_dir}/{pattern}",
                "converted": 0,
                "failed": 0
            }
        
        results = []
        success_count = 0
        failed_count = 0
        
        for csv_file in csv_files:
            print(f"변환 중: {csv_file.name}...")
            result = self.convert_file(csv_file, format_type=format_type, chunk_size=chunk_size)
            results.append(result)
            
            if result["success"]:
                success_count += 1
                if "output_file" in result:
                    print(f"  ✓ 완료: {result['output_file']} ({result['total_rows']} 행)")
                elif "output_files" in result:
                    print(f"  ✓ 완료: {result['total_chunks']}개 청크 파일 생성 ({result['total_rows']} 행)")
                
                # 변환 성공 시 백업 디렉토리로 이동
                if move_to_backup:
                    self.move_to_backup(csv_file)
            else:
                failed_count += 1
                print(f"  ✗ 실패: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "total_files": len(csv_files),
            "converted": success_count,
            "failed": failed_count,
            "results": results
        }


def main():
    parser = argparse.ArgumentParser(description='CSV to JSON Converter')
    parser.add_argument('--input-dir', type=str, default='../data',
                       help='입력 CSV 파일 디렉토리 (기본: ../data)')
    parser.add_argument('--output-dir', type=str, default='../data_json',
                       help='출력 JSON 파일 디렉토리 (기본: ../data_json)')
    parser.add_argument('--format', type=str, default='array',
                       choices=['array', 'objects'],
                       help='JSON 형식 (기본: array)')
    parser.add_argument('--chunk-size', type=int, default=None,
                       help='청크 크기 (대용량 파일 분할)')
    parser.add_argument('--file', type=str, default=None,
                       help='특정 파일만 변환 (전체 변환 시 생략)')
    parser.add_argument('--pattern', type=str, default='*.csv',
                       help='파일 패턴 (기본: *.csv)')
    
    args = parser.parse_args()
    
    converter = CSVToJSONConverter(args.input_dir, args.output_dir)
    
    if args.file:
        # 단일 파일 변환
        csv_file = Path(args.input_dir) / args.file
        result = converter.convert_file(csv_file, format_type=args.format, chunk_size=args.chunk_size)
        
        if result["success"]:
            print(f"\n변환 완료!")
            if "output_file" in result:
                print(f"  입력: {result['input_file']}")
                print(f"  출력: {result['output_file']}")
                print(f"  행 수: {result['total_rows']}")
            sys.exit(0)
        else:
            print(f"\n변환 실패: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    else:
        # 전체 파일 변환
        summary = converter.convert_all(format_type=args.format, 
                                       chunk_size=args.chunk_size,
                                       pattern=args.pattern)
        
        if summary["success"]:
            print(f"\n변환 완료!")
            print(f"  전체 파일: {summary['total_files']}개")
            print(f"  성공: {summary['converted']}개")
            print(f"  실패: {summary['failed']}개")
            sys.exit(0)
        else:
            print(f"\n오류: {summary.get('message', 'Unknown error')}")
            sys.exit(1)


if __name__ == '__main__':
    main()
