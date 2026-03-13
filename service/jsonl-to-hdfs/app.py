#!/usr/bin/env python3
"""
JSONL to HDFS Converter Web Service
JSONL 파일을 Spark를 이용하여 HDFS에 저장하는 웹서비스
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import os
import uuid
from datetime import datetime

from jsonl_to_hdfs import JSONLToHDFSConverter

app = FastAPI(
    title="JSONL to HDFS Converter API",
    description="JSONL 파일을 Spark를 이용하여 HDFS에 저장하는 웹서비스",
    version="1.0.0"
)

# 작업 상태 저장소
job_status = {}
job_results = {}

# 기본 설정
DEFAULT_INPUT_DIR = "../data_json"
DEFAULT_HDFS_PATH = "hdfs://namenode:9000/data/jsonl"
DEFAULT_SPARK_MASTER = "spark://spark-master:7077"

# 환경에 따라 경로 자동 감지
if os.path.exists("/app/data_json"):
    DEFAULT_INPUT_DIR = "/app/data_json"


class UploadRequest(BaseModel):
    """업로드 요청 모델"""
    input_dir: str = Field(default=DEFAULT_INPUT_DIR, description="입력 JSONL 파일 디렉토리")
    hdfs_path: str = Field(default=DEFAULT_HDFS_PATH, description="HDFS 저장 경로")
    spark_master: str = Field(default=DEFAULT_SPARK_MASTER, description="Spark Master URL")
    files: Optional[List[str]] = Field(default=None, description="업로드할 파일 목록 (None이면 전체)")
    pattern: str = Field(default="*.jsonl", description="파일 패턴")


class JobStatus(BaseModel):
    """작업 상태 모델"""
    job_id: str
    status: str  # pending, running, completed, failed
    progress: float = 0.0
    message: str = ""
    created_at: str
    updated_at: str
    result: Optional[Dict] = None


def run_uploader(job_id: str, request: UploadRequest):
    """백그라운드에서 업로드 작업 실행"""
    try:
        # Preserve created_at if present
        existing = job_status.get(job_id, {})
        created_at = existing.get("created_at", datetime.now().isoformat())
        job_status[job_id] = {
            "status": "running",
            "progress": 0.0,
            "message": "업로드 작업 시작...",
            "created_at": created_at,
            "updated_at": datetime.now().isoformat()
        }
        
        converter = JSONLToHDFSConverter(
            input_dir=request.input_dir,
            hdfs_path=request.hdfs_path,
            spark_master=request.spark_master
        )
        
        if request.files and len(request.files) > 0:
            # 선택한 파일들만 업로드
            results = []
            for filename in request.files:
                jsonl_file = Path(request.input_dir) / filename
                if jsonl_file.exists():
                    result = converter.upload_file(jsonl_file)
                    results.append(result)
            
            job_results[job_id] = {
                "success": True,
                "total_files": len(request.files),
                "uploaded": sum(1 for r in results if r.get("success")),
                "failed": sum(1 for r in results if not r.get("success")),
                "results": results
            }
        else:
            # 전체 파일 업로드
            result = converter.upload_all(pattern=request.pattern)
            job_results[job_id] = result
        
        # Preserve created_at when marking completed
        created_at = job_status.get(job_id, {}).get("created_at", datetime.now().isoformat())
        uploaded_count = job_results[job_id].get("uploaded", job_results[job_id].get("total_files", 0))
        job_status[job_id] = {
            "status": "completed",
            "progress": 100.0,
            "message": f"업로드 완료: {uploaded_count}개 파일",
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
        <title>JSONL to HDFS Converter</title>
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
                border-bottom: 3px solid #FF9800;
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
                box-sizing: border-box;
            }
            button {
                background-color: #FF9800;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                margin-right: 10px;
            }
            button:hover {
                background-color: #F57C00;
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
            .job-list {
                margin-top: 30px;
            }
            .job-item {
                padding: 15px;
                margin-bottom: 10px;
                background-color: #f9f9f9;
                border-left: 4px solid #FF9800;
                border-radius: 4px;
            }
            .job-item.running {
                border-left-color: #FF9800;
            }
            .job-item.failed {
                border-left-color: #f44336;
            }
            .job-item.completed {
                border-left-color: #4CAF50;
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
                background-color: #FF9800;
                transition: width 0.3s;
            }
            .file-list {
                margin-top: 20px;
                max-height: 400px;
                overflow-y: auto;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 15px;
                background-color: #fafafa;
            }
            .file-item {
                padding: 10px;
                margin-bottom: 8px;
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                display: flex;
                align-items: center;
            }
            .file-item input[type="checkbox"] {
                width: auto;
                margin-right: 10px;
                cursor: pointer;
            }
            .file-item label {
                flex: 1;
                margin: 0;
                cursor: pointer;
                font-weight: normal;
            }
            .file-actions {
                margin-top: 15px;
                display: flex;
                gap: 10px;
            }
            .file-actions button {
                margin: 0;
            }
            .api-docs {
                margin-top: 30px;
                padding: 20px;
                background-color: #fff3e0;
                border-radius: 4px;
            }
            .api-docs a {
                color: #FF9800;
                text-decoration: none;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📦 JSONL to HDFS Converter</h1>
            
            <div class="form-group">
                <label>JSONL 파일 목록:</label>
                <div class="file-list" id="fileList">
                    <p>파일 목록을 불러오는 중...</p>
                </div>
                <div class="file-actions">
                    <button type="button" onclick="selectAll()">전체 선택</button>
                    <button type="button" onclick="deselectAll()">전체 해제</button>
                    <button type="button" onclick="loadFileList()">새로고침</button>
                </div>
            </div>
            
            <form id="uploadForm">
                <div class="form-group">
                    <label for="hdfs_path">HDFS 저장 경로:</label>
                    <input type="text" id="hdfs_path" name="hdfs_path" value="hdfs://namenode:9000/data/jsonl" placeholder="hdfs://namenode:9000/data/jsonl">
                </div>
                
                <button type="submit">선택한 파일 HDFS 업로드</button>
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
            // 체크 상태를 전역 변수로 관리
            let checkedFilesSet = new Set();
            
            // 체크박스 변경 이벤트 리스너
            function setupCheckboxListeners() {
                document.querySelectorAll('#fileList input[type="checkbox"]').forEach(checkbox => {
                    checkbox.addEventListener('change', function() {
                        if (this.checked) {
                            checkedFilesSet.add(this.value);
                        } else {
                            checkedFilesSet.delete(this.value);
                        }
                    });
                });
            }
            
            function getCheckedFiles() {
                return Array.from(checkedFilesSet);
            }
            
            async function loadFileList() {
                try {
                    const response = await fetch('/api/files');
                    if (!response.ok) {
                        throw new Error('파일 목록을 불러올 수 없습니다.');
                    }
                    const data = await response.json();
                    const fileList = document.getElementById('fileList');
                    
                    if (data.jsonl_files.length === 0) {
                        fileList.innerHTML = '<p>JSONL 파일이 없습니다.</p>';
                        checkedFilesSet.clear();
                        return;
                    }
                    
                    const currentFilesSet = new Set(data.jsonl_files);
                    checkedFilesSet = new Set(Array.from(checkedFilesSet).filter(f => currentFilesSet.has(f)));
                    
                    fileList.innerHTML = '';
                    data.jsonl_files.forEach(file => {
                        const fileItem = document.createElement('div');
                        fileItem.className = 'file-item';
                        const isChecked = checkedFilesSet.has(file);
                        const safeId = file.replace(/[^a-zA-Z0-9]/g, '_');
                        fileItem.innerHTML = `
                            <input type="checkbox" id="file_${safeId}" name="files" value="${file}" ${isChecked ? 'checked' : ''}>
                            <label for="file_${safeId}">${file}</label>
                        `;
                        fileList.appendChild(fileItem);
                    });
                    
                    setupCheckboxListeners();
                } catch (error) {
                    const fileList = document.getElementById('fileList');
                    fileList.innerHTML = `<p style="color: red;">오류: ${error.message}</p>`;
                }
            }
            
            function selectAll() {
                document.querySelectorAll('#fileList input[type="checkbox"]').forEach(cb => {
                    cb.checked = true;
                    checkedFilesSet.add(cb.value);
                });
            }
            
            function deselectAll() {
                document.querySelectorAll('#fileList input[type="checkbox"]').forEach(cb => {
                    cb.checked = false;
                    checkedFilesSet.delete(cb.value);
                });
            }
            
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const selectedFiles = Array.from(document.querySelectorAll('#fileList input[type="checkbox"]:checked'))
                    .map(cb => cb.value);
                
                if (selectedFiles.length === 0) {
                    showStatus('error', '업로드할 파일을 선택해주세요.');
                    return;
                }
                
                const formData = new FormData(e.target);
                const data = {
                    hdfs_path: formData.get('hdfs_path'),
                    files: selectedFiles
                };
                
                try {
                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        selectedFiles.forEach(file => checkedFilesSet.delete(file));
                        showStatus('success', `작업이 시작되었습니다. Job ID: ${result.job_id} (${selectedFiles.length}개 파일)`);
                        setTimeout(() => {
                            loadJobs();
                            loadFileList();
                        }, 1000);
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
                    if (!response.ok) {
                        const text = await response.text();
                        console.error('Non-JSON response:', text);
                        return;
                    }
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
                                <strong>결과:</strong> ${JSON.stringify(job.result, null, 2).substring(0, 200)}...
                            ` : ''}
                        `;
                        jobList.appendChild(jobDiv);
                    });
                } catch (error) {
                    console.error('작업 목록 로드 실패:', error);
                }
            }
            
            loadFileList();
            loadJobs();
            setInterval(() => {
                loadFileList();
                loadJobs();
            }, 5000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/upload")
async def start_upload(request: UploadRequest, background_tasks: BackgroundTasks):
    """업로드 작업 시작"""
    job_id = str(uuid.uuid4())
    
    job_status[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "작업 대기 중...",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # 백그라운드 작업으로 실행
    background_tasks.add_task(run_uploader, job_id, request)
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": "HDFS 업로드 작업이 시작되었습니다."
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
async def list_files(input_dir: str = DEFAULT_INPUT_DIR):
    """파일 목록 조회"""
    input_path = Path(input_dir)
    
    jsonl_files = []
    
    if input_path.exists():
        jsonl_files = sorted([f.name for f in input_path.glob("*.jsonl")])
    
    return {
        "input_dir": str(input_dir),
        "jsonl_files": jsonl_files,
        "jsonl_count": len(jsonl_files)
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
    uvicorn.run(app, host="0.0.0.0", port=8002)
