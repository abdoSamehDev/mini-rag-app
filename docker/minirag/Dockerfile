FROM ghcr.io/astral-sh/uv:0.11.7-python3.14-trixie-slim

WORKDIR /app

#Install additonal system dependencies for lxml and other packages
#Each layer is installed once and cached when buliding again until there is some change so it will reinstall/rerun from the changed layer until the end of the dockerfile
#So it's better to keep all the unchanging layers at the top of file and changing layers at the end of file to take advantage of caching and reduce build time
RUN apt-get update && apt-get install -y \
    build-essential \
    libavif-dev pkg-config \
    libjpeg-dev \
    gcc unzip zip \
    python3-dev \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* 
# lists that has been downloaded with package so del them to reduce image size

COPY src/requirements.txt .

RUN uv pip install -r requirements.txt --system

COPY src/ .

#Create dir structure for Alembic
RUN mkdir -p /app/models/db_schemes/minirag/ 
#-p to ignore error if the dir exists already

COPY docker/minirag/alembic.ini /app/models/db_schemes/minirag/alembic.ini

COPY docker/minirag/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]

#Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]