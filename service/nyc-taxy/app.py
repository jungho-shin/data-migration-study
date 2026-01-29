#!/usr/bin/env python3
"""
NYC Taxi Data Collector Web Service
뉴욕 택시 운행 데이터 수집 웹서비스
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import asyncio
import threading
from pathlib import Path
import json
from datetime import datetime
import uuid

from data_collector import NYCTaxiDataCollector

app = FastAPI(
    title="NYC Taxi Data Collector API",
    description="뉴욕 택시 운행 데이터 수집 웹서비스",
    version="1.0.0"
)

# 작업 상태 저장소 (실제 운영 환경에서는 Redis나 DB 사용 권장)
job_status = {}
job_results = {}

# 기본 설정
DEFAULT_OUTPUT_DIR = "./data"
DEFAULT_MAX_SIZE_GB = 10.0


class CollectRequest(BaseModel):
    """데이터 수집 요청 모델"""
    taxi_type: str = Field(default="yellow", description="택시 타입 (yellow, green, fhv, fhvhv)")
    start_year: int = Field(default=2023, description="시작 연도")
    start_month: int = Field(default=1, ge=1, le=12, description="시작 월")
    end_year: Optional[int] = Field(default=None, description="종료 연도")
    end_month: Optional[int] = Field(default=None, ge=1, le=12, description="종료 월")
    max_size_gb: float = Field(default=10.0, gt=0, description="최대 수집 크기 (GB)")
    max_files: Optional[int] = Field(default=None, gt=0, description="최대 파일 수")
    output_dir: str = Field(default=DEFAULT_OUTPUT_DIR, description="출력 디렉토리")


class JobStatus(BaseModel):
    """작업 상태 모델"""
    job_id: str
    status: str  # pending, running, completed, failed
    progress: float = 0.0
    message: str = ""
    created_at: str
    updated_at: str
    result: Optional[Dict] = None


def run_collector(job_id: str, request: CollectRequest):
    """백그라운드에서 데이터 수집 실행"""
    try:
        # Preserve created_at if present, otherwise set it
        existing = job_status.get(job_id, {})
        created_at = existing.get("created_at", datetime.now().isoformat())
        job_status[job_id] = {
            "status": "running",
            "progress": 0.0,
            "message": "데이터 수집 시작...",
            "created_at": created_at,
            "updated_at": datetime.now().isoformat()
        }
        
        collector = NYCTaxiDataCollector(
            output_dir=request.output_dir,
            max_size_gb=request.max_size_gb
        )
        
        # 콜백 함수로 진행률 업데이트
        original_collect = collector.collect_data
        
        def collect_with_progress(*args, **kwargs):
            # 간단한 진행률 추적 (실제로는 더 정교한 구현 필요)
            job_status[job_id]["message"] = "데이터 다운로드 중..."
            result = original_collect(*args, **kwargs)
            return result
        
        collector.collect_data = collect_with_progress
        
        collector.collect_data(
            taxi_type=request.taxi_type,
            start_year=request.start_year,
            start_month=request.start_month,
            end_year=request.end_year,
            end_month=request.end_month,
            max_files=request.max_files
        )
        
        # 결과 수집
        output_path = Path(request.output_dir)
        files = list(output_path.glob("*.csv"))
        total_size = sum(f.stat().st_size for f in files)
        
        job_results[job_id] = {
            "files_count": len(files),
            "total_size_gb": total_size / (1024 * 1024 * 1024),
            "files": [f.name for f in files]
        }
        
        # Preserve created_at when marking completed
        created_at = job_status.get(job_id, {}).get("created_at", datetime.now().isoformat())
        job_status[job_id] = {
            "status": "completed",
            "progress": 100.0,
            "message": f"수집 완료: {len(files)}개 파일, {total_size / (1024*1024*1024):.2f} GB",
            "created_at": created_at,
            "updated_at": datetime.now().isoformat(),
            "result": job_results[job_id]
        }
        
    except Exception as e:
        created_at = job_status.get(job_id, {}).get("created_at", datetime.now().isoformat())
        job_status[job_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": f"오류 발생: {str(e)}",
            "created_at": created_at,
            "updated_at": datetime.now().isoformat()
        }


@app.get("/", response_class=HTMLResponse)
async def root():
    """웹 인터페이스"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>NYC Taxi Data Collector</title>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #555;
            }
            input, select {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                margin-right: 10px;
            }
            button:hover {
                background-color: #45a049;
            }
            .status {
                margin-top: 20px;
                padding: 15px;
                border-radius: 4px;
                display: none;
            }
            .status.success {
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
            }
            .status.error {
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
            }
            .status.info {
                background-color: #d1ecf1;
                border: 1px solid #bee5eb;
                color: #0c5460;
            }
            .job-list {
                margin-top: 30px;
            }
            .job-item {
                padding: 15px;
                margin-bottom: 10px;
                background-color: #f9f9f9;
                border-left: 4px solid #4CAF50;
                border-radius: 4px;
            }
            .job-item.running {
                border-left-color: #2196F3;
            }
            .job-item.failed {
                border-left-color: #f44336;
            }
            .progress-bar {
                width: 100%;
                height: 20px;
                background-color: #e0e0e0;
                border-radius: 10px;
                overflow: hidden;
                margin-top: 10px;
            }
            .progress-fill {
                height: 100%;
                background-color: #4CAF50;
                transition: width 0.3s;
            }
            .api-docs {
                margin-top: 30px;
                padding: 20px;
                background-color: #e8f5e9;
                border-radius: 4px;
            }
            .api-docs a {
                color: #4CAF50;
                text-decoration: none;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚕 NYC Taxi Data Collector</h1>
            
            <form id="collectForm">
                <div class="form-group">
                    <label for="taxi_type">택시 타입:</label>
                    <select id="taxi_type" name="taxi_type">
                        <option value="yellow">Yellow Taxi</option>
                        <option value="green">Green Taxi</option>
                        <option value="fhv">For-Hire Vehicle (FHV)</option>
                        <option value="fhvhv">High Volume FHV</option>
                    </select>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div class="form-group">
                        <label for="start_year">시작 연도:</label>
                        <input type="number" id="start_year" name="start_year" value="2023" min="2009" max="2024">
                    </div>
                    
                    <div class="form-group">
                        <label for="start_month">시작 월:</label>
                        <input type="number" id="start_month" name="start_month" value="1" min="1" max="12">
                    </div>
                    
                    <div class="form-group">
                        <label for="end_year">종료 연도 (선택):</label>
                        <input type="number" id="end_year" name="end_year" min="2009" max="2024" placeholder="비워두면 현재 연도">
                    </div>
                    
                    <div class="form-group">
                        <label for="end_month">종료 월 (선택):</label>
                        <input type="number" id="end_month" name="end_month" min="1" max="12" placeholder="비워두면 현재 월">
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div class="form-group">
                        <label for="max_size_gb">최대 크기 (GB):</label>
                        <input type="number" id="max_size_gb" name="max_size_gb" value="10" step="0.1" min="0.1">
                    </div>
                    
                    <div class="form-group">
                        <label for="max_files">최대 파일 수 (선택):</label>
                        <input type="number" id="max_files" name="max_files" min="1" placeholder="비워두면 제한 없음">
                    </div>
                </div>
                
                <button type="submit">데이터 수집 시작</button>
                <button type="button" onclick="loadJobs()">작업 목록 새로고침</button>
            </form>
            
            <div id="status" class="status"></div>
            
            <div class="job-list">
                <h2>작업 목록</h2>
                <div id="jobList"></div>
            </div>
            
            <div class="api-docs">
                <h3>📚 API 문서</h3>
                <p>REST API 문서는 <a href="/docs">/docs</a>에서 확인할 수 있습니다.</p>
                <p>대체 문서는 <a href="/redoc">/redoc</a>에서도 제공됩니다.</p>
            </div>
        </div>
        
        <script>
            document.getElementById('collectForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const data = {
                    taxi_type: formData.get('taxi_type'),
                    start_year: parseInt(formData.get('start_year')),
                    start_month: parseInt(formData.get('start_month')),
                    max_size_gb: parseFloat(formData.get('max_size_gb'))
                };
                
                const endYear = formData.get('end_year');
                const endMonth = formData.get('end_month');
                const maxFiles = formData.get('max_files');
                
                if (endYear) data.end_year = parseInt(endYear);
                if (endMonth) data.end_month = parseInt(endMonth);
                if (maxFiles) data.max_files = parseInt(maxFiles);
                
                try {
                    const response = await fetch('/api/collect', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        showStatus('success', `작업이 시작되었습니다. Job ID: ${result.job_id}`);
                        setTimeout(loadJobs, 1000);
                    } else {
                        showStatus('error', result.detail || '오류가 발생했습니다.');
                    }
                } catch (error) {
                    showStatus('error', '요청 중 오류가 발생했습니다: ' + error.message);
                }
            });
            
            function showStatus(type, message) {
                const statusDiv = document.getElementById('status');
                statusDiv.className = 'status ' + type;
                statusDiv.textContent = message;
                statusDiv.style.display = 'block';
                
                if (type === 'success') {
                    setTimeout(() => statusDiv.style.display = 'none', 5000);
                }
            }
            
            async function loadJobs() {
                try {
                    const response = await fetch('/api/jobs');
                    const jobs = await response.json();
                    
                    const jobList = document.getElementById('jobList');
                    jobList.innerHTML = '';
                    
                    if (jobs.length === 0) {
                        jobList.innerHTML = '<p>작업이 없습니다.</p>';
                        return;
                    }
                    
                    jobs.forEach(job => {
                        const jobDiv = document.createElement('div');
                        jobDiv.className = 'job-item ' + job.status;
                        jobDiv.innerHTML = `
                            <strong>Job ID:</strong> ${job.job_id}<br>
                            <strong>상태:</strong> ${job.status}<br>
                            <strong>메시지:</strong> ${job.message}<br>
                            <strong>생성 시간:</strong> ${job.created_at}<br>
                            ${job.status === 'running' ? `
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${job.progress}%"></div>
                                </div>
                            ` : ''}
                            ${job.result ? `
                                <strong>결과:</strong> ${job.result.files_count}개 파일, ${job.result.total_size_gb.toFixed(2)} GB
                            ` : ''}
                        `;
                        jobList.appendChild(jobDiv);
                    });
                } catch (error) {
                    console.error('작업 목록 로드 실패:', error);
                }
            }
            
            // 페이지 로드 시 작업 목록 로드
            loadJobs();
            // 5초마다 자동 새로고침
            setInterval(loadJobs, 5000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/collect")
async def start_collection(request: CollectRequest, background_tasks: BackgroundTasks):
    """데이터 수집 작업 시작"""
    job_id = str(uuid.uuid4())
    
    job_status[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "작업 대기 중...",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # 백그라운드 작업으로 실행
    background_tasks.add_task(run_collector, job_id, request)
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": "데이터 수집 작업이 시작되었습니다."
    }


@app.get("/api/jobs")
async def list_jobs():
    """모든 작업 목록 조회"""
    try:
        jobs = []
        for job_id, status in job_status.items():
            jobs.append({
                "job_id": job_id,
                **status
            })
        # 최신 작업부터 정렬 (created_at이 없을 수 있으므로 get 사용)
        jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return jobs
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "error": str(e)})


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """특정 작업 상태 조회"""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        **job_status[job_id]
    }


@app.get("/api/files")
async def list_files(output_dir: str = DEFAULT_OUTPUT_DIR):
    """수집된 파일 목록 조회"""
    output_path = Path(output_dir)
    if not output_path.exists():
        return {"files": [], "total_size_gb": 0, "count": 0}
    
    files = list(output_path.glob("*.csv"))
    total_size = sum(f.stat().st_size for f in files)
    
    return {
        "files": [
            {
                "name": f.name,
                "size_mb": f.stat().st_size / (1024 * 1024),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            }
            for f in files
        ],
        "total_size_gb": total_size / (1024 * 1024 * 1024),
        "count": len(files)
    }


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """작업 삭제"""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    del job_status[job_id]
    if job_id in job_results:
        del job_results[job_id]
    
    return {"message": "Job deleted successfully"}


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_jobs": sum(1 for s in job_status.values() if s["status"] == "running")
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
