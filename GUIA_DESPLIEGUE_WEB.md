# 🚀 Guía de Despliegue Web - Consultia

Esta guía te muestra cómo desplegar Consultia en producción con soporte completo para **extracción de documentos médicos** (imágenes y PDFs).

## 📋 Tabla de Contenidos

1. [Opción 1: Docker (Recomendado)](#opción-1-docker-recomendado)
2. [Opción 2: Railway.app (Más fácil)](#opción-2-railwayapp-más-fácil)
3. [Opción 3: Render.com](#opción-3-rendercom)
4. [Opción 4: VPS Manual](#opción-4-vps-manual)

---

## Opción 1: Docker (Recomendado)

### ✅ Ventajas
- Funciona en cualquier servidor
- Incluye poppler automáticamente
- Fácil de escalar
- Ambiente consistente

### 📝 Pasos

#### 1. Compilar el Frontend

```bash
cd consultia/frontend
npm run build
```

#### 2. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
OPENAI_API_KEY=tu-clave-api-de-openai
ALLOWED_ORIGINS=https://tu-dominio.com,http://localhost:4200
```

#### 3. Construir la Imagen Docker

```bash
# En la raíz del proyecto (donde está el Dockerfile)
docker build -t consultia:latest .
```

#### 4. Ejecutar el Contenedor

```bash
docker run -d \
  -p 8001:8001 \
  --env-file .env \
  --name consultia \
  consultia:latest
```

#### 5. Acceder a la Aplicación

Abre tu navegador en: `http://localhost:8001`

### 🔄 Con Docker Compose (Más fácil)

```bash
# Ejecutar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

---

## Opción 2: Railway.app (Más fácil)

### ✅ Ventajas
- Deploy automático desde GitHub
- poppler incluido
- SSL/HTTPS gratis
- Escalado automático

### 📝 Pasos

#### 1. Preparar el Proyecto

Crear archivo `railway.toml` en la raíz:

```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "cd consultia/backend && uvicorn server:app --host 0.0.0.0 --port $PORT"
```

#### 2. Subir a GitHub

```bash
git add .
git commit -m "Preparar para Railway"
git push origin main
```

#### 3. Desplegar en Railway

1. Ve a [railway.app](https://railway.app)
2. Click en "New Project"
3. Selecciona "Deploy from GitHub repo"
4. Selecciona tu repositorio
5. Agrega variable de entorno `OPENAI_API_KEY`
6. Railway detectará automáticamente Python y instalará poppler

#### 4. Configurar Dominio

Railway te da un dominio automático como `consultia-production.up.railway.app`

---

## Opción 3: Render.com

### ✅ Ventajas
- Gratis para empezar
- Deploy automático
- SSL incluido

### 📝 Pasos

#### 1. Crear `render.yaml`

```yaml
services:
  - type: web
    name: consultia
    env: python
    plan: free
    buildCommand: |
      apt-get update
      apt-get install -y poppler-utils
      cd consultia/frontend && npm install && npm run build
      cd ../backend && pip install -r requirements.txt
    startCommand: cd consultia/backend && uvicorn server:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OPENAI_API_KEY
        sync: false
```

#### 2. Conectar a Render

1. Ve a [render.com](https://render.com)
2. "New Web Service"
3. Conecta tu repositorio de GitHub
4. Render detectará el `render.yaml` automáticamente

---

## Opción 4: VPS Manual (DigitalOcean, AWS, etc.)

### ✅ Ventajas
- Control total
- Más barato a largo plazo
- Puedes optimizar recursos

### 📝 Pasos (Ubuntu/Debian)

#### 1. Conectar al Servidor

```bash
ssh root@tu-servidor-ip
```

#### 2. Instalar Dependencias del Sistema

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python, Node.js, poppler, nginx
sudo apt install -y python3 python3-pip nodejs npm poppler-utils nginx
```

#### 3. Clonar el Proyecto

```bash
cd /var/www
git clone https://github.com/tu-usuario/consultia.git
cd consultia
```

#### 4. Configurar Backend

```bash
cd consultia/backend

# Instalar dependencias Python
pip3 install -r requirements.txt

# Crear archivo .env
nano .env
# Agregar: OPENAI_API_KEY=tu-clave
```

#### 5. Compilar Frontend

```bash
cd ../frontend
npm install
npm run build
```

#### 6. Configurar Systemd (Para que corra automáticamente)

Crear archivo `/etc/systemd/system/consultia.service`:

```ini
[Unit]
Description=Consultia Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/consultia/consultia/backend
Environment="PATH=/usr/bin"
ExecStart=/usr/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar el servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable consultia
sudo systemctl start consultia
```

#### 7. Configurar Nginx (Proxy Reverso)

Crear `/etc/nginx/sites-available/consultia`:

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Aumentar límite de tamaño para uploads
    client_max_body_size 10M;
}
```

Activar sitio:

```bash
sudo ln -s /etc/nginx/sites-available/consultia /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 8. Configurar SSL con Let's Encrypt (HTTPS)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com
```

---

## 🔧 Configuración de Variables de Entorno

En **producción**, asegúrate de configurar:

```env
# OpenAI API Key (REQUERIDO)
OPENAI_API_KEY=sk-...

# Orígenes permitidos (CORS)
ALLOWED_ORIGINS=https://tu-dominio.com

# Modelo de OpenAI (opcional)
OPENAI_MODEL_TEXT=gpt-4o-mini
OPENAI_MODEL_JSON=gpt-4o-mini

# Puerto (opcional, por defecto 8001)
PORT=8001
```

---

## 📊 Verificar que Todo Funcione

### 1. Backend Health Check

```bash
curl http://tu-dominio.com/
# Debe responder con el HTML del frontend
```

### 2. Probar Upload de Documento

1. Abre la aplicación
2. Click en "Nueva Consulta"
3. Click en "Cargar Documento"
4. Sube una imagen de historia clínica
5. Verifica que los datos se llenen en el formulario

### 3. Ver Logs

**Docker:**
```bash
docker logs consultia
```

**Railway/Render:**
- Ver en el dashboard web

**VPS:**
```bash
sudo journalctl -u consultia -f
```

---

## ❓ Troubleshooting

### Error: "pdf2image not installed"

**Solución:** poppler no está instalado

```bash
# En servidor Ubuntu/Debian
sudo apt-get install poppler-utils

# Con Docker: Ya está incluido en el Dockerfile
```

### Error: "CORS policy"

**Solución:** Configurar ALLOWED_ORIGINS correctamente

```env
ALLOWED_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com
```

### Error: "File too large"

**Solución:** Aumentar límite en nginx

```nginx
client_max_body_size 20M;
```

---

## 🎯 Resumen por Facilidad

| Opción | Dificultad | Tiempo | Costo Mensual | poppler Incluido |
|--------|------------|--------|---------------|------------------|
| **Railway** | ⭐ Fácil | 10 min | $5-20 | ✅ Sí |
| **Render** | ⭐ Fácil | 15 min | Gratis-$7 | ✅ Sí |
| **Docker Local** | ⭐⭐ Medio | 20 min | $0 | ✅ Sí |
| **VPS Manual** | ⭐⭐⭐ Difícil | 60 min | $5-10 | ⚙️ Manual |

---

## 🚀 Siguiente Paso Recomendado

**Para empezar rápido:**
1. Usa **Railway** o **Render** (sin instalar poppler manualmente)
2. Deploy automático desde GitHub
3. SSL/HTTPS incluido gratis

**Para control total:**
1. Usa **Docker** en un VPS
2. Más personalizable
3. Mejor rendimiento

---

## 📝 Checklist Final

Antes de ir a producción:

- [ ] Frontend compilado (`npm run build`)
- [ ] `OPENAI_API_KEY` configurada
- [ ] `ALLOWED_ORIGINS` configurada
- [ ] SSL/HTTPS configurado
- [ ] poppler instalado (para PDFs)
- [ ] Límite de upload ajustado (10MB)
- [ ] Logs monitoreados
- [ ] Backup de base de datos (si aplica)

---

## 🆘 Soporte

Si tienes problemas:

1. Revisa los logs del servidor
2. Verifica la consola del navegador (F12)
3. Prueba primero con imágenes (JPG/PNG) antes que PDFs
4. Asegúrate que la API Key de OpenAI sea válida

---

**¡Listo para producción!** 🎉
