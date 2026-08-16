"""
Bilingual support module for Tamil and English.
Detects Tamil script and translates text to English using deep_translator (GoogleTranslator).
"""

import re
from deep_translator import GoogleTranslator

def is_tamil(text):
    """
    Detects if the input text contains Tamil Unicode characters (\u0B80 - \u0BFF).
    """
    if not text:
        return False
    # Tamil Unicode block range: U+0B80 to U+0BFF
    tamil_pattern = re.compile(r'[\u0B80-\u0BFF]')
    return bool(tamil_pattern.search(text))

def translate_if_needed(text):
    """
    Detects if text is Tamil. If Tamil, translates to English and returns (original_language, translated_text).
    If English or translation fails, returns ('en', None) or ('ta', translated_text).
    """
    if not text:
        return 'en', None

    if is_tamil(text):
        try:
            translator = GoogleTranslator(source='ta', target='en')
            translated = translator.translate(text)
            return 'ta', translated
        except Exception as e:
            print(f"Translation warning: {e}")
            return 'ta', text # Fallback to original text if translation API is unavailable
    else:
        return 'en', None
