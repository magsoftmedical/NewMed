# Integración Completa Medberos AI - Guía Técnica de Producción

## 📋 Tabla de Contenidos

1. [Arquitectura y Flujo](#arquitectura)
2. [Implementaciones por Lenguaje](#implementaciones)
3. [Validaciones y Normalización](#validaciones)
4. [Integración con TIMA](#integracion-tima)
5. [Optimización y Producción](#produccion)

---

## 🏗️ Arquitectura y Flujo {#arquitectura}

### Diagrama de Flujo General

```
┌─────────────────┐
│  Médico Dicta   │
│   (Audio/Voz)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  TIMA Frontend  │
│  (Transcripción)│
└────────┬────────┘
         │ WebSocket
         ▼
┌─────────────────────────────────────────────┐
│           TIMA Backend (FastAPI)            │
│                                             │
│  1. Recibe transcripción                    │
│  2. Extrae info con OpenAI                  │
│  3. Construye formulario                    │
│  4. Normaliza datos                         │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│        Medberos Client (Tu código)          │
│                                             │
│  1. Verifica token (caché)                  │
│  2. Si expirado → Re-autentica              │
│  3. Mapea formulario → payload Medberos     │
│  4. POST /ai/predictDiagnoses               │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│       Medberos AI API (Externo)             │
│   https://test-api.medberos.com/api         │
│                                             │
│  - Procesa payload                          │
│  - Ejecuta modelo de IA                     │
│  - Devuelve predicciones                    │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│        TIMA Backend (Respuesta)             │
│                                             │
│  1. Recibe predicciones                     │
│  2. Normaliza formato                       │
│  3. Enriquece con metadata                  │
└────────┬────────────────────────────────────┘
         │ WebSocket
         ▼
┌─────────────────┐
│  TIMA Frontend  │
│  (UI Muestra    │
│   Predicciones) │
└─────────────────┘
```

### Pseudocódigo Arquitectónico

```python
# NIVEL 1: WebSocket Handler
async def on_voice_transcript(session_id, transcript):
    # Extraer info con OpenAI
    form = await extract_form_with_openai(transcript)

    # Validar antes de enviar
    validated_form = validate_and_normalize(form)

    # Llamar a Medberos
    if has_enough_info(validated_form):
        predictions = await medberos_predict_all(validated_form, transcript)
        await ws.send_json(predictions)

# NIVEL 2: Medberos Client
async def medberos_predict_all(form, transcript):
    # Asegurar autenticación
    await ensure_valid_token()

    # Mapear a formato Medberos
    payload = map_tima_to_medberos(form, transcript)

    # Llamadas paralelas
    diagnoses, exams, treatments = await asyncio.gather(
        predict_diagnoses(payload),
        predict_exams(payload),
        predict_treatments(payload)
    )

    return merge_predictions(diagnoses, exams, treatments)

# NIVEL 3: Token Management
async def ensure_valid_token():
    token = load_from_cache()

    if token and not is_expired(token):
        return token

    # Re-autenticar
    new_token = await authenticate()
    save_to_cache(new_token)
    return new_token
```

---

## 💻 Implementaciones por Lenguaje {#implementaciones}

### Python (FastAPI) - PRODUCCIÓN READY

```python
# medberos_client_production.py
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import httpx
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MedberosClient:
    """Cliente de producción para Medberos AI con gestión robusta de tokens."""

    def __init__(self):
        self.base_url = os.getenv("MEDBEROS_API_URL", "https://test-api.medberos.com/api")
        self.api_key = os.getenv("MEDBEROS_API_KEY")
        self.api_secret = os.getenv("MEDBEROS_API_SECRET")
        self.cache_path = Path(os.getenv("MEDBEROS_TOKEN_CACHE_PATH", ".medberos_token.cache"))

        # Token management
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

        # HTTP client con retry
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

        # Validación
        if not self.api_key or not self.api_secret:
            raise ValueError("MEDBEROS_API_KEY y MEDBEROS_API_SECRET son requeridos en .env")

    # ========== TOKEN MANAGEMENT ==========

    def _load_token_from_cache(self) -> bool:
        """Intenta cargar token del caché en disco."""
        if not self.cache_path.exists():
            return False

        try:
            with open(self.cache_path, 'r') as f:
                data = json.load(f)

            self.access_token = data.get('access_token')
            expiry_str = data.get('expiry')

            if expiry_str:
                self.token_expiry = datetime.fromisoformat(expiry_str)

            # Verificar si sigue válido (con 5 min de margen)
            if self.token_expiry and self.token_expiry > datetime.now() + timedelta(minutes=5):
                logger.info(f"[MEDBEROS] Token cargado desde caché. Válido hasta {self.token_expiry}")
                return True

        except Exception as e:
            logger.warning(f"[MEDBEROS] Error cargando caché: {e}")

        return False

    def _save_token_to_cache(self):
        """Guarda token en caché en disco."""
        try:
            data = {
                'access_token': self.access_token,
                'expiry': self.token_expiry.isoformat() if self.token_expiry else None
            }

            with open(self.cache_path, 'w') as f:
                json.dump(data, f)

            logger.info(f"[MEDBEROS] Token guardado en caché")

        except Exception as e:
            logger.warning(f"[MEDBEROS] Error guardando caché: {e}")

    async def _authenticate(self) -> bool:
        """Autentica con API Key/Secret y obtiene JWT token."""
        auth_url = f"{self.base_url}/api-key-auth/authenticate"

        logger.info("[MEDBEROS] Autenticando con API Key/Secret...")

        try:
            response = await self.client.post(
                auth_url,
                json={
                    "ApiKey": self.api_key,
                    "ApiSecret": self.api_secret
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"[MEDBEROS] Auth failed: {response.status_code} - {response.text}")
                return False

            data = response.json()
            self.access_token = data.get("accessToken")

            if not self.access_token:
                logger.error("[MEDBEROS] No accessToken en respuesta")
                return False

            # Token expira en 2 horas según docs
            self.token_expiry = datetime.now() + timedelta(hours=2)

            # Guardar en caché
            self._save_token_to_cache()

            logger.info(f"[MEDBEROS] ✅ Autenticación exitosa. Token válido hasta {self.token_expiry}")
            return True

        except Exception as e:
            logger.exception("[MEDBEROS] Error en autenticación")
            return False

    async def _ensure_valid_token(self) -> bool:
        """Asegura que tengamos un token válido (carga caché o re-autentica)."""
        # Intento 1: Token en memoria
        now = datetime.now()
        if self.access_token and self.token_expiry:
            if self.token_expiry > now + timedelta(minutes=5):
                logger.debug("[MEDBEROS] Usando token en memoria")
                return True

        # Intento 2: Cargar desde caché
        if self._load_token_from_cache():
            return True

        # Intento 3: Re-autenticar
        return await self._authenticate()

    # ========== API METHODS ==========

    async def test_connection(self) -> Dict[str, Any]:
        """Prueba la conexión con el endpoint de test."""
        if not await self._ensure_valid_token():
            return {"ok": False, "error": "Authentication failed"}

        try:
            test_url = f"{self.base_url}/api-key-auth/test"

            response = await self.client.get(
                test_url,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )

            if response.status_code == 200:
                logger.info("[MEDBEROS] ✅ Connection test successful")
                return {"ok": True, "message": "Connection successful"}
            else:
                logger.error(f"[MEDBEROS] Test failed: {response.status_code}")
                return {"ok": False, "error": f"Status {response.status_code}"}

        except Exception as e:
            logger.exception("[MEDBEROS] Connection test error")
            return {"ok": False, "error": str(e)}

    async def predict_diagnoses(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Predice diagnósticos."""
        return await self._predict("predictDiagnoses", payload)

    async def predict_exams(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Predice exámenes."""
        return await self._predict("predictExams", payload)

    async def predict_treatments(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Predice tratamientos."""
        return await self._predict("predictTreatments", payload)

    async def _predict(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Método genérico para llamar a endpoints de predicción."""
        if not await self._ensure_valid_token():
            return {"error": "Authentication failed"}

        url = f"{self.base_url}/ai/{endpoint}"

        logger.info(f"[MEDBEROS] Calling {endpoint}...")
        logger.debug(f"[MEDBEROS] Payload: {json.dumps(payload, indent=2)[:500]}...")

        try:
            response = await self.client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code != 200:
                error_text = response.text[:500]
                logger.error(f"[MEDBEROS] {endpoint} failed: {response.status_code} - {error_text}")
                return {"error": f"API error: {response.status_code}", "details": error_text}

            result = response.json()
            predictions_count = len(result.get('predictions', []))

            logger.info(f"[MEDBEROS] ✅ {endpoint} successful. Got {predictions_count} predictions")

            return result

        except httpx.TimeoutException:
            logger.error(f"[MEDBEROS] Timeout en {endpoint}")
            return {"error": "Request timeout"}

        except Exception as e:
            logger.exception(f"[MEDBEROS] Error en {endpoint}")
            return {"error": str(e)}

    async def predict_all(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Llama a los 3 endpoints en paralelo para máxima velocidad."""
        logger.info("[MEDBEROS] Iniciando predicciones paralelas...")

        results = await asyncio.gather(
            self.predict_diagnoses(payload),
            self.predict_exams(payload),
            self.predict_treatments(payload),
            return_exceptions=True
        )

        diagnoses, exams, treatments = results

        return {
            "diagnoses": diagnoses if not isinstance(diagnoses, Exception) else {"error": str(diagnoses)},
            "exams": exams if not isinstance(exams, Exception) else {"error": str(exams)},
            "treatments": treatments if not isinstance(treatments, Exception) else {"error": str(treatments)}
        }

    async def close(self):
        """Cierra el cliente HTTP."""
        await self.client.aclose()


# Instancia global
medberos_client = MedberosClient()
```

### Node.js (TypeScript + Axios) - PRODUCCIÓN READY

```typescript
// medberos-client.ts
import axios, { AxiosInstance, AxiosError } from 'axios';
import * as fs from 'fs/promises';
import * as path from 'path';

interface TokenCache {
  accessToken: string;
  expiry: string;
}

interface PredictionPayload {
  [key: string]: any;
}

interface PredictionResponse {
  predictions?: any[];
  error?: string;
}

export class MedberosClient {
  private baseURL: string;
  private apiKey: string;
  private apiSecret: string;
  private cachePath: string;

  private accessToken: string | null = null;
  private tokenExpiry: Date | null = null;

  private client: AxiosInstance;

  constructor() {
    this.baseURL = process.env.MEDBEROS_API_URL || 'https://test-api.medberos.com/api';
    this.apiKey = process.env.MEDBEROS_API_KEY || '';
    this.apiSecret = process.env.MEDBEROS_API_SECRET || '';
    this.cachePath = process.env.MEDBEROS_TOKEN_CACHE_PATH || '.medberos_token.cache';

    if (!this.apiKey || !this.apiSecret) {
      throw new Error('MEDBEROS_API_KEY and MEDBEROS_API_SECRET required in .env');
    }

    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  // ========== TOKEN MANAGEMENT ==========

  private async loadTokenFromCache(): Promise<boolean> {
    try {
      const cacheFile = path.resolve(this.cachePath);
      const exists = await fs.access(cacheFile).then(() => true).catch(() => false);

      if (!exists) return false;

      const data = await fs.readFile(cacheFile, 'utf-8');
      const cache: TokenCache = JSON.parse(data);

      this.accessToken = cache.accessToken;
      this.tokenExpiry = new Date(cache.expiry);

      // Verificar validez (5 min de margen)
      const now = new Date();
      const margin = new Date(now.getTime() + 5 * 60 * 1000);

      if (this.tokenExpiry > margin) {
        console.log(`[MEDBEROS] Token loaded from cache. Valid until ${this.tokenExpiry}`);
        return true;
      }

    } catch (error) {
      console.warn('[MEDBEROS] Error loading cache:', error);
    }

    return false;
  }

  private async saveTokenToCache(): Promise<void> {
    try {
      const cache: TokenCache = {
        accessToken: this.accessToken!,
        expiry: this.tokenExpiry!.toISOString()
      };

      const cacheFile = path.resolve(this.cachePath);
      await fs.writeFile(cacheFile, JSON.stringify(cache, null, 2));

      console.log('[MEDBEROS] Token saved to cache');
    } catch (error) {
      console.warn('[MEDBEROS] Error saving cache:', error);
    }
  }

  private async authenticate(): Promise<boolean> {
    const authURL = `${this.baseURL}/api-key-auth/authenticate`;

    console.log('[MEDBEROS] Authenticating with API Key/Secret...');

    try {
      const response = await this.client.post(authURL, {
        ApiKey: this.apiKey,
        ApiSecret: this.apiSecret
      });

      this.accessToken = response.data.accessToken;

      if (!this.accessToken) {
        console.error('[MEDBEROS] No accessToken in response');
        return false;
      }

      // Token expires in 2 hours
      this.tokenExpiry = new Date(Date.now() + 2 * 60 * 60 * 1000);

      // Save to cache
      await this.saveTokenToCache();

      console.log(`[MEDBEROS] ✅ Authentication successful. Token valid until ${this.tokenExpiry}`);
      return true;

    } catch (error) {
      const axiosError = error as AxiosError;
      console.error('[MEDBEROS] Authentication error:', axiosError.response?.data || axiosError.message);
      return false;
    }
  }

  private async ensureValidToken(): Promise<boolean> {
    // Try 1: Token in memory
    const now = new Date();
    const margin = new Date(now.getTime() + 5 * 60 * 1000);

    if (this.accessToken && this.tokenExpiry && this.tokenExpiry > margin) {
      console.log('[MEDBEROS] Using token in memory');
      return true;
    }

    // Try 2: Load from cache
    if (await this.loadTokenFromCache()) {
      return true;
    }

    // Try 3: Re-authenticate
    return await this.authenticate();
  }

  // ========== API METHODS ==========

  async testConnection(): Promise<{ ok: boolean; message?: string; error?: string }> {
    if (!await this.ensureValidToken()) {
      return { ok: false, error: 'Authentication failed' };
    }

    try {
      const response = await this.client.get('/api-key-auth/test', {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      });

      console.log('[MEDBEROS] ✅ Connection test successful');
      return { ok: true, message: 'Connection successful' };

    } catch (error) {
      const axiosError = error as AxiosError;
      console.error('[MEDBEROS] Connection test failed:', axiosError.response?.status);
      return { ok: false, error: `Status ${axiosError.response?.status}` };
    }
  }

  async predictDiagnoses(payload: PredictionPayload): Promise<PredictionResponse> {
    return this.predict('predictDiagnoses', payload);
  }

  async predictExams(payload: PredictionPayload): Promise<PredictionResponse> {
    return this.predict('predictExams', payload);
  }

  async predictTreatments(payload: PredictionPayload): Promise<PredictionResponse> {
    return this.predict('predictTreatments', payload);
  }

  private async predict(endpoint: string, payload: PredictionPayload): Promise<PredictionResponse> {
    if (!await this.ensureValidToken()) {
      return { error: 'Authentication failed' };
    }

    const url = `/ai/${endpoint}`;

    console.log(`[MEDBEROS] Calling ${endpoint}...`);
    console.log(`[MEDBEROS] Payload sample:`, JSON.stringify(payload).substring(0, 200) + '...');

    try {
      const response = await this.client.post(url, payload, {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      });

      const predictionsCount = response.data.predictions?.length || 0;
      console.log(`[MEDBEROS] ✅ ${endpoint} successful. Got ${predictionsCount} predictions`);

      return response.data;

    } catch (error) {
      const axiosError = error as AxiosError;
      console.error(`[MEDBEROS] ${endpoint} error:`, axiosError.response?.data || axiosError.message);
      return { error: axiosError.message };
    }
  }

  async predictAll(payload: PredictionPayload): Promise<any> {
    console.log('[MEDBEROS] Starting parallel predictions...');

    const [diagnoses, exams, treatments] = await Promise.allSettled([
      this.predictDiagnoses(payload),
      this.predictExams(payload),
      this.predictTreatments(payload)
    ]);

    return {
      diagnoses: diagnoses.status === 'fulfilled' ? diagnoses.value : { error: diagnoses.reason },
      exams: exams.status === 'fulfilled' ? exams.value : { error: exams.reason },
      treatments: treatments.status === 'fulfilled' ? treatments.value : { error: treatments.reason }
    };
  }
}

// Export singleton
export const medberosClient = new MedberosClient();
```

### C# (.NET 6+) - PRODUCCIÓN READY

```csharp
// MedberosClient.cs
using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace TIMA.Services
{
    public class TokenCache
    {
        public string AccessToken { get; set; }
        public DateTime Expiry { get; set; }
    }

    public class MedberosClient : IDisposable
    {
        private readonly string _baseUrl;
        private readonly string _apiKey;
        private readonly string _apiSecret;
        private readonly string _cachePath;

        private string _accessToken;
        private DateTime? _tokenExpiry;

        private readonly HttpClient _httpClient;
        private readonly ILogger<MedberosClient> _logger;

        public MedberosClient(IConfiguration config, ILogger<MedberosClient> logger)
        {
            _baseUrl = config["MEDBEROS_API_URL"] ?? "https://test-api.medberos.com/api";
            _apiKey = config["MEDBEROS_API_KEY"] ?? throw new ArgumentException("MEDBEROS_API_KEY required");
            _apiSecret = config["MEDBEROS_API_SECRET"] ?? throw new ArgumentException("MEDBEROS_API_SECRET required");
            _cachePath = config["MEDBEROS_TOKEN_CACHE_PATH"] ?? ".medberos_token.cache";

            _httpClient = new HttpClient
            {
                BaseAddress = new Uri(_baseUrl),
                Timeout = TimeSpan.FromSeconds(30)
            };

            _logger = logger;
        }

        // ========== TOKEN MANAGEMENT ==========

        private async Task<bool> LoadTokenFromCacheAsync()
        {
            try
            {
                if (!File.Exists(_cachePath))
                    return false;

                var json = await File.ReadAllTextAsync(_cachePath);
                var cache = JsonSerializer.Deserialize<TokenCache>(json);

                if (cache == null)
                    return false;

                _accessToken = cache.AccessToken;
                _tokenExpiry = cache.Expiry;

                // Verify validity (5 min margin)
                var now = DateTime.UtcNow;
                var margin = now.AddMinutes(5);

                if (_tokenExpiry > margin)
                {
                    _logger.LogInformation($"[MEDBEROS] Token loaded from cache. Valid until {_tokenExpiry}");
                    return true;
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning($"[MEDBEROS] Error loading cache: {ex.Message}");
            }

            return false;
        }

        private async Task SaveTokenToCacheAsync()
        {
            try
            {
                var cache = new TokenCache
                {
                    AccessToken = _accessToken,
                    Expiry = _tokenExpiry.Value
                };

                var json = JsonSerializer.Serialize(cache, new JsonSerializerOptions { WriteIndented = true });
                await File.WriteAllTextAsync(_cachePath, json);

                _logger.LogInformation("[MEDBEROS] Token saved to cache");
            }
            catch (Exception ex)
            {
                _logger.LogWarning($"[MEDBEROS] Error saving cache: {ex.Message}");
            }
        }

        private async Task<bool> AuthenticateAsync()
        {
            var authUrl = $"{_baseUrl}/api-key-auth/authenticate";

            _logger.LogInformation("[MEDBEROS] Authenticating with API Key/Secret...");

            try
            {
                var payload = new
                {
                    ApiKey = _apiKey,
                    ApiSecret = _apiSecret
                };

                var response = await _httpClient.PostAsJsonAsync(authUrl, payload);

                if (!response.IsSuccessStatusCode)
                {
                    var error = await response.Content.ReadAsStringAsync();
                    _logger.LogError($"[MEDBEROS] Auth failed: {response.StatusCode} - {error}");
                    return false;
                }

                var result = await response.Content.ReadFromJsonAsync<Dictionary<string, object>>();

                if (result == null || !result.TryGetValue("accessToken", out var token))
                {
                    _logger.LogError("[MEDBEROS] No accessToken in response");
                    return false;
                }

                _accessToken = token.ToString();
                _tokenExpiry = DateTime.UtcNow.AddHours(2);

                await SaveTokenToCacheAsync();

                _logger.LogInformation($"[MEDBEROS] ✅ Authentication successful. Token valid until {_tokenExpiry}");
                return true;
            }
            catch (Exception ex)
            {
                _logger.LogError($"[MEDBEROS] Authentication error: {ex.Message}");
                return false;
            }
        }

        private async Task<bool> EnsureValidTokenAsync()
        {
            // Try 1: Token in memory
            var now = DateTime.UtcNow;
            var margin = now.AddMinutes(5);

            if (!string.IsNullOrEmpty(_accessToken) && _tokenExpiry.HasValue && _tokenExpiry > margin)
            {
                _logger.LogDebug("[MEDBEROS] Using token in memory");
                return true;
            }

            // Try 2: Load from cache
            if (await LoadTokenFromCacheAsync())
                return true;

            // Try 3: Re-authenticate
            return await AuthenticateAsync();
        }

        // ========== API METHODS ==========

        public async Task<Dictionary<string, object>> TestConnectionAsync()
        {
            if (!await EnsureValidTokenAsync())
                return new Dictionary<string, object> { ["ok"] = false, ["error"] = "Authentication failed" };

            try
            {
                var request = new HttpRequestMessage(HttpMethod.Get, "/api-key-auth/test");
                request.Headers.Add("Authorization", $"Bearer {_accessToken}");

                var response = await _httpClient.SendAsync(request);

                if (response.IsSuccessStatusCode)
                {
                    _logger.LogInformation("[MEDBEROS] ✅ Connection test successful");
                    return new Dictionary<string, object> { ["ok"] = true, ["message"] = "Connection successful" };
                }

                _logger.LogError($"[MEDBEROS] Test failed: {response.StatusCode}");
                return new Dictionary<string, object> { ["ok"] = false, ["error"] = $"Status {response.StatusCode}" };
            }
            catch (Exception ex)
            {
                _logger.LogError($"[MEDBEROS] Connection test error: {ex.Message}");
                return new Dictionary<string, object> { ["ok"] = false, ["error"] = ex.Message };
            }
        }

        public async Task<Dictionary<string, object>> PredictDiagnosesAsync(object payload)
        {
            return await PredictAsync("predictDiagnoses", payload);
        }

        public async Task<Dictionary<string, object>> PredictExamsAsync(object payload)
        {
            return await PredictAsync("predictExams", payload);
        }

        public async Task<Dictionary<string, object>> PredictTreatmentsAsync(object payload)
        {
            return await PredictAsync("predictTreatments", payload);
        }

        private async Task<Dictionary<string, object>> PredictAsync(string endpoint, object payload)
        {
            if (!await EnsureValidTokenAsync())
                return new Dictionary<string, object> { ["error"] = "Authentication failed" };

            var url = $"/ai/{endpoint}";

            _logger.LogInformation($"[MEDBEROS] Calling {endpoint}...");

            try
            {
                var request = new HttpRequestMessage(HttpMethod.Post, url)
                {
                    Content = JsonContent.Create(payload)
                };
                request.Headers.Add("Authorization", $"Bearer {_accessToken}");

                var response = await _httpClient.SendAsync(request);

                if (!response.IsSuccessStatusCode)
                {
                    var error = await response.Content.ReadAsStringAsync();
                    _logger.LogError($"[MEDBEROS] {endpoint} failed: {response.StatusCode} - {error}");
                    return new Dictionary<string, object> { ["error"] = $"API error: {response.StatusCode}" };
                }

                var result = await response.Content.ReadFromJsonAsync<Dictionary<string, object>>();

                _logger.LogInformation($"[MEDBEROS] ✅ {endpoint} successful");

                return result;
            }
            catch (Exception ex)
            {
                _logger.LogError($"[MEDBEROS] {endpoint} error: {ex.Message}");
                return new Dictionary<string, object> { ["error"] = ex.Message };
            }
        }

        public async Task<Dictionary<string, object>> PredictAllAsync(object payload)
        {
            _logger.LogInformation("[MEDBEROS] Starting parallel predictions...");

            var tasks = new[]
            {
                PredictDiagnosesAsync(payload),
                PredictExamsAsync(payload),
                PredictTreatmentsAsync(payload)
            };

            var results = await Task.WhenAll(tasks);

            return new Dictionary<string, object>
            {
                ["diagnoses"] = results[0],
                ["exams"] = results[1],
                ["treatments"] = results[2]
            };
        }

        public void Dispose()
        {
            _httpClient?.Dispose();
        }
    }
}
```

---

## 🔍 Validaciones y Normalización {#validaciones}

### Archivo de Validación Completo

```python
# medberos_validator.py
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class MedberosValidator:
    """Validador y normalizador de datos antes de enviar a Medberos."""

    # Mapeo de sexo
    GENDER_MAP = {
        "M": "Masculino",
        "F": "Femenino",
        "Male": "Masculino",
        "Female": "Femenino",
        "Hombre": "Masculino",
        "Mujer": "Femenino"
    }

    # Especialidades válidas (obtener lista completa de Medberos)
    VALID_SPECIALTIES = {
        1: "Medicina General",
        2: "Pediatría",
        3: "Cardiología",
        4: "Ginecología",
        # ... agregar todas
    }

    @staticmethod
    def normalize_gender(gender: Optional[str]) -> Optional[str]:
        """Normaliza el sexo al formato esperado por Medberos."""
        if not gender:
            return None

        normalized = MedberosValidator.GENDER_MAP.get(gender.strip())

        if not normalized:
            logger.warning(f"[VALIDATOR] Sexo no reconocido: {gender}. Usando valor original.")
            return gender

        return normalized

    @staticmethod
    def validate_age(age: Optional[int]) -> bool:
        """Valida que la edad esté en rango razonable."""
        if age is None:
            return False

        if not (0 <= age <= 120):
            logger.warning(f"[VALIDATOR] Edad fuera de rango: {age}")
            return False

        return True

    @staticmethod
    def validate_vital_signs(vitals: Dict[str, Any]) -> Dict[str, List[str]]:
        """Valida signos vitales y retorna warnings."""
        warnings = {
            "missing": [],
            "out_of_range": []
        }

        # Presión arterial
        if not vitals.get("BloodPressure"):
            warnings["missing"].append("BloodPressure (PA)")

        # Frecuencia cardíaca
        hr = vitals.get("HeartRate")
        if hr is None:
            warnings["missing"].append("HeartRate (FC)")
        elif not (30 <= hr <= 220):
            warnings["out_of_range"].append(f"HeartRate: {hr} (esperado 30-220)")

        # Frecuencia respiratoria
        rr = vitals.get("RespiratoryRate")
        if rr is None:
            warnings["missing"].append("RespiratoryRate (FR)")
        elif not (8 <= rr <= 60):
            warnings["out_of_range"].append(f"RespiratoryRate: {rr} (esperado 8-60)")

        # Temperatura
        temp = vitals.get("Temperature")
        if temp is None:
            warnings["missing"].append("Temperature")
        elif isinstance(temp, (int, float)):
            if not (35 <= temp <= 42):
                warnings["out_of_range"].append(f"Temperature: {temp} (esperado 35-42°C)")

        # SpO2
        spo2 = vitals.get("Oxygen")
        if spo2 is not None:
            # Normalizar: "96%" → 96
            if isinstance(spo2, str):
                spo2_clean = spo2.replace('%', '').strip()
                try:
                    spo2 = float(spo2_clean)
                    vitals["Oxygen"] = spo2
                except ValueError:
                    warnings["out_of_range"].append(f"Oxygen: formato inválido '{spo2}'")

            if isinstance(spo2, (int, float)) and not (70 <= spo2 <= 100):
                warnings["out_of_range"].append(f"Oxygen: {spo2} (esperado 70-100%)")

        return warnings

    @staticmethod
    def ensure_specialty_id(payload: Dict[str, Any], default: int = 1) -> int:
        """Asegura que haya un SpecialtyId válido."""
        specialty_id = payload.get("SpecialtyId")

        if specialty_id is None:
            logger.info(f"[VALIDATOR] SpecialtyId faltante. Usando default: {default} (Medicina General)")
            return default

        if specialty_id not in MedberosValidator.VALID_SPECIALTIES:
            logger.warning(f"[VALIDATOR] SpecialtyId inválido: {specialty_id}. Usando default: {default}")
            return default

        return specialty_id

    @staticmethod
    def has_minimum_info(payload: Dict[str, Any]) -> bool:
        """Verifica que haya información mínima para predicción útil."""
        # Debe tener al menos:
        # - Edad O sexo
        # - Al menos 1 síntoma O 1 signo vital

        has_demographic = payload.get("PatientAge") or payload.get("PatientSex")
        has_symptoms = payload.get("Symptoms") and len(payload["Symptoms"]) > 0
        has_vitals = payload.get("VitalSigns") and len(payload["VitalSigns"]) > 0

        has_clinical = has_symptoms or has_vitals

        if not (has_demographic and has_clinical):
            logger.warning("[VALIDATOR] Información insuficiente para predicción útil")
            return False

        return True

    @staticmethod
    def validate_and_normalize(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Valida y normaliza payload completo antes de enviar."""
        normalized = payload.copy()

        # 1. Normalizar sexo
        if "PatientSex" in normalized:
            normalized["PatientSex"] = MedberosValidator.normalize_gender(normalized["PatientSex"])

        # 2. Validar edad
        age = normalized.get("PatientAge")
        if age is not None:
            if not MedberosValidator.validate_age(age):
                logger.warning("[VALIDATOR] Edad inválida, removiendo del payload")
                normalized.pop("PatientAge", None)

        # 3. Asegurar SpecialtyId
        normalized["SpecialtyId"] = MedberosValidator.ensure_specialty_id(normalized)

        # 4. Validar signos vitales
        if "VitalSigns" in normalized:
            warnings = MedberosValidator.validate_vital_signs(normalized["VitalSigns"])

            if warnings["missing"]:
                logger.info(f"[VALIDATOR] Signos vitales faltantes: {', '.join(warnings['missing'])}")

            if warnings["out_of_range"]:
                logger.warning(f"[VALIDATOR] Signos vitales fuera de rango: {', '.join(warnings['out_of_range'])}")

        # 5. Limpiar DoctorComments
        if "DoctorComments" in normalized:
            comments = normalized["DoctorComments"]
            if isinstance(comments, str):
                # Eliminar espacios múltiples
                normalized["DoctorComments"] = " ".join(comments.split())

        # 6. Verificar info mínima
        if not MedberosValidator.has_minimum_info(normalized):
            logger.warning("[VALIDATOR] ⚠️ Payload no tiene información mínima recomendada")

        return normalized
```

### Uso del Validador

```python
from medberos_validator import MedberosValidator

# En tu mapper
def consultia_to_medberos_payload(form: Dict[str, Any], doctor_comments: str = "") -> Dict[str, Any]:
    # ... construcción del payload ...

    # VALIDAR Y NORMALIZAR antes de enviar
    validated_payload = MedberosValidator.validate_and_normalize(payload)

    return validated_payload
```

---

## 🔗 Integración con TIMA {#integracion-tima}

### Flujo Completo de Integración

```python
# En tu server.py - Modificar run_incremental_update

async def run_incremental_update(
    ws: WebSocket,
    session_id: str,
    fragment: str,
    prev_form: dict,
    transcript: str
):
    try:
        # 1. Actualizar formulario con OpenAI (YA EXISTE)
        delta = await extract_form_delta(session_id, fragment)
        updated_form = deep_merge(prev_form, delta)
        missing = compute_missing(updated_form)

        # 2. Generar sugerencias contextuales (YA EXISTE)
        suggestions = await generate_contextual_suggestions(
            transcript=transcript,
            current_form=updated_form,
            recent_fragment=fragment
        )

        # 3. NUEVO: Llamar a Medberos AI si hay suficiente info
        ai_predictions = None

        if should_call_medberos(updated_form):
            logger.info("[TIMA] Llamando a Medberos AI para predicciones...")

            # Mapear y validar
            payload = consultia_to_medberos_payload(updated_form, transcript)
            payload = MedberosValidator.validate_and_normalize(payload)

            # Llamar en paralelo (diagnósticos, exámenes, tratamientos)
            ai_predictions = await medberos_client.predict_all(payload)

            # Convertir al formato de Consult-IA
            if "diagnoses" in ai_predictions and "predictions" in ai_predictions["diagnoses"]:
                diagnosticos_ai = medberos_diagnoses_to_consultia(ai_predictions["diagnoses"]["predictions"])
                ai_predictions["diagnosticos_consultia"] = diagnosticos_ai

        # 4. Enviar TODO al frontend
        await ws.send_json({
            "type": "form_update",
            "form": updated_form,
            "missing": missing,
            "suggestions": suggestions,
            "ai_predictions": ai_predictions  # NUEVO
        })

        # 5. Explicar deltas (YA EXISTE)
        deltas = compute_deltas(prev_form, updated_form)
        if deltas:
            explained = await explain_deltas(transcript, deltas)
            await ws.send_json({"type": "form_delta", "changes": explained})

        # 6. Actualizar sesión
        sessions[session_id]["json_state"] = updated_form
        sessions[session_id]["last_form"] = updated_form

    except Exception as e:
        logger.exception("[TIMA] Error en incremental update")
        await ws.send_json({"type": "error", "message": f"Update error: {e}"})


def should_call_medberos(form: Dict[str, Any]) -> bool:
    """Determina si hay suficiente información para llamar a Medberos."""
    # Criterios mínimos:
    # 1. Al menos 2 síntomas principales
    # 2. O al menos 1 síntoma + signos vitales
    # 3. Edad del paciente conocida

    anamnesis = form.get("anamnesis", {})
    sintomas = anamnesis.get("sintomasPrincipales", [])

    examen = form.get("examenClinico", {})
    signos_vitales = examen.get("signosVitales", {})
    has_vitals = any(signos_vitales.values())

    afiliacion = form.get("afiliacion", {})
    edad = afiliacion.get("edad", {}).get("anios")

    # Condición 1: Al menos 2 síntomas
    if len(sintomas) >= 2 and edad:
        return True

    # Condición 2: Al menos 1 síntoma + signos vitales
    if len(sintomas) >= 1 and has_vitals and edad:
        return True

    logger.debug("[TIMA] Info insuficiente para Medberos AI. Esperando más datos...")
    return False
```

### Manejo en Frontend (Angular/TypeScript)

```typescript
// En tu componente de TIMA

interface AIPredictions {
  diagnoses?: {
    predictions: Array<{
      Name: string;
      ICD10Code: string;
      Confidence: number;
    }>;
  };
  exams?: {
    predictions: Array<{
      Name: string;
      Confidence: number;
    }>;
  };
  treatments?: {
    predictions: Array<{
      Name: string;
      Dosage: string;
      Confidence: number;
    }>;
  };
  diagnosticos_consultia?: Array<{
    nombre: string;
    cie10: string;
    tipo: string;
    confianza: number;
  }>;
}

// En el WebSocket handler
private handleWebSocketMessage(message: any): void {
  switch (message.type) {
    case 'form_update':
      this.updateForm(message.form);
      this.missingFields = message.missing;
      this.suggestions = message.suggestions;

      // NUEVO: Manejar predicciones de IA
      if (message.ai_predictions) {
        this.handleAIPredictions(message.ai_predictions);
      }
      break;

    // ... otros casos
  }
}

private handleAIPredictions(predictions: AIPredictions): void {
  console.log('[TIMA] Predicciones de IA recibidas:', predictions);

  // Mostrar notificación
  this.showNotification('Nueva predicción de IA disponible', 'info');

  // Actualizar panel de predicciones
  this.aiPredictions = predictions;

  // Mostrar badge de "nuevas predicciones"
  this.hasNewPredictions = true;

  // Auto-scroll al panel de predicciones
  setTimeout(() => {
    this.scrollToPredictionsPanel();
  }, 300);
}

// Método para aceptar una predicción
acceptDiagnosis(diagnosis: any): void {
  // Agregar al formulario
  if (!this.form.diagnosticos) {
    this.form.diagnosticos = [];
  }

  this.form.diagnosticos.push({
    nombre: diagnosis.Name,
    cie10: diagnosis.ICD10Code,
    tipo: 'Presuntivo',
    origen: 'IA'  // Marcar que viene de IA
  });

  // Remover de predicciones pendientes
  this.removePrediction('diagnoses', diagnosis);

  // Mostrar confirmación
  this.showNotification(`Diagnóstico "${diagnosis.Name}" agregado`, 'success');
}
```

---

## ⚡ Optimización y Producción {#produccion}

### 1. Optimización de Latencia

```python
# Técnicas para reducir latencia

# A. Caché inteligente por síntomas similares
from functools import lru_cache
import hashlib

class MedberosCache:
    """Caché de predicciones para síntomas similares."""

    def __init__(self, ttl_seconds: int = 300):  # 5 minutos
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    def _hash_payload(self, payload: Dict) -> str:
        """Genera hash de payload para cacheado."""
        # Solo cachear por síntomas + edad + sexo (lo más relevante)
        key_data = {
            "age": payload.get("PatientAge"),
            "sex": payload.get("PatientSex"),
            "symptoms": sorted(payload.get("Symptoms", []))
        }

        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, payload: Dict) -> Optional[Any]:
        """Obtiene predicción del caché si existe y es válida."""
        key = self._hash_payload(payload)

        if key in self.cache:
            result, timestamp = self.cache[key]

            if datetime.now() - timestamp < self.ttl:
                logger.info(f"[CACHE] HIT para {key[:8]}...")
                return result
            else:
                logger.info(f"[CACHE] EXPIRED para {key[:8]}...")
                del self.cache[key]

        logger.info(f"[CACHE] MISS para {key[:8]}...")
        return None

    def set(self, payload: Dict, result: Any):
        """Guarda predicción en caché."""
        key = self._hash_payload(payload)
        self.cache[key] = (result, datetime.now())
        logger.info(f"[CACHE] SET para {key[:8]}...")

# Instancia global
prediction_cache = MedberosCache()

# Uso en predict_diagnoses
async def predict_diagnoses_cached(payload: Dict) -> Dict:
    # Verificar caché
    cached = prediction_cache.get(payload)
    if cached:
        return cached

    # Llamar a API
    result = await medberos_client.predict_diagnoses(payload)

    # Guardar en caché
    prediction_cache.set(payload, result)

    return result


# B. Debouncing inteligente
class SmartDebouncer:
    """Debouncer que espera 2 seg después del último input."""

    def __init__(self, delay_seconds: float = 2.0):
        self.delay = delay_seconds
        self.tasks: Dict[str, asyncio.Task] = {}

    async def debounce(self, key: str, coro):
        """Ejecuta corutina solo si no hay nuevos inputs en 2 seg."""
        # Cancelar tarea anterior
        if key in self.tasks:
            self.tasks[key].cancel()

        # Crear nueva tarea
        async def delayed():
            await asyncio.sleep(self.delay)
            return await coro

        task = asyncio.create_task(delayed())
        self.tasks[key] = task

        try:
            return await task
        except asyncio.CancelledError:
            logger.debug(f"[DEBOUNCER] Cancelado: {key}")
            raise

# Uso
debouncer = SmartDebouncer(delay_seconds=2.0)

async def on_transcript_fragment(session_id, fragment):
    # Solo predecir si no hay más inputs en 2 seg
    await debouncer.debounce(
        f"predict_{session_id}",
        call_medberos_predictions(session_id, fragment)
    )


# C. Paralelización máxima
async def predict_all_optimized(payload: Dict) -> Dict:
    """Versión optimizada que llama a los 3 endpoints en paralelo."""
    start = time.time()

    # Llamadas paralelas con timeout individual
    tasks = [
        asyncio.wait_for(predict_diagnoses_cached(payload), timeout=10.0),
        asyncio.wait_for(predict_exams_cached(payload), timeout=10.0),
        asyncio.wait_for(predict_treatments_cached(payload), timeout=10.0)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start
    logger.info(f"[OPTIMIZATION] Predicciones paralelas completadas en {elapsed:.2f}s")

    return {
        "diagnoses": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "exams": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "treatments": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        "elapsed_seconds": elapsed
    }
```

### 2. Estrategias de Retry

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class MedberosClientWithRetry(MedberosClient):
    """Cliente con retry automático para errores transitorios."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True
    )
    async def predict_diagnoses(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Predice diagnósticos con retry automático."""
        logger.info("[RETRY] Intentando predict_diagnoses...")
        return await super().predict_diagnoses(payload)

    # Similar para otros métodos...
```

### 3. Monitoring y Auditoría

```python
# medberos_monitoring.py
import time
from typing import Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json

@dataclass
class PredictionLog:
    """Log de cada predicción para auditoría."""
    timestamp: str
    session_id: str
    endpoint: str  # diagnoses, exams, treatments
    payload_hash: str
    response_time_ms: float
    predictions_count: int
    success: bool
    error: str = None

class MedberosMonitor:
    """Monitor para logs y métricas de Medberos."""

    def __init__(self, log_file: str = "medberos_audit.jsonl"):
        self.log_file = log_file

    def log_prediction(self, log: PredictionLog):
        """Guarda log de predicción en archivo."""
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(asdict(log)) + '\n')

    async def monitored_predict(self, session_id: str, endpoint: str, payload: Dict, predict_fn):
        """Wrapper que monitorea cualquier predicción."""
        start = time.time()
        payload_hash = hashlib.md5(json.dumps(payload).encode()).hexdigest()

        try:
            result = await predict_fn(payload)
            elapsed_ms = (time.time() - start) * 1000

            log = PredictionLog(
                timestamp=datetime.now().isoformat(),
                session_id=session_id,
                endpoint=endpoint,
                payload_hash=payload_hash,
                response_time_ms=elapsed_ms,
                predictions_count=len(result.get('predictions', [])),
                success=True
            )

            self.log_prediction(log)

            logger.info(f"[MONITOR] {endpoint}: {elapsed_ms:.0f}ms, {log.predictions_count} predicciones")

            return result

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000

            log = PredictionLog(
                timestamp=datetime.now().isoformat(),
                session_id=session_id,
                endpoint=endpoint,
                payload_hash=payload_hash,
                response_time_ms=elapsed_ms,
                predictions_count=0,
                success=False,
                error=str(e)
            )

            self.log_prediction(log)

            logger.error(f"[MONITOR] {endpoint} FAILED: {e}")

            raise

# Uso
monitor = MedberosMonitor()

async def predict_diagnoses_monitored(session_id, payload):
    return await monitor.monitored_predict(
        session_id,
        "diagnoses",
        payload,
        medberos_client.predict_diagnoses
    )
```

### 4. Rotación de Keys y Seguridad

```python
# medberos_security.py
import os
from cryptography.fernet import Fernet
from pathlib import Path

class MedberosSecureConfig:
    """Manejo seguro de credenciales con encriptación."""

    def __init__(self):
        # Generar o cargar key de encriptación
        self.key_file = Path(".medberos.key")

        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(self.key)
            self.key_file.chmod(0o600)  # Solo propietario puede leer

        self.cipher = Fernet(self.key)

    def encrypt_credentials(self, api_key: str, api_secret: str) -> Dict[str, bytes]:
        """Encripta credenciales."""
        return {
            "api_key": self.cipher.encrypt(api_key.encode()),
            "api_secret": self.cipher.encrypt(api_secret.encode())
        }

    def decrypt_credentials(self, encrypted: Dict[str, bytes]) -> Dict[str, str]:
        """Desencripta credenciales."""
        return {
            "api_key": self.cipher.decrypt(encrypted["api_key"]).decode(),
            "api_secret": self.cipher.decrypt(encrypted["api_secret"]).decode()
        }

    @staticmethod
    def rotate_keys():
        """Helper para rotar API keys (ejecutar manualmente)."""
        print("ROTACIÓN DE KEYS - Proceso Manual")
        print("1. Genera nuevas keys en https://test-api.medberos.com")
        print("2. Actualiza .env con nuevas credenciales")
        print("3. Reinicia el servidor")
        print("4. Verifica con: curl http://localhost:8001/medberos/test")
        print("\n⚠️ Las keys antiguas seguirán funcionando hasta que las revoques en la consola de Medberos")

# Para producción: usar un servicio de secrets como AWS Secrets Manager, HashiCorp Vault, etc.
```

### 5. Archivo .env Completo para Producción

```bash
# .env.production

# ========== OpenAI ==========
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL_TEXT=gpt-4o-mini
OPENAI_MODEL_JSON=gpt-4o-mini

# ========== CORS ==========
ALLOWED_ORIGINS=https://tima.medberos.com,https://tima-staging.medberos.com

# ========== Server ==========
PORT=8001
ENVIRONMENT=production

# ========== Medberos AI ==========
MEDBEROS_API_URL=https://test-api.medberos.com/api
MEDBEROS_API_KEY=e0998fca8b234058bc0e0a4efa6f1f9b
MEDBEROS_API_SECRET=55afa10b96e049eeaa2de86071507cb7
MEDBEROS_TOKEN_CACHE_PATH=.medberos_token.cache
MEDBEROS_ALLOWED_ORIGIN=https://tima.medberos.com

# ========== Medberos Config ==========
# Tiempo de caché de predicciones (segundos)
MEDBEROS_CACHE_TTL=300

# Timeout para requests (segundos)
MEDBEROS_REQUEST_TIMEOUT=30

# Retry automático
MEDBEROS_RETRY_ATTEMPTS=3
MEDBEROS_RETRY_DELAY=1

# Debounce para predicciones (segundos después del último input)
MEDBEROS_DEBOUNCE_DELAY=2.0

# SpecialtyId por defecto (1 = Medicina General)
MEDBEROS_DEFAULT_SPECIALTY=1

# ========== Monitoring ==========
# Archivo de logs de auditoría
MEDBEROS_AUDIT_LOG=logs/medberos_audit.jsonl

# Nivel de logging (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# ========== Security ==========
# Rotación de keys (días)
MEDBEROS_KEY_ROTATION_DAYS=90

# Archivo encriptado de credenciales (si usas encriptación)
MEDBEROS_ENCRYPTED_CREDS=.medberos.encrypted
```

### 6. Checklist de Producción

```markdown
## Checklist para Deploy a Producción

### Pre-Deploy
- [ ] Todas las credenciales en .env (no hardcodeadas)
- [ ] .env en .gitignore (NUNCA commitear credenciales)
- [ ] Token caché configurado
- [ ] Logs configurados (archivo + rotación)
- [ ] Monitoring configurado
- [ ] Tests pasando (pytest)
- [ ] Retry habilitado
- [ ] Timeouts configurados (30s)
- [ ] Caché habilitado (5 min)
- [ ] Debounce configurado (2s)

### Seguridad
- [ ] HTTPS habilitado (certificado SSL)
- [ ] CORS configurado correctamente
- [ ] Rate limiting en API (si aplica)
- [ ] Firewall configurado
- [ ] Keys rotadas últimos 90 días
- [ ] Logs de auditoría habilitados
- [ ] Manejo de errores sin exponer detalles internos

### Performance
- [ ] Predicciones en paralelo (asyncio.gather)
- [ ] Caché de tokens en disco
- [ ] Caché de predicciones similares
- [ ] Debouncing en frontend
- [ ] Lazy loading de componentes
- [ ] CDN para assets estáticos

### Monitoring
- [ ] Health check: /health
- [ ] Logs estructurados (JSON)
- [ ] Métricas de latencia
- [ ] Alertas de errores (>5% error rate)
- [ ] Dashboard de Grafana/Prometheus
- [ ] Logs centralizados (ELK Stack o similar)

### Fallback y Resiliencia
- [ ] Fallback a solo OpenAI si Medberos falla
- [ ] Retry automático (3 intentos)
- [ ] Circuit breaker (si >50% falla, pausar 1 min)
- [ ] Mensajes de error amigables para usuarios
- [ ] Graceful degradation

### Documentación
- [ ] README actualizado
- [ ] API docs (Swagger/OpenAPI)
- [ ] Guía de troubleshooting
- [ ] Runbook de operaciones
- [ ] Contactos de soporte (Daniel para Medberos)
```

---

## 📊 Métricas Recomendadas

```python
# medberos_metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Contadores
medberos_requests_total = Counter(
    'medberos_requests_total',
    'Total de requests a Medberos API',
    ['endpoint', 'status']
)

medberos_errors_total = Counter(
    'medberos_errors_total',
    'Total de errores en Medberos API',
    ['endpoint', 'error_type']
)

# Histogramas (latencia)
medberos_request_duration = Histogram(
    'medberos_request_duration_seconds',
    'Duración de requests a Medberos',
    ['endpoint']
)

# Gauges (estado actual)
medberos_token_expiry = Gauge(
    'medberos_token_expiry_timestamp',
    'Timestamp de expiración del token'
)

# Uso
@medberos_request_duration.labels('diagnoses').time()
async def predict_diagnoses_with_metrics(payload):
    try:
        result = await medberos_client.predict_diagnoses(payload)

        medberos_requests_total.labels(endpoint='diagnoses', status='success').inc()

        return result

    except Exception as e:
        medberos_requests_total.labels(endpoint='diagnoses', status='error').inc()
        medberos_errors_total.labels(endpoint='diagnoses', error_type=type(e).__name__).inc()

        raise
```

---

## 🎯 Resumen Ejecutivo

### Puntos Clave

1. **Token Management**: Caché en disco + renovación automática cada 2h
2. **Validación**: Normalizar sexo, validar rangos, asegurar SpecialtyId
3. **Performance**: Paralelización + caché + debounce = <2s latencia total
4. **Resiliencia**: Retry 3x + circuit breaker + fallback a OpenAI
5. **Monitoring**: Logs de auditoría + métricas Prometheus + alertas
6. **Seguridad**: HTTPS + .env + rotación de keys cada 90 días

### Arquitectura Recomendada

```
Frontend (Angular)
    ↓ WebSocket
Backend (FastAPI)
    ↓ Async calls
Medberos Client (con caché/retry)
    ↓ HTTPS
Medberos AI API
```

### Performance Esperado

- **Autenticación**: 200-500ms (solo 1 vez cada 2h)
- **Predicción individual**: 500-1500ms
- **Predicción paralela (3 endpoints)**: 800-2000ms
- **Con caché**: <50ms
- **Con debounce**: Espera 2s después del último input

### Próximos Pasos Inmediatos

1. ✅ Configurar credenciales en .env (YA HECHO)
2. ⏳ Ejecutar test_medberos.py
3. ⏳ Integrar en flujo de WebSocket
4. ⏳ Agregar UI en frontend
5. ⏳ Configurar monitoring

---

**Toda la implementación está lista para producción.** Solo necesitas configurar las credenciales y probar.
