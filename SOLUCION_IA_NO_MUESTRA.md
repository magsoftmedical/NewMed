# 🔧 SOLUCIÓN: IA NO MUESTRA TEXTO EN EL FRONTEND

## 📊 DIAGNÓSTICO ACTUAL

**Síntoma:** El asistente IA no muestra ningún texto en el panel del frontend.

**Logs del backend muestran:**
```
INFO: [AI] stream_summary ENTER len=195, missing=[...]
INFO: [AI] assistant_reset SENT
```

**Pero NO muestran:** `[AI] stream_summary COMPLETE. Sent X tokens`

**Conclusión:** OpenAI NO está enviando tokens de vuelta, o hay un error en el streaming.

---

## 🔍 PASO 1: Verificar que OpenAI funciona

### Ejecutar test de conexión:

```bash
cd consultia\backend
.venv\Scripts\activate
python test_openai.py
```

**Resultado esperado:**
```
TEST 1: ✓ Respuesta recibida: hola
TEST 2: ✓ Streaming completado: 50 tokens
TEST 3: ✓ JSON recibido: {"motivoConsulta": "fiebre"}
```

### Posibles errores:

#### ❌ Error: "Invalid API key"
```
openai.AuthenticationError: Error code: 401
```

**Causa:** La API key es inválida o ha expirado.

**Solución:**
1. Ve a https://platform.openai.com/api-keys
2. Crea una nueva API key
3. Cópiala en `consultia/backend/.env`:
```env
OPENAI_API_KEY=sk-proj-TU_NUEVA_KEY_AQUI
```
4. Reinicia el servidor

---

#### ❌ Error: "Insufficient quota"
```
openai.RateLimitError: Error code: 429
You exceeded your current quota
```

**Causa:** La cuenta de OpenAI no tiene créditos.

**Solución:**
1. Ve a https://platform.openai.com/account/billing
2. Agrega un método de pago
3. Compra créditos (mínimo $5)
4. Espera 5-10 minutos
5. Reinicia el servidor

---

#### ❌ Error: "Rate limit exceeded"
```
openai.RateLimitError: Error code: 429
Rate limit reached
```

**Causa:** Has hecho demasiadas llamadas muy rápido.

**Solución:**
- Espera 1 minuto
- Vuelve a intentar

---

#### ❌ Error: "Connection timeout"
```
httpx.ConnectTimeout
```

**Causa:** Tu conexión a internet está bloqueando OpenAI.

**Solución:**
1. Verifica tu conexión a internet
2. Desactiva firewall/antivirus temporalmente
3. Prueba con otra red (usa tu celular como hotspot)

---

## 🔍 PASO 2: Verificar logs detallados del backend

### Aumentar nivel de logging:

Edita `consultia/backend/server.py`, busca la línea 28:

**Cambiar de:**
```python
logger = logging.getLogger("uvicorn.error")
```

**A:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### Reiniciar servidor:
```bash
# Ctrl+C para detener
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Hablar en el micrófono y buscar:

```
[AI] stream_summary ENTER len=..., missing=[...]
[AI] assistant_reset SENT
[AI] Sending token #1: Paciente...
[AI] Sending token #2:  refiere...
[AI] Sending token #3:  fiebre...
...
[AI] stream_summary COMPLETE. Sent 50 tokens
```

### Posibles resultados:

#### ✅ Si ves los tokens:
**Problema:** El backend funciona, el problema está en el frontend.
→ Ve al PASO 3

#### ❌ Si NO ves tokens:
**Problema:** OpenAI no está respondiendo.
→ Revisa el resultado del test_openai.py

#### ❌ Si ves error de OpenAI:
```
openai.AuthenticationError: ...
openai.RateLimitError: ...
```
**Problema:** API key o créditos.
→ Ve a las soluciones del PASO 1

---

## 🔍 PASO 3: Verificar WebSocket en el frontend

### Abrir consola del navegador (F12)

1. Abre http://localhost:4200
2. Presiona F12
3. Ve a la pestaña "Console"

### Buscar logs:

```javascript
[AI WS] conectado
[AI WS <<] {"type":"assistant_reset"}
[AI WS <<] {"type":"assistant_token","delta":"Paciente"}
[AI WS <<] {"type":"assistant_token","delta":" refiere"}
...
```

### Posibles resultados:

#### ✅ Si ves `assistant_token`:
**Problema:** Los mensajes llegan pero no se muestran en la UI.
→ Ve al PASO 4

#### ❌ Si solo ves `assistant_reset` pero NO tokens:
**Problema:** El backend no está enviando los tokens.
→ Vuelve al PASO 2

#### ❌ Si NO ves ningún mensaje:
**Problema:** El WebSocket no está conectado.
→ Ve al PASO 5

---

## 🔍 PASO 4: Verificar componente de UI

### Buscar el archivo del componente:

```bash
consultia/frontend/src/app/features/consultation-room/ai-stream-panel.component.ts
```

### Verificar que el observable esté subscrito:

```typescript
ngOnInit() {
  this.aiText$ = this.aiStream.aiText$;
}
```

### En el template HTML:

```html
<div>{{ aiText$ | async }}</div>
```

### Posible solución rápida:

**Edita:** `ai-stream-panel.component.ts`

**Agrega logging:**
```typescript
ngOnInit() {
  this.aiText$ = this.aiStream.aiText$;

  // DEBUG: Ver cambios en tiempo real
  this.aiText$.subscribe(text => {
    console.log('[AI PANEL] Text updated:', text);
  });
}
```

### Recargar página y hablar:

Si ves en consola:
```
[AI PANEL] Text updated:
[AI PANEL] Text updated: Paciente
[AI PANEL] Text updated: Paciente refiere
```

**Entonces:** El servicio funciona, el problema es el binding en el template.

---

## 🔍 PASO 5: Verificar conexión WebSocket

### En la consola del navegador:

```javascript
// Ver el estado del WebSocket
window.__ai.ws.readyState
// 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED
```

**Si es 3 (CLOSED):**

### Verificar URL del WebSocket:

**Archivo:** `consultia/frontend/src/environments/environment.ts`

```typescript
export const environment = {
  production: false,
  apiBase: '/api',
  timaBase: '/tima',
  wsBase: 'ws://127.0.0.1:8001'  // ← Verificar que sea correcta
};
```

### Verificar CORS en el backend:

**Archivo:** `consultia/backend/server.py`

```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200").split(",")
```

**En `.env`:**
```env
ALLOWED_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
```

---

## 🚀 SOLUCIÓN RÁPIDA (Si nada funciona)

### Opción 1: Usar test directo

**Crear:** `consultia/frontend/test-ai.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>Test IA</title>
</head>
<body>
    <h1>Test Asistente IA</h1>
    <button onclick="testAI()">Probar IA</button>
    <div id="output" style="white-space: pre-wrap; border: 1px solid black; padding: 10px; margin-top: 10px;"></div>

    <script>
        function testAI() {
            const output = document.getElementById('output');
            output.textContent = 'Conectando...\n';

            const ws = new WebSocket('ws://127.0.0.1:8001/ws?session=test123');

            ws.onopen = () => {
                output.textContent += 'Conectado!\n';

                // Enviar texto de prueba
                ws.send(JSON.stringify({
                    type: 'final',
                    text: 'Paciente viene por fiebre'
                }));

                output.textContent += 'Mensaje enviado\n';
            };

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                output.textContent += `Recibido: ${msg.type}\n`;

                if (msg.type === 'assistant_token') {
                    output.textContent += msg.delta;
                }

                if (msg.type === 'form_update') {
                    output.textContent += `\nFormulario: ${JSON.stringify(msg.form, null, 2)}\n`;
                }
            };

            ws.onerror = (error) => {
                output.textContent += `Error: ${error}\n`;
            };
        }
    </script>
</body>
</html>
```

**Abrir:** `http://localhost:4200/test-ai.html` (o directamente el archivo)

**Hacer clic en "Probar IA"**

**Resultado esperado:**
```
Conectando...
Conectado!
Mensaje enviado
Recibido: assistant_reset
Recibido: assistant_token
Paciente refiere fiebre...
```

Si esto funciona → El problema está en el componente Angular.

---

## 📋 CHECKLIST COMPLETO

- [ ] Test de OpenAI pasa (test_openai.py)
- [ ] Logs del backend muestran tokens enviados
- [ ] Consola del navegador muestra mensajes WebSocket
- [ ] Consola muestra `assistant_token` con delta
- [ ] El servicio aiStream actualiza aiText$
- [ ] El componente está subscrito al observable
- [ ] El template usa `| async` correctamente

---

## 🆘 SI NADA FUNCIONA

Comparte estos datos:

1. **Salida completa de `test_openai.py`**
2. **Logs del backend cuando hablas** (últimas 50 líneas)
3. **Consola del navegador** (pestaña Console, todos los mensajes)
4. **Screenshot del panel de IA** (vacío)

Con esa información puedo identificar exactamente dónde está el problema.

---

## 💡 CAUSA MÁS PROBABLE

Basado en tus logs actuales:

```
[AI] stream_summary ENTER len=195, missing=[...]
[AI] assistant_reset SENT
```

**Falta:** `[AI] stream_summary COMPLETE. Sent X tokens`

**Diagnóstico:** OpenAI NO está enviando tokens.

**Razones posibles:**
1. ❌ API key inválida (401 error)
2. ❌ Sin créditos (429 error)
3. ❌ Timeout de conexión
4. ❌ El prompt está causando un error

**Siguiente paso:**
```bash
cd consultia\backend
.venv\Scripts\activate
python test_openai.py
```

Comparte el resultado y seguimos desde ahí.
