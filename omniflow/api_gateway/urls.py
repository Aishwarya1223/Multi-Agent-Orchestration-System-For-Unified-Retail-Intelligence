from django.urls import path, include
from .views import QueryAPIView, omni_ui
from .whisper_views import whisper_transcribe, whisper_status, whisper_fallback
from .tts_views import tts_speak
from django.http import JsonResponse

def api_root(request):
    """API root endpoint with available endpoints"""
    if request.method == 'GET':
        return JsonResponse({
            "message": "OmniFlow API",
            "version": "1.0.0",
            "endpoints": {
                "query": "/api/query/",
                "ui": "/api/ui/",
                "websocket": "ws://127.0.0.1:8000/ws/query/",
                "tts": "/api/tts/",
                "whisper": {
                    "transcribe": "/api/whisper/transcribe/",
                    "status": "/api/whisper/status/",
                    "fallback": "/api/whisper/fallback/"
                }
            },
            "methods": {
                "query": "POST",
                "ui": "GET",
                "tts": "POST",
                "whisper_transcribe": "POST",
                "whisper_status": "GET",
                "whisper_fallback": "POST"
            }
        })
    return JsonResponse({"error": "Method not allowed"}, status=405)

urlpatterns = [
    path("", api_root, name="api-root"),
    path("query/", QueryAPIView.as_view(), name="query"),
    path("ui/", omni_ui, name="omni-ui"),
    path("tts/", tts_speak, name="tts-speak"),
    path("whisper/transcribe/", whisper_transcribe, name="whisper-transcribe"),
    path("whisper/status/", whisper_status, name="whisper-status"),
    path("whisper/fallback/", whisper_fallback, name="whisper-fallback"),
]
