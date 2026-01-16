from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import os

from omniflow.utils.config import settings as pydantic_settings


@csrf_exempt
@require_http_methods(["POST"])
def tts_speak(request):
    try:
        payload = json.loads(request.body or "{}")
        text = (payload.get("text") or "").strip()
        if not text:
            return JsonResponse({"error": "text is required"}, status=400)

        api_key = (
            (pydantic_settings.OPENAI_API_KEY or "").strip()
            or (getattr(settings, "OPENAI_API_KEY", "") or "").strip()
            or (os.getenv("OPENAI_API_KEY", "") or "").strip()
        )
        if not api_key:
            return JsonResponse({"error": "OPENAI_API_KEY not configured"}, status=503)

        model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
        voice = os.getenv("OPENAI_TTS_VOICE", "alloy")
        fmt = os.getenv("OPENAI_TTS_FORMAT", "mp3")

        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        audio = client.audio.speech.create(
            model=model,
            voice=voice,
            response_format=fmt,
            input=text,
        )

        if hasattr(audio, "read"):
            audio_bytes = audio.read()
        elif hasattr(audio, "content"):
            audio_bytes = audio.content
        elif hasattr(audio, "iter_bytes"):
            audio_bytes = b"".join(audio.iter_bytes())
        else:
            audio_bytes = bytes(audio)

        if fmt == "mp3":
            content_type = "audio/mpeg"
        elif fmt == "wav":
            content_type = "audio/wav"
        else:
            content_type = "application/octet-stream"
        return HttpResponse(audio_bytes, content_type=content_type)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
