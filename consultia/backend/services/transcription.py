import io

from fastapi import UploadFile

from config import client, logger

_HALLUCINATIONS = [
    "subtítulos realizados por la comunidad de amara.org",
    "gracias por ver el vídeo",
    "thanks for watching",
    "subtítulos por la comunidad de amara.org",
    "subtitulado por",
    "suscríbete al canal",
    "saludos",
    "un saludo",
    "¡Joder!",
    "jodete",
    "jódete",
    "suscríbete",
    "suscripción",
    "like y comparte",
    "gracias por escuchar",
    "gracias a todos",
    "gracias",
    "¡Muchas gracias!",
    "¡Muchas gracias por ver el vídeo!",
    "¡Gracias por ver el vídeo!",
    "Buenas tardes",
    "Buenos días",
    "Buenas noches",
]


async def transcribe_audio(file: UploadFile) -> str:
    """
    Transcribe audio using OpenAI Whisper.
    Returns the transcribed text (empty string if hallucination detected).
    Raises ValueError for empty files, Exception for API errors.
    """
    logger.info(f"[WHISPER] Received audio: {file.filename}, content_type: {file.content_type}")

    contents = await file.read()
    if not contents:
        raise ValueError("Archivo de audio vacío")

    fname = file.filename or "audio.webm"
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else "webm"
    allowed = {"flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"}
    if ext not in allowed:
        ext = "webm"

    audio_file = io.BytesIO(contents)
    audio_file.name = f"audio.{ext}"

    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="es",
    )

    text = response.text.strip()
    logger.info(f"[WHISPER] Transcribed: {text[:100]}...")

    text_lower = text.lower().strip("¡!¿?.,;: ")
    if any(h in text_lower for h in _HALLUCINATIONS):
        logger.warning(f"[WHISPER] Hallucination filtered: {text}")
        return ""

    return text
