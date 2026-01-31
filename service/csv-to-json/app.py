#!/usr/bin/env python3
"""
CSV to JSON Converter Web Service
CSV 파일을 JSON으로 변환하는 웹서비스
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import os
import uuid
from datetime import datetime

from csv_to_json import CSVToJSONConverter

app = FastAPI(
    title="CSV to JSONL Converter API",
    description="CSV 파일을 JSONL(JSON Lines) 형식으로 변환하는 웹서비스",
    version="1.0.0"
)

# 작업 상태 저장소
job_status = {}
job_results = {}

# 기본 설정
DEFAULT_INPUT_DIR = "../data"
DEFAULT_OUTPUT_DIR = "../data_json"
DEFAULT_BACKUP_DIR = "../data_csv_bk"

# 환경에 따라 경로 자동 감지
if os.path.exists("/app/data"):
    DEFAULT_INPUT_DIR = "/app/data"
    DEFAULT_OUTPUT_DIR = "/app/data_json"
    DEFAULT_BACKUP_DIR = "/app/data_csv_bk"


class ConvertRequest(BaseModel):
    """변환 요청 모델"""
    input_dir: str = Field(default=DEFAULT_INPUT_DIR, description="입력 CSV 파일 디렉토리")
    output_dir: str = Field(default=DEFAULT_OUTPUT_DIR, description="출력 JSON 파일 디렉토리")
    backup_dir: str = Field(default=DEFAULT_BACKUP_DIR, description="백업 디렉토리")
    format_type: str = Field(default="jsonl", description="출력 형식 (기본: jsonl)")
    chunk_size: Optional[int] = Field(default=None, description="청크 크기 (대용량 파일 분할)")
    files: Optional[List[str]] = Field(default=None, description="변환할 파일 목록 (None이면 전체)")
    pattern: str = Field(default="*.csv", description="파일 패턴")


class JobStatus(BaseModel):
    """작업 상태 모델"""
    job_id: str
    status: str  # pending, running, completed, failed
    progress: float = 0.0
    message: str = ""
    created_at: str
    updated_at: str
    result: Optional[Dict] = None


def run_converter(job_id: str, request: ConvertRequest):
    """백그라운드에서 변환 작업 실행"""
    try:
        # Preserve created_at if present
        existing = job_status.get(job_id, {})
        created_at = existing.get("created_at", datetime.now().isoformat())
        job_status[job_id] = {
            "status": "running",
            "progress": 0.0,
            "message": "변환 작업 시작...",
            "created_at": created_at,
            "updated_at": datetime.now().isoformat()
        }
        
        converter = CSVToJSONConverter(request.input_dir, request.output_dir, request.backup_dir)
        
        if request.files and len(request.files) > 0:
            # 선택한 파일들만 변환
            results = []
            for filename in request.files:
                csv_file = Path(request.input_dir) / filename
                if csv_file.exists():
                    result = converter.convert_file(
                        csv_file,
                        format_type=request.format_type,
                        chunk_size=request.chunk_size
                    )
                    if result.get("success"):
                        # 변환 성공 시 백업 디렉토리로 이동
                        # 파일이 여전히 존재하는지 확인
                        if csv_file.exists():
                            backup_result = converter.move_to_backup(csv_file)
                            if not backup_result:
                                result["backup_moved"] = False
                                result["backup_error"] = "백업 이동 실패"
                            else:
                                result["backup_moved"] = True
                        else:
                            result["backup_moved"] = False
                            result["backup_error"] = "변환 후 파일이 존재하지 않음"
                    results.append(result)
            
            job_results[job_id] = {
                "success": True,
                "total_files": len(request.files),
                "converted": sum(1 for r in results if r.get("success")),
                "failed": sum(1 for r in results if not r.get("success")),
                "results": results
            }
        else:
            # 전체 파일 변환
            result = converter.convert_all(
                format_type=request.format_type,
                chunk_size=request.chunk_size,
                pattern=request.pattern,
                move_to_backup=True
            )
            job_results[job_id] = result
        
        # Preserve created_at when marking completed
        created_at = job_status.get(job_id, {}).get("created_at", datetime.now().isoformat())
        converted_count = job_results[job_id].get("converted", job_results[job_id].get("total_files", 0))
        job_status[job_id] = {
            "status": "completed",
            "progress": 100.0,
            "message": f"변환 완료: {converted_count}개 파일",
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
        <title>CSV to JSON Converter</title>
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
                border-bottom: 3px solid #2196F3;
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
                background-color: #2196F3;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                margin-right: 10px;
            }
            button:hover {
                background-color: #1976D2;
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
                border-left: 4px solid #2196F3;
                border-radius: 4px;
            }
            .job-item.running {
                border-left-color: #2196F3;
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
                background-color: #2196F3;
                transition: width 0.3s;
            }
            .api-docs {
                margin-top: 30px;
                padding: 20px;
                background-color: #e3f2fd;
                border-radius: 4px;
            }
            .api-docs a {
                color: #2196F3;
                text-decoration: none;
                font-weight: bold;
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
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📄 CSV to JSON Converter</h1>
            
            <div class="form-group">
                <label>CSV 파일 목록:</label>
                <div class="file-list" id="fileList">
                    <p>파일 목록을 불러오는 중...</p>
                </div>
                <div class="file-actions">
                    <button type="button" onclick="selectAll()">전체 선택</button>
                    <button type="button" onclick="deselectAll()">전체 해제</button>
                    <button type="button" onclick="loadFileList()">새로고침</button>
                </div>
            </div>
            
            <form id="convertForm">
                <div class="form-group">
                    <label for="chunk_size">청크 크기 (선택, 대용량 파일 분할용):</label>
                    <input type="number" id="chunk_size" name="chunk_size" min="1" placeholder="비워두면 전체 변환">
                    <small style="color: #666; display: block; margin-top: 5px;">각 CSV 행이 JSONL 형식(한 줄에 하나의 JSON 객체)으로 변환됩니다.</small>
                </div>
                
                <button type="submit">선택한 파일 변환 시작</button>
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
                // 전역 변수에서 체크된 파일 목록 반환
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
                    
                    if (data.csv_files.length === 0) {
                        fileList.innerHTML = '<p>CSV 파일이 없습니다.</p>';
                        checkedFilesSet.clear(); // 파일이 없으면 체크 상태 초기화
                        return;
                    }
                    
                    // 파일 목록이 변경되었는지 확인 (삭제된 파일의 체크 상태 제거)
                    const currentFilesSet = new Set(data.csv_files);
                    checkedFilesSet = new Set(Array.from(checkedFilesSet).filter(f => currentFilesSet.has(f)));
                    
                    fileList.innerHTML = '';
                    data.csv_files.forEach(file => {
                        const fileItem = document.createElement('div');
                        fileItem.className = 'file-item';
                        const isChecked = checkedFilesSet.has(file);
                        // 파일명에 특수문자가 있을 수 있으므로 ID는 안전하게 처리
                        const safeId = file.replace(/[^a-zA-Z0-9]/g, '_');
                        fileItem.innerHTML = `
                            <input type="checkbox" id="file_${safeId}" name="files" value="${file}" ${isChecked ? 'checked' : ''}>
                            <label for="file_${safeId}">${file}</label>
                        `;
                        fileList.appendChild(fileItem);
                    });
                    
                    // 체크박스 이벤트 리스너 설정
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
            
            document.getElementById('convertForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const selectedFiles = Array.from(document.querySelectorAll('#fileList input[type="checkbox"]:checked'))
                    .map(cb => cb.value);
                
                if (selectedFiles.length === 0) {
                    showStatus('error', '변환할 파일을 선택해주세요.');
                    return;
                }
                
                const formData = new FormData(e.target);
                const data = {
                    format_type: "jsonl",  // JSONL 형식으로 고정
                    files: selectedFiles
                };
                
                const chunkSize = formData.get('chunk_size');
                if (chunkSize) data.chunk_size = parseInt(chunkSize);
                
                try {
                    const response = await fetch('/api/convert', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        // 변환 시작된 파일들의 체크 상태 제거
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
            
            // 페이지 로드 시 파일 목록 및 작업 목록 로드
            loadFileList();
            loadJobs();
            // 5초마다 자동 새로고침
            setInterval(() => {
                loadFileList();
                loadJobs();
            }, 5000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/convert")
async def start_conversion(request: ConvertRequest, background_tasks: BackgroundTasks):
    """변환 작업 시작"""
    job_id = str(uuid.uuid4())
    
    job_status[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "작업 대기 중...",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # 백그라운드 작업으로 실행
    background_tasks.add_task(run_converter, job_id, request)
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": "변환 작업이 시작되었습니다."
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
async def list_files(input_dir: str = DEFAULT_INPUT_DIR, output_dir: str = DEFAULT_OUTPUT_DIR):
    """파일 목록 조회"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    csv_files = []
    json_files = []
    
    if input_path.exists():
        csv_files = sorted([f.name for f in input_path.glob("*.csv")])
    
    if output_path.exists():
        json_files = sorted([f.name for f in output_path.glob("*.jsonl")])
    
    return {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "csv_files": csv_files,
        "json_files": json_files,
        "csv_count": len(csv_files),
        "json_count": len(json_files)
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
    uvicorn.run(app, host="0.0.0.0", port=8001)
