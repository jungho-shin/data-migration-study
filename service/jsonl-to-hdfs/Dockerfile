FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Java 8 설치 (Spark 3.2.0과 호환)
# Adoptium OpenJDK 8 설치
RUN wget -q https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u392-b08/OpenJDK8U-jdk_x64_linux_hotspot_8u392b08.tar.gz && \
    tar -xzf OpenJDK8U-jdk_x64_linux_hotspot_8u392b08.tar.gz -C /opt && \
    mv /opt/jdk8u392-b08 /opt/java8 && \
    rm OpenJDK8U-jdk_x64_linux_hotspot_8u392b08.tar.gz

# Java 환경 변수 설정
ENV JAVA_HOME=/opt/java8
ENV PATH=$PATH:$JAVA_HOME/bin

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 데이터 디렉토리 생성
RUN mkdir -p /app/data_json

# 포트 노출
EXPOSE 8002

# 애플리케이션 실행
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
