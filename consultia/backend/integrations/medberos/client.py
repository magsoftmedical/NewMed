"""
Cliente para integración con Medberos AI API.

Maneja:
- Autenticación con API Key/Secret
- Token JWT (renovación cada 2 horas)
- Predicciones de diagnósticos, exámenes y tratamientos
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("uvicorn.error")


class MedberosClient:
    """Cliente para interactuar con Medberos AI API."""

    def __init__(self):
        self.base_url = os.getenv("MEDBEROS_API_URL", "https://test-api.medberos.com/api")
        self.api_key = os.getenv("MEDBEROS_API_KEY", "")
        self.api_secret = os.getenv("MEDBEROS_API_SECRET", "")

        # Token management
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

        # HTTP client with timeout
        self.client = httpx.AsyncClient(timeout=30.0)

        if not self.api_key or not self.api_secret:
            logger.warning("[MEDBEROS] API Key/Secret not configured. AI predictions will be disabled.")

    async def _ensure_authenticated(self) -> bool:
        """Verifica que tengamos un token válido, o lo renueva."""

        if not self.api_key or not self.api_secret:
            logger.error("[MEDBEROS] Missing API credentials")
            return False

        # Si ya tenemos un token válido (con 5 min de margen)
        now = datetime.now()
        if self.access_token and self.token_expiry:
            if self.token_expiry > now + timedelta(minutes=5):
                logger.debug("[MEDBEROS] Using cached token")
                return True

        # Autenticar y obtener nuevo token
        logger.info("[MEDBEROS] Authenticating with API Key/Secret...")

        try:
            auth_url = f"{self.base_url}/api-key-auth/authenticate"

            response = await self.client.post(
                auth_url,
                json={
                    "ApiKey": self.api_key,
                    "ApiSecret": self.api_secret
                }
            )

            if response.status_code != 200:
                logger.error(f"[MEDBEROS] Authentication failed: {response.status_code} - {response.text}")
                return False

            data = response.json()

            # La API devuelve "token" no "accessToken"
            self.access_token = data.get("token") or data.get("accessToken")

            if not self.access_token:
                logger.error("[MEDBEROS] No token in response")
                logger.error(f"[MEDBEROS DEBUG] Keys en response: {list(data.keys())}")
                return False

            # Token expira en 2 horas según docs
            self.token_expiry = now + timedelta(hours=2)

            logger.info("[MEDBEROS] Authentication successful. Token valid until %s",
                       self.token_expiry.strftime("%Y-%m-%d %H:%M:%S"))

            return True

        except Exception as e:
            logger.exception("[MEDBEROS] Authentication error")
            return False

    async def test_connection(self) -> Dict[str, Any]:
        """Prueba la conexión con el endpoint de test."""

        if not await self._ensure_authenticated():
            return {"ok": False, "error": "Authentication failed"}

        try:
            test_url = f"{self.base_url}/api-key-auth/test"

            response = await self.client.get(
                test_url,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )

            if response.status_code == 200:
                logger.info("[MEDBEROS] Connection test successful")
                return {"ok": True, "message": "Connection successful"}
            else:
                logger.error(f"[MEDBEROS] Test failed: {response.status_code}")
                return {"ok": False, "error": f"Status {response.status_code}"}

        except Exception as e:
            logger.exception("[MEDBEROS] Connection test error")
            return {"ok": False, "error": str(e)}

    async def predict_diagnoses(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predice diagnósticos basados en los datos de la consulta.

        Args:
            payload: Objeto con estructura compatible con Medberos API
                     (ver ejemplos en medberos_examples.json)

        Returns:
            Dict con predicciones de diagnósticos
        """

        if not await self._ensure_authenticated():
            return {"error": "Authentication failed"}

        try:
            url = f"{self.base_url}/ai/predictDiagnoses"

            logger.info("[MEDBEROS] Calling predictDiagnoses...")

            response = await self.client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code != 200:
                logger.error(f"[MEDBEROS] predictDiagnoses failed: {response.status_code} - {response.text}")
                return {"error": f"API error: {response.status_code}"}

            result = response.json()

            # La API puede devolver lista directamente o {predictions: [...]}
            if isinstance(result, list):
                predictions = result
                logger.info(f"[MEDBEROS] predictDiagnoses successful. Got {len(predictions)} predictions")
                return {"predictions": predictions}
            else:
                predictions = result.get('predictions', [])
                logger.info(f"[MEDBEROS] predictDiagnoses successful. Got {len(predictions)} predictions")
                return result

        except Exception as e:
            logger.exception("[MEDBEROS] predictDiagnoses error")
            return {"error": str(e)}

    async def predict_exams(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predice exámenes médicos basados en los datos de la consulta.

        Args:
            payload: Objeto con estructura compatible con Medberos API

        Returns:
            Dict con predicciones de exámenes
        """

        if not await self._ensure_authenticated():
            return {"error": "Authentication failed"}

        try:
            url = f"{self.base_url}/ai/predictExams"

            logger.info("[MEDBEROS] Calling predictExams...")

            response = await self.client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code != 200:
                logger.error(f"[MEDBEROS] predictExams failed: {response.status_code} - {response.text}")
                return {"error": f"API error: {response.status_code}"}

            result = response.json()

            # La API puede devolver lista directamente o {predictions: [...]}
            if isinstance(result, list):
                predictions = result
                logger.info(f"[MEDBEROS] predictExams successful. Got {len(predictions)} predictions")
                return {"predictions": predictions}
            else:
                predictions = result.get('predictions', [])
                logger.info(f"[MEDBEROS] predictExams successful. Got {len(predictions)} predictions")
                return result

        except Exception as e:
            logger.exception("[MEDBEROS] predictExams error")
            return {"error": str(e)}

    async def predict_treatments(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predice tratamientos basados en los datos de la consulta.

        Args:
            payload: Objeto con estructura compatible con Medberos API

        Returns:
            Dict con predicciones de tratamientos
        """

        if not await self._ensure_authenticated():
            return {"error": "Authentication failed"}

        try:
            url = f"{self.base_url}/ai/predictTreatments"

            logger.info("[MEDBEROS] Calling predictTreatments...")

            response = await self.client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code != 200:
                logger.error(f"[MEDBEROS] predictTreatments failed: {response.status_code} - {response.text}")
                return {"error": f"API error: {response.status_code}"}

            result = response.json()

            # La API puede devolver lista directamente o {predictions: [...]}
            if isinstance(result, list):
                predictions = result
                logger.info(f"[MEDBEROS] predictTreatments successful. Got {len(predictions)} predictions")
                return {"predictions": predictions}
            else:
                predictions = result.get('predictions', [])
                logger.info(f"[MEDBEROS] predictTreatments successful. Got {len(predictions)} predictions")
                return result

        except Exception as e:
            logger.exception("[MEDBEROS] predictTreatments error")
            return {"error": str(e)}

    async def close(self):
        """Cierra el cliente HTTP."""
        await self.client.aclose()


# Instancia global del cliente
medberos_client = MedberosClient()
