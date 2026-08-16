import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'life_log_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from logs.models import Entry, Reminder
from logs.utils.categorizer import categorize_entry
from logs.utils.translator import translate_if_needed, is_tamil
from logs.utils.voice import generate_voice_summary
from logs.utils.scheduler import sync_reminders, send_reminder_email

def run_tests():
    print("==========================================")
    print("STARTING ALL FEATURE VERIFICATION TESTS...")
    print("==========================================")

    # 1. Test Categorizer & Dictionary Matching
    print("\n--- 1. Testing Smart Categorization ---")
    assert categorize_entry("morning ate eggs") == "Food", "Failed Food categorization"
    assert categorize_entry("spent 70 rupees for lunch") == "Expense", "Failed Expense categorization"
    assert categorize_entry("meeting with team at 3pm") == "Task", "Failed Task categorization"
    assert categorize_entry("played basketball with friends") == "Event", "Failed Event categorization"
    assert categorize_entry("just watching sunset") == "General", "Failed General categorization"
    print("[OK] All 5 smart category tests passed!")

    # 2. Test Bilingual Tamil Detection & Translation
    print("\n--- 2. Testing Bilingual Tamil Support ---")
    tamil_text = "காலை உணவு சாப்பிட்டேன்"
    assert is_tamil(tamil_text) == True, "Failed Tamil script detection"
    lang, translated = translate_if_needed(tamil_text)
    print(f"Original Tamil Text -> Detected Lang: '{lang}', Translated: '{translated}'")
    assert lang == 'ta', "Failed language code assignment"
    cat_tamil = categorize_entry(tamil_text, translated)
    print(f"Categorized Tamil entry as: '{cat_tamil}'")
    assert cat_tamil == 'Food', "Failed Tamil entry categorization as Food"
    print("[OK] Bilingual Tamil detection & translation tests passed!")

    # 3. Test User Authentication & Dashboard Endpoints
    print("\n--- 3. Testing User Authentication & Views ---")
    client = Client()
    
    # Create test user
    User.objects.filter(username='testuser').delete()
    user = User.objects.create_user(username='testuser', password='Password123!')
    print(f"Created test user: {user.username}")

    # Login
    login_success = client.login(username='testuser', password='Password123!')
    assert login_success == True, "Failed user login"
    print("[OK] User authentication (signup/login) passed!")

    # 4. Test Add Entry API
    print("\n--- 4. Testing Add Entry API ---")
    res1 = client.post('/api/add-entry/', {'text': 'morning ate eggs'})
    assert res1.status_code == 200, "Add entry 1 failed"
    
    res2 = client.post('/api/add-entry/', {'text': 'spent 70 rupees for lunch'})
    assert res2.status_code == 200, "Add entry 2 failed"
    
    res3 = client.post('/api/add-entry/', {'text': 'played basketball in evening'})
    assert res3.status_code == 200, "Add entry 3 failed"

    user_entries_count = Entry.objects.filter(user=user).count()
    assert user_entries_count == 3, f"Expected 3 entries, found {user_entries_count}"
    print(f"[OK] Added {user_entries_count} entries successfully via API!")

    # 5. Test Search & Natural Language Query (with total expense calculation)
    print("\n--- 5. Testing Search & Natural Language Query ---")
    search_food = client.get('/api/search/?q=what did I eat today')
    food_data = search_food.json()
    assert food_data['status'] == 'success'
    assert len(food_data['entries']) >= 1
    print(f"Query 'what did I eat today' returned {len(food_data['entries'])} result(s). Summary: {food_data['summary']}")

    search_expense = client.get('/api/search/?q=total expense this week')
    expense_data = search_expense.json()
    assert expense_data['status'] == 'success'
    print(f"Query 'total expense this week' summary: {expense_data['summary']}, Total calculated: {expense_data['total_expense']}")
    assert expense_data['total_expense'] == 70.0, f"Expected total expense 70.0, got {expense_data['total_expense']}"
    print("[OK] Search & expense calculation ORM queries passed!")

    # 6. Test Daily Summary & gTTS Audio Generation
    print("\n--- 6. Testing gTTS Voice Summary ---")
    voice_res = client.get('/api/voice-summary/')
    voice_data = voice_res.json()
    assert voice_data['status'] == 'success'
    assert 'audio_url' in voice_data
    print(f"Daily Summary Text: '{voice_data['summary_text']}'")
    print(f"Generated Audio URL: '{voice_data['audio_url']}'")
    print("[OK] gTTS audio summary generation passed!")

    # 7. Test Email Reminder API & Scheduler
    print("\n--- 7. Testing Email Reminder Scheduler ---")
    rem_res = client.post('/api/set-reminder/', {'email': 'testuser@example.com', 'reminder_time': '17:00'})
    assert rem_res.status_code == 200
    rem_obj = Reminder.objects.get(user=user)
    assert rem_obj.email == 'testuser@example.com'
    
    # Test sending email dispatch silently
    send_reminder_email(rem_obj.id)
    print("[OK] Email reminder setting & dispatch passed!")

    print("\n==========================================")
    print("ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==========================================")


if __name__ == '__main__':
    run_tests()
