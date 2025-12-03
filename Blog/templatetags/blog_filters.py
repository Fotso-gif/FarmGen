# blog/templatetags/blog_filters.py
from django import template

register = template.Library()

@register.filter(name='get_media_type')
def get_media_type(url):
    """Retourne le type de média basé sur l'extension"""
    if not url:
        return 'unknown'
    
    url_lower = str(url).lower()
    
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
    audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.wma']
    
    for ext in video_extensions:
        if url_lower.endswith(ext):
            return 'video'
    
    for ext in audio_extensions:
        if url_lower.endswith(ext):
            return 'audio'
    
    # Vérifier par contenu type si présent dans l'URL
    if 'video' in url_lower:
        return 'video'
    elif 'audio' in url_lower:
        return 'audio'
    
    return 'unknown'

@register.filter(name='is_video')
def is_video(url):
    """Vérifie si c'est une vidéo"""
    return get_media_type(url) == 'video'

@register.filter(name='is_audio')
def is_audio(url):
    """Vérifie si c'est un audio"""
    return get_media_type(url) == 'audio'