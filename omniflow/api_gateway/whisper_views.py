from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status
import json
import logging
import tempfile
import os
from io import BytesIO

from omniflow.utils.config import settings as pydantic_settings

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def whisper_transcribe(request):
    """
    Handle audio transcription using OpenAI Whisper API
    """
    try:
        if 'audio' not in request.FILES:
            return JsonResponse({
                'error': 'No audio file provided',
                'transcript': None
            }, status=status.HTTP_400_BAD_REQUEST)

        audio_file = request.FILES['audio']
        
        # Validate file size (max 25MB)
        if audio_file.size > 25 * 1024 * 1024:
            return JsonResponse({
                'error': 'Audio file too large (max 25MB)',
                'transcript': None
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate file type
        allowed_types = ['audio/webm', 'audio/wav', 'audio/mp3', 'audio/m4a', 'audio/ogg']
        if audio_file.content_type not in allowed_types:
            return JsonResponse({
                'error': f'Unsupported audio type: {audio_file.content_type}',
                'transcript': None
            }, status=status.HTTP_400_BAD_REQUEST)

        # Read audio file
        audio_data = audio_file.read()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name

        try:
            api_key = (
                (pydantic_settings.OPENAI_API_KEY or "").strip()
                or (getattr(settings, 'OPENAI_API_KEY', '') or '').strip()
                or (os.getenv('OPENAI_API_KEY', '') or '').strip()
            )

            if not api_key:
                logger.error("OpenAI API key not configured")
                return JsonResponse({
                    'error': 'Speech recognition service not available',
                    'transcript': None
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            with open(temp_file_path, 'rb') as audio_file_obj:
                transcript_text = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file_obj,
                    language="en"
                )

            # Clean up temporary file
            os.unlink(temp_file_path)

            text_out = transcript_text.text if hasattr(transcript_text, "text") else str(transcript_text)
            logger.info(f"Whisper transcription successful: {text_out[:100]}...")

            return JsonResponse({
                'success': True,
                'transcript': text_out,
                'duration': 0
            })

        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
            logger.error(f"Whisper transcription error: {str(e)}")
            return JsonResponse({
                'error': f'Transcription failed: {str(e)}',
                'transcript': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"Whisper API error: {str(e)}")
        return JsonResponse({
            'error': f'Server error: {str(e)}',
            'transcript': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@require_http_methods(["GET"])
def whisper_status(request):
    """
    Check Whisper API status
    """
    try:
        api_key = (
            (pydantic_settings.OPENAI_API_KEY or "").strip()
            or (getattr(settings, 'OPENAI_API_KEY', '') or '').strip()
            or (os.getenv('OPENAI_API_KEY', '') or '').strip()
        )

        if not api_key:
            return JsonResponse({
                'available': False,
                'error': 'OpenAI API key not configured'
            })

        # Test API connectivity
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            models = client.models.list()
            return JsonResponse({
                'available': True,
                'whisper_available': any('whisper' in model.id for model in models.data),
                'models': [model.id for model in models.data if 'whisper' in model.id]
            })
        except Exception as e:
            return JsonResponse({
                'available': False,
                'error': f'API connectivity error: {str(e)}'
            })

    except Exception as e:
        logger.error(f"Whisper status check error: {str(e)}")
        return JsonResponse({
            'available': False,
            'error': f'Server error: {str(e)}'
        })

@csrf_exempt
@require_http_methods(["POST"])
def whisper_fallback(request):
    """
    Fallback speech recognition using browser's Web Speech API
    """
    try:
        data = json.loads(request.body)
        transcript = data.get('transcript', '')
        
        if not transcript:
            return JsonResponse({
                'error': 'No transcript provided',
                'transcript': None
            }, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Fallback transcript received: {transcript[:100]}...")

        return JsonResponse({
            'success': True,
            'transcript': transcript,
            'source': 'browser_fallback'
        })

    except Exception as e:
        logger.error(f"Fallback transcript error: {str(e)}")
        return JsonResponse({
            'error': f'Server error: {str(e)}',
            'transcript': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
