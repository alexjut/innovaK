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

# Exponer el puerto 8000
EXPOSE 8000

# Comando de inicio
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
