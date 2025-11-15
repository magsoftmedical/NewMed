# 🟣 Despliegue en Heroku - Consultia

Guía paso a paso para desplegar Consultia en Heroku con soporte completo para PDFs.

## ✅ Ventajas de Heroku

- Deploy super fácil con Git
- poppler se instala automáticamente con buildpacks
- SSL/HTTPS gratis
- Escalado sencillo
- Interfaz web amigable

---

## 📋 Prerrequisitos

1. Cuenta en [Heroku](https://www.heroku.com) (gratis o de pago)
2. [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) instalado
3. Git configurado en tu proyecto

---

## 🚀 Pasos para Desplegar

### 1. Instalar Heroku CLI (si no lo tienes)

```bash
# Windows (con Chocolatey)
choco install heroku-cli

# O descarga desde: https://devcenter.heroku.com/articles/heroku-cli
```

### 2. Crear Archivos de Configuración

#### A. Crear `Procfile` (en la raíz del proyecto)

```bash
web: cd consultia/backend && uvicorn server:app --host 0.0.0.0 --port $PORT
```

Crear el archivo:

```bash
echo "web: cd consultia/backend && uvicorn server:app --host 0.0.0.0 --port $PORT" > Procfile
```

#### B. Crear `runtime.txt` (especificar versión de Python)

```bash
python-3.11.10
```

Crear el archivo:

```bash
echo "python-3.11.10" > runtime.txt
```

#### C. Actualizar `requirements.txt` del backend

Ya debe estar actualizado con:
```
Pillow==11.0.0
pdf2image==1.17.0
python-multipart==0.0.20
```

### 3. Crear Aplicación en Heroku

```bash
# Login a Heroku
heroku login

# Crear app (sustituye 'consultia' por un nombre único)
heroku create consultia-app

# O si ya tienes la app creada en la web:
heroku git:remote -a nombre-de-tu-app
```

### 4. Configurar Buildpacks (Para instalar poppler)

Heroku usa "buildpacks" para instalar dependencias del sistema. Necesitas dos:

```bash
# 1. Buildpack para poppler (PDFs)
heroku buildpacks:add --index 1 https://github.com/heroku/heroku-buildpack-apt

# 2. Buildpack para Python
heroku buildpacks:add --index 2 heroku/python
```

#### Crear archivo `Aptfile` (para instalar poppler)

```bash
poppler-utils
```

Crear el archivo:

```bash
echo "poppler-utils" > Aptfile
```

### 5. Configurar Variables de Entorno

```bash
# API Key de OpenAI (REQUERIDO)
heroku config:set OPENAI_API_KEY=sk-tu-clave-aqui

# Orígenes permitidos para CORS
heroku config:set ALLOWED_ORIGINS=https://consultia-app.herokuapp.com

# Modelo de OpenAI (opcional)
heroku config:set OPENAI_MODEL_TEXT=gpt-4o-mini
heroku config:set OPENAI_MODEL_JSON=gpt-4o-mini
```

### 6. Compilar el Frontend

**Antes de hacer deploy**, compila el frontend:

```bash
cd consultia/frontend
npm install
npm run build
cd ../..
```

### 7. Preparar Git

```bash
# Asegúrate de que .gitignore NO excluya dist/consultia
# Verificar que dist/consultia esté en el repositorio

git add .
git commit -m "Preparar para Heroku: buildpacks, Procfile, Aptfile"
```

### 8. Desplegar a Heroku

```bash
git push heroku main

# O si tu rama es master:
git push heroku master
```

### 9. Abrir la Aplicación

```bash
heroku open
```

---

## 🔍 Verificar Instalación

### Ver Logs en Tiempo Real

```bash
heroku logs --tail
```

### Verificar que poppler está instalado

```bash
heroku run bash
# Dentro del contenedor:
which pdfinfo
# Debe mostrar: /app/.apt/usr/bin/pdfinfo
```

---

## 📁 Estructura de Archivos Requeridos

Asegúrate de tener estos archivos en la **raíz del proyecto**:

```
NewMed/
├── Procfile                          # ← NUEVO
├── runtime.txt                       # ← NUEVO
├── Aptfile                           # ← NUEVO (para poppler)
├── consultia/
│   ├── backend/
│   │   ├── server.py
│   │   ├── requirements.txt          # ← Actualizado con Pillow, pdf2image
│   │   └── ...
│   └── frontend/
│       └── dist/
│           └── consultia/            # ← Frontend compilado
│               ├── index.html
│               └── ...
└── ...
```

---

## ⚙️ Configuración Avanzada

### Aumentar Límite de Upload (si es necesario)

Por defecto Heroku permite hasta 30 segundos de request. Para archivos grandes:

```bash
heroku config:set WEB_CONCURRENCY=4
```

### Usar Base de Datos (opcional, para futuro)

```bash
heroku addons:create heroku-postgresql:essential-0
```

---

## 🐛 Troubleshooting

### Error: "Application error"

**Ver logs:**
```bash
heroku logs --tail
```

**Causas comunes:**
- `OPENAI_API_KEY` no configurada
- Buildpacks en orden incorrecto
- Frontend no compilado

### Error: "pdf2image not installed"

**Solución:** Verificar que Aptfile existe y buildpack apt está configurado

```bash
# Ver buildpacks
heroku buildpacks

# Debe mostrar:
# 1. https://github.com/heroku/heroku-buildpack-apt
# 2. heroku/python
```

### Error: "ModuleNotFoundError"

**Solución:** Verificar requirements.txt

```bash
heroku run pip list
```

---

## 🔄 Actualizar la Aplicación

Cada vez que hagas cambios:

```bash
# 1. Recompilar frontend (si cambió)
cd consultia/frontend
npm run build
cd ../..

# 2. Commit y push
git add .
git commit -m "Actualización"
git push heroku main

# 3. Ver logs
heroku logs --tail
```

---

## 💰 Costos en Heroku

### Dyno Gratis (Hobby)
- **Costo:** $0/mes
- **Limitaciones:**
  - Se duerme después de 30 min sin uso
  - 550-1000 horas/mes gratis
  - Perfecto para testing

### Dyno Basic
- **Costo:** $7/mes
- **Ventajas:**
  - Nunca se duerme
  - SSL incluido
  - Recomendado para producción

### Dyno Standard
- **Costo:** $25-50/mes
- **Ventajas:**
  - Mejor performance
  - Más RAM
  - Escalado horizontal

---

## 📊 Monitoreo

### Ver Métricas

```bash
heroku ps
heroku logs --tail
```

### Dashboard Web

1. Ve a [dashboard.heroku.com](https://dashboard.heroku.com)
2. Selecciona tu app
3. Ver: Logs, Métricas, Settings, Resources

---

## ✅ Checklist Final

Antes de ir a producción en Heroku:

- [ ] `Procfile` creado
- [ ] `runtime.txt` creado
- [ ] `Aptfile` creado (para poppler)
- [ ] Buildpacks configurados (apt + python)
- [ ] `OPENAI_API_KEY` configurada
- [ ] `ALLOWED_ORIGINS` configurada con tu dominio Heroku
- [ ] Frontend compilado y en `consultia/frontend/dist/consultia`
- [ ] `requirements.txt` incluye Pillow y pdf2image
- [ ] Git commit con todos los archivos
- [ ] Deploy exitoso: `git push heroku main`
- [ ] App abre correctamente: `heroku open`
- [ ] Logs sin errores: `heroku logs --tail`

---

## 🎯 Comandos Rápidos

```bash
# Crear app
heroku create consultia-app

# Buildpacks
heroku buildpacks:add --index 1 https://github.com/heroku/heroku-buildpack-apt
heroku buildpacks:add --index 2 heroku/python

# Config
heroku config:set OPENAI_API_KEY=sk-...
heroku config:set ALLOWED_ORIGINS=https://consultia-app.herokuapp.com

# Deploy
git push heroku main

# Ver logs
heroku logs --tail

# Abrir app
heroku open

# Ver buildpacks
heroku buildpacks

# Ver variables
heroku config

# Restart
heroku restart
```

---

## 🆘 Soporte

Si algo no funciona:

1. **Ver logs:** `heroku logs --tail`
2. **Verificar buildpacks:** `heroku buildpacks`
3. **Verificar variables:** `heroku config`
4. **Probar localmente primero**
5. **Revisar que frontend esté compilado**

---

## 🚀 Próximo Paso

Después de desplegar:

1. Prueba subir una imagen de historia clínica
2. Verifica que los datos se extraigan correctamente
3. Prueba exportar PDF con datos reales
4. Configura un dominio personalizado (opcional):
   ```bash
   heroku domains:add www.tu-dominio.com
   ```

---

**¡Listo para Heroku!** 🟣
