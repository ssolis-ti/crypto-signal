# Imagen base con Python 3.12+
FROM python:3.12-slim

# Instalar dependencias de sistema para TA-Lib
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Instalar TA-Lib desde source
RUN cd /tmp && \
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    rm -rf /tmp/ta-lib*

# Copiar aplicación
COPY ./app /app
WORKDIR /app

# Instalar dependencias Python
RUN pip install --upgrade pip
RUN pip install -r requirements-step-1.txt
RUN pip install -r requirements-step-2.txt

# Ejecutar
CMD ["python", "app.py"]
