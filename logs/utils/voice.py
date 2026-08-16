"""
Voice reply utility using gTTS (Google Text-to-Speech).
Converts daily summary text into an MP3 file saved in media directory for browser playback.
"""

import os
from gtts import gTTS
from django.conf import settings
from logs.utils.translator import is_tamil

def generate_voice_summary(text, user_id):
    """
    Converts text to an MP3 audio file using gTTS.
    Saves file to media/audio/summary_<user_id>.mp3
    Returns the media URL path for HTML5 <audio> tag.
    """
    if not text:
        text = "No summary available."

    # Determine TTS language
    lang = 'ta' if is_tamil(text) else 'en'
    
    # Ensure media/audio directory exists
    audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    
    filename = f"summary_{user_id}.mp3"
    filepath = os.path.join(audio_dir, filename)
    
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(filepath)
        # Add timestamp cache buster query parameter for browser fresh load
        media_url = f"{settings.MEDIA_URL}audio/{filename}"
        return media_url
    except Exception as e:
        print(f"Error generating voice summary: {e}")
        return None
