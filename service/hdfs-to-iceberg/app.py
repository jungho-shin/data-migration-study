#!/usr/bin/env python3
"""
HDFS to Iceberg Converter Web Service
HDFS의 JSON 파일을 Spark를 이용하여 Iceberg 테이블에 저장하는 웹서비스
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import os
import uuid
from datetime import datetime

from hdfs_to_iceberg import HDFSToIcebergConverter

app = FastAPI(
    title="HDFS to Iceberg Converter API",
    description="HDFS의 JSON 파일을 Spark를 이용하여 Iceberg 테이블에 저장하는 웹서비스",
    version="1.0.0"
)

# 작업 상태 저장소
job_status = {}
job_results = {}

# 기본 설정
DEFAULT_HDFS_PATH = "hdfs://namenode:9000/data/jsonl/*.json"
DEFAULT_CATALOG = "spark_catalog"
DEFAULT_DATABASE = "default"
DEFAULT_TABLE = "nyc_taxi"
DEFAULT_SPARK_MASTER = "spark://spark-master:7077"


class MigrateRequest(BaseModel):
    """마이그레이션 요청 모델"""
    hdfs_path: str = Field(default=DEFAULT_HDFS_PATH, description="HDFS에서 읽을 JSON 파일 경로")
    catalog: str = Field(default=DEFAULT_CATALOG, description="Iceberg 카탈로그 이름")
    database: str = Field(default=DEFAULT_DATABASE, description="데이터베이스 이름")
    table: str = Field(default=DEFAULT_TABLE, description="테이블 이름")
    spark_master: str = Field(default=DEFAULT_SPARK_MASTER, description="Spark Master URL")


class JobStatus(BaseModel):
    """작업 상태 모델"""
    job_id: str
    status: str  # pending, running, completed, failed
    progress: float = 0.0
    message: str = ""
    created_at: str
    updated_at: str
    result: Optional[Dict] = None


def run_migrator(job_id: str, request: MigrateRequest):
    """백그라운드에서 마이그레이션 작업 실행"""
    try:
        # Preserve created_at if present
        existing = job_status.get(job_id, {})
        created_at = existing.get("created_at", datetime.now().isoformat())
        job_status[job_id] = {
            "status": "running",
            "progress": 0.0,
            "message": "마이그레이션 작업 시작...",
            "created_at": created_at,
            "updated_at": datetime.now().isoformat()
        }
        
        converter = HDFSToIcebergConverter(
            hdfs_path=request.hdfs_path,
            catalog_name=request.catalog,
            database_name=request.database,
            table_name=request.table,
            spark_master=request.spark_master
        )
        
        job_status[job_id]["message"] = "HDFS에서 데이터 읽는 중..."
        job_status[job_id]["progress"] = 20.0
        job_status[job_id]["updated_at"] = datetime.now().isoformat()
        
        result = converter.migrate_to_iceberg()
        
        # Preserve created_at when marking completed
        created_at = job_status.get(job_id, {}).get("created_at", datetime.now().isoformat())
        
        if result.get("success"):
            job_status[job_id] = {
                "status": "completed",
                "progress": 100.0,
                "message": "마이그레이션 완료",
                "created_at": created_at,
                "updated_at": datetime.now().isoformat()
            }
            job_results[job_id] = result
        else:
            job_status[job_id] = {
                "status": "failed",
                "progress": 0.0,
                "message": f"마이그레이션 실패: {result.get('error', 'Unknown error')}",
                "created_at": created_at,
                "updated_at": datetime.now().isoformat()
            }
            job_results[job_id] = result
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        created_at = job_status.get(job_id, {}).get("created_at", datetime.now().isoformat())
        job_status[job_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": f"오류 발생: {str(e)}",
            "created_at": created_at,
            "updated_at": datetime.now().isoformat()
        }
        job_results[job_id] = {
            "success": False,
            "error": str(e)
        }


@app.get("/", response_class=HTMLResponse)
async def root():
    """웹 UI"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>HDFS to Iceberg Converter</title>
        <meta charset="utf-8">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            .header p {
                opacity: 0.9;
                font-size: 1.1em;
            }
            .content {
                padding: 40px;
            }
            .form-group {
                margin-bottom: 25px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                color: #333;
                font-size: 14px;
            }
            input[type="text"] {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            input[type="text"]:focus {
                outline: none;
                border-color: #667eea;
            }
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
                width: 100%;
                margin-top: 10px;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            .jobs-section {
                margin-top: 40px;
                padding-top: 40px;
                border-top: 2px solid #e0e0e0;
            }
            .jobs-section h2 {
                margin-bottom: 20px;
                color: #333;
            }
            .job-item {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 15px;
                border-left: 4px solid #667eea;
            }
            .job-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .job-id {
                font-family: monospace;
                color: #667eea;
                font-weight: 600;
            }
            .job-status {
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
            }
            .status-pending { background: #fff3cd; color: #856404; }
            .status-running { background: #d1ecf1; color: #0c5460; }
            .status-completed { background: #d4edda; color: #155724; }
            .status-failed { background: #f8d7da; color: #721c24; }
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
                overflow: hidden;
                margin: 10px 0;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                transition: width 0.3s;
            }
            .job-message {
                color: #666;
                font-size: 14px;
                margin-top: 10px;
            }
            .job-result {
                margin-top: 15px;
                padding: 15px;
                background: white;
                border-radius: 6px;
                font-size: 13px;
            }
            .result-item {
                margin: 5px 0;
            }
            .result-label {
                font-weight: 600;
                color: #333;
            }
            .error {
                color: #dc3545;
                background: #f8d7da;
                padding: 15px;
                border-radius: 6px;
                margin-top: 15px;
            }
            .refresh-btn {
                background: #6c757d;
                width: auto;
                margin-top: 0;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 HDFS to Iceberg Converter</h1>
                <p>HDFS의 JSON 파일을 Iceberg 테이블로 마이그레이션</p>
            </div>
            <div class="content">
                <form id="migrateForm">
                    <div class="form-group">
                        <label for="hdfs_path">HDFS 경로 (JSON 파일)</label>
                        <input type="text" id="hdfs_path" name="hdfs_path" value="hdfs://namenode:9000/data/jsonl/*.json" required>
                    </div>
                    <div class="form-group">
                        <label for="catalog">카탈로그 이름</label>
                        <input type="text" id="catalog" name="catalog" value="spark_catalog" required>
                    </div>
                    <div class="form-group">
                        <label for="database">데이터베이스 이름</label>
                        <input type="text" id="database" name="database" value="default" required>
                    </div>
                    <div class="form-group">
                        <label for="table">테이블 이름</label>
                        <input type="text" id="table" name="table" value="nyc_taxi" required>
                    </div>
                    <div class="form-group">
                        <label for="spark_master">Spark Master URL</label>
                        <input type="text" id="spark_master" name="spark_master" value="spark://spark-master:7077" required>
                    </div>
                    <button type="submit" id="submitBtn">마이그레이션 시작</button>
                </form>
                
                <div class="jobs-section">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h2>작업 목록</h2>
                        <button class="refresh-btn" onclick="loadJobs()">새로고침</button>
                    </div>
                    <div id="jobsList"></div>
                </div>
            </div>
        </div>
        
        <script>
            document.getElementById('migrateForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const submitBtn = document.getElementById('submitBtn');
                submitBtn.disabled = true;
                submitBtn.textContent = '처리 중...';
                
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData);
                
                try {
                    const response = await fetch('/api/migrate', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data)
                    });
                    
                    if (!response.ok) {
                        throw new Error('마이그레이션 시작 실패');
                    }
                    
                    const result = await response.json();
                    alert(`작업이 시작되었습니다!\\n작업 ID: ${result.job_id}`);
                    
                    // 폼 초기화
                    e.target.reset();
                    
                    // 작업 목록 새로고침
                    setTimeout(loadJobs, 1000);
                    
                } catch (error) {
                    alert('오류: ' + error.message);
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.textContent = '마이그레이션 시작';
                }
            });
            
            async function loadJobs() {
                try {
                    const response = await fetch('/api/jobs');
                    if (!response.ok) {
                        throw new Error('작업 목록을 불러올 수 없습니다.');
                    }
                    const jobs = await response.json();
                    const jobsList = document.getElementById('jobsList');
                    
                    if (jobs.length === 0) {
                        jobsList.innerHTML = '<p>작업이 없습니다.</p>';
                        return;
                    }
                    
                    jobsList.innerHTML = jobs.map(job => {
                        const statusClass = `status-${job.status}`;
                        const progress = job.progress || 0;
                        const result = job.result ? `
                            <div class="job-result">
                                ${job.result.success ? `
                                    <div class="result-item"><span class="result-label">HDFS 경로:</span> ${job.result.hdfs_path || 'N/A'}</div>
                                    <div class="result-item"><span class="result-label">테이블:</span> ${job.result.table_name || 'N/A'}</div>
                                    <div class="result-item"><span class="result-label">행 수:</span> ${job.result.total_rows || 0}</div>
                                ` : `
                                    <div class="error">오류: ${job.result.error || 'Unknown error'}</div>
                                `}
                            </div>
                        ` : '';
                        
                        return `
                            <div class="job-item">
                                <div class="job-header">
                                    <span class="job-id">${job.job_id}</span>
                                    <span class="job-status ${statusClass}">${job.status}</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${progress}%"></div>
                                </div>
                                <div class="job-message">${job.message || ''}</div>
                                <div style="font-size: 12px; color: #999; margin-top: 5px;">
                                    생성: ${new Date(job.created_at).toLocaleString('ko-KR')} | 
                                    업데이트: ${new Date(job.updated_at).toLocaleString('ko-KR')}
                                </div>
                                ${result}
                            </div>
                        `;
                    }).join('');
                } catch (error) {
                    document.getElementById('jobsList').innerHTML = `<p style="color: red;">오류: ${error.message}</p>`;
                }
            }
            
            // 페이지 로드 시 작업 목록 불러오기
            loadJobs();
            
            // 5초마다 자동 새로고침
            setInterval(loadJobs, 5000);
        </script>
    </body>
    </html>
    """


@app.get("/health")
async def health():
    """헬스 체크"""
    return {"status": "healthy"}


@app.post("/api/migrate", response_model=Dict[str, str])
async def start_migration(request: MigrateRequest, background_tasks: BackgroundTasks):
    """마이그레이션 작업 시작"""
    job_id = str(uuid.uuid4())
    
    job_status[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "작업 대기 중...",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(run_migrator, job_id, request)
    
    return {"job_id": job_id, "status": "pending"}


@app.get("/api/jobs", response_model=List[JobStatus])
async def list_jobs():
    """작업 목록 조회"""
    try:
        jobs = []
        for job_id, status in job_status.items():
            job = {
                "job_id": job_id,
                "status": status.get("status", "unknown"),
                "progress": status.get("progress", 0.0),
                "message": status.get("message", ""),
                "created_at": status.get("created_at", ""),
                "updated_at": status.get("updated_at", ""),
                "result": job_results.get(job_id)
            }
            jobs.append(job)
        
        # created_at 기준으로 정렬 (최신순)
        jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return jobs
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    """특정 작업 조회"""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    status = job_status[job_id]
    return {
        "job_id": job_id,
        "status": status.get("status", "unknown"),
        "progress": status.get("progress", 0.0),
        "message": status.get("message", ""),
        "created_at": status.get("created_at", ""),
        "updated_at": status.get("updated_at", ""),
        "result": job_results.get(job_id)
    }
