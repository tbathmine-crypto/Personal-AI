import re
import os
import tempfile
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q, Sum

from logs.models import Entry, Reminder
from logs.utils.categorizer import categorize_entry
from logs.utils.translator import translate_if_needed
from logs.utils.voice import generate_voice_summary
from logs.utils.scheduler import sync_reminders

import speech_recognition as sr

# Authentication Views
def signup_view(request):
    """
    Handles new user registration.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    return render(request, 'signup.html', {'form': form})


def login_view(request):
    """
    Handles user authentication and login.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """
    Handles user logout.
    """
    logout(request)
    return redirect('login')


# Dashboard & Features Views
def generate_daily_summary_text(user):
    """
    Generates a human-friendly single-sentence summary of today's user entries.
    Example: 'Today you logged 3 entries: ate eggs, played basketball, spent 70 rupees.'
    """
    today = date.today()
    today_entries = Entry.objects.filter(user=user, timestamp__date=today).order_by('timestamp')
    
    count = today_entries.count()
    if count == 0:
        return "You haven't logged any entries today yet."

    snippets = []
    for entry in today_entries:
        # Use translated text if available, else original
        txt = entry.translated_text if entry.translated_text else entry.text
        snippets.append(txt.strip())

    if len(snippets) == 1:
        details = snippets[0]
    elif len(snippets) == 2:
        details = f"{snippets[0]} and {snippets[1]}"
    else:
        details = ", ".join(snippets[:-1]) + f", and {snippets[-1]}"

    return f"Today you logged {count} {'entries' if count > 1 else 'entry'}: {details}."



@login_required
def dashboard_view(request):
    """
    Main user dashboard view. Displays recent entries, daily summary, search query interface, and reminders.
    """
    user_entries = Entry.objects.filter(user=request.user)
    today = date.today()
    today_entries = user_entries.filter(timestamp__date=today)
    daily_summary = generate_daily_summary_text(request.user)
    
    # Active reminder for the user
    user_reminder = Reminder.objects.filter(user=request.user, is_active=True).first()

    context = {
        'entries': user_entries[:20], # Show top 20 recent
        'today_count': today_entries.count(),
        'daily_summary': daily_summary,
        'user_reminder': user_reminder,
    }
    return render(request, 'dashboard.html', context)


@login_required
def add_entry_view(request):
    """
    API endpoint to save a new life log entry.
    Auto-detects Tamil/English language, translates if needed, and applies smart categorization.
    """
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if not text:
            return JsonResponse({'status': 'error', 'message': 'Entry text cannot be empty.'}, status=400)

        # Bilingual detection and translation
        orig_lang, translated = translate_if_needed(text)
        
        # Smart categorization
        category = categorize_entry(text, translated_text=translated)
        
        # Save entry
        entry = Entry.objects.create(
            user=request.user,
            text=text,
            category=category,
            original_language=orig_lang,
            translated_text=translated
        )

        return JsonResponse({
            'status': 'success',
            'entry': {
                'id': entry.id,
                'text': entry.text,
                'category': entry.category,
                'original_language': entry.original_language,
                'translated_text': entry.translated_text,
                'timestamp': entry.timestamp.strftime('%b %d, %Y %I:%M %p')
            },
            'new_summary': generate_daily_summary_text(request.user)
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@login_required
def search_entries_view(request):
    """
    Smart search and natural language query feature using Django ORM.
    Supports queries like 'what did I eat today', 'total expense this week', 'spent', 'food'.
    Calculates total numerical values for expense queries.
    """
    query = request.GET.get('q', '').strip().lower()
    if not query:
        return JsonResponse({'entries': [], 'summary': 'Please type a query.'})

    entries = Entry.objects.filter(user=request.user)
    today = date.today()

    # Time filters check
    if 'today' in query:
        entries = entries.filter(timestamp__date=today)
    elif 'this week' in query or 'week' in query:
        start_of_week = today - timedelta(days=today.weekday())
        entries = entries.filter(timestamp__date__gte=start_of_week)

    # Category filters check
    if any(k in query for k in ['eat', 'food', 'ate', 'breakfast', 'lunch', 'dinner']):
        entries = entries.filter(category='Food')
    elif any(k in query for k in ['expense', 'spent', 'cost', 'bought', 'price', 'paid', 'rupees', 'rs']):
        entries = entries.filter(category='Expense')
    elif any(k in query for k in ['task', 'todo', 'meeting', 'work', 'call']):
        entries = entries.filter(category='Task')
    elif any(k in query for k in ['event', 'play', 'movie', 'party', 'went']):
        entries = entries.filter(category='Event')
    else:
        # Keyword text search fallback
        entries = entries.filter(Q(text__icontains=query) | Q(translated_text__icontains=query))

    # Calculate total if expense query
    is_expense_query = 'expense' in query or 'spent' in query or 'cost' in query or 'total' in query
    total_expense = 0
    if is_expense_query:
        for entry in entries:
            # Extract all numbers from original & translated text
            nums = re.findall(r'\b\d+(?:\.\d+)?\b', entry.text + " " + (entry.translated_text or ""))
            for n in nums:
                try:
                    total_expense += float(n)
                except ValueError:
                    pass

    # Build response list
    entry_data = [
        {
            'id': e.id,
            'text': e.text,
            'category': e.category,
            'timestamp': e.timestamp.strftime('%b %d, %Y %I:%M %p'),
            'translated_text': e.translated_text
        }
        for e in entries
    ]

    summary_msg = f"Found {len(entry_data)} matching entry{'ies' if len(entry_data) != 1 else ''}."
    if is_expense_query and total_expense > 0:
        summary_msg += f" Total calculated amount: {total_expense:.2f} rupees."

    return JsonResponse({
        'status': 'success',
        'query': query,
        'entries': entry_data,
        'summary': summary_msg,
        'total_expense': total_expense if is_expense_query else None
    })


@login_required
def generate_summary_voice_view(request):
    """
    Generates gTTS audio file for today's summary and returns media URL.
    """
    summary_text = generate_daily_summary_text(request.user)
    media_url = generate_voice_summary(summary_text, request.user.id)
    
    if media_url:
        return JsonResponse({
            'status': 'success',
            'audio_url': media_url,
            'summary_text': summary_text
        })
    else:
        return JsonResponse({'status': 'error', 'message': 'Failed to generate audio summary.'}, status=500)


@login_required
def speech_to_text_view(request):
    """
    Backend SpeechRecognition fallback view for uploaded voice audio recordings.
    Converts speech to text in Tamil or English.
    """
    if request.method == 'POST' and request.FILES.get('audio'):
        audio_file = request.FILES['audio']
        lang = request.POST.get('lang', 'en-US') # 'en-US' or 'ta-IN'
        
        # Save temporary audio file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(tmp_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language=lang)
                
            os.remove(tmp_path)
            return JsonResponse({'status': 'success', 'text': text})
        except sr.UnknownValueError:
            os.remove(tmp_path)
            return JsonResponse({'status': 'error', 'message': 'Could not understand audio.'}, status=400)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return JsonResponse({'status': 'error', 'message': f'Speech recognition error: {str(e)}'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'No audio file provided.'}, status=400)


@login_required
def set_reminder_view(request):
    """
    Saves or updates daily email reminder preference for the user.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        reminder_time = request.POST.get('reminder_time', '').strip() # Expecting HH:MM
        
        if not email or not reminder_time:
            return JsonResponse({'status': 'error', 'message': 'Email and time are required.'}, status=400)

        reminder, created = Reminder.objects.update_or_create(
            user=request.user,
            defaults={
                'email': email,
                'reminder_time': reminder_time,
                'is_active': True
            }
        )

        # Re-sync scheduler jobs
        sync_reminders()

        return JsonResponse({
            'status': 'success',
            'message': f"Reminder scheduled daily for {email} at {reminder_time}."
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
