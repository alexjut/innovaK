FROM python:3.10-slim

# Instalación de dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    pkg-config \
    libcairo2-dev \
    libgirepository1.0-dev \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    libffi-dev \
    curl \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Instalación de Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

# Crear carpeta de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar paquetes de Python
RUN pip install --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Copiar todo el código fuente
COPY . .

# Instalar paquetes npm y compilar SCSS con webpack
WORKDIR /app/static
RUN npm install && npm run build
WORKDIR /app

# Copiar variables de entorno si existen
COPY .env .env

# Puerto coherente con docker-compose.yml (gunicorn 8032)
EXPOSE 8032

# CMD coherente con docker-compose.yml (que de todos modos lo sobrescribe).
# Si alguien corre `docker run` sin compose, arranca gunicorn correctamente.
CMD ["gunicorn", "core.wsgi:application", \
     "--bind", "0.0.0.0:8032", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
