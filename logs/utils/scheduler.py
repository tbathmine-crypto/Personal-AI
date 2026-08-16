"""
Background email reminder module using schedule library and threading.
Checks active user reminders and dispatches email daily summaries.
"""

import time
import threading
from datetime import date
import schedule
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

_scheduler_thread = None
_scheduler_started = False

def send_reminder_email(reminder_id):
    """
    Sends email reminder with user's current daily summary.
    Executed by schedule job runner.
    """
    from logs.models import Reminder, Entry
    try:
        reminder = Reminder.objects.get(id=reminder_id, is_active=True)
        user = reminder.user
        
        today = date.today()
        today_entries = Entry.objects.filter(user=user, timestamp__date=today)
        
        if today_entries.exists():
            entry_list_str = "\n".join([f"• [{e.category}] {e.text} ({e.timestamp.strftime('%I:%M %p')})" for e in today_entries])
            summary_text = f"Here are your logged entries for today ({today.strftime('%B %d, %Y')}):\n\n{entry_list_str}"
        else:
            summary_text = "You haven't logged any entries today yet. Don't forget to record your meals, expenses, and tasks!"

        subject = f"Personal AI Life Log Reminder - {today.strftime('%B %d, %Y')}"
        message = (
            f"Hello {user.username},\n\n"
            f"This is your scheduled daily reminder from Personal AI Life Log Assistant.\n\n"
            f"{summary_text}\n\n"
            f"Best regards,\nPersonal AI Life Log Team"
        )
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reminder.email],
            fail_silently=False
        )
        print(f"[Scheduler] Successfully sent email reminder to {reminder.email} for user {user.username}")
    except Exception as e:
        print(f"[Scheduler Error] Failed to send reminder #{reminder_id}: {e}")


def check_and_run_schedule():
    """
    Background loop that runs schedule.run_pending() continuously.
    """
    print("[Scheduler] Background scheduler loop started.")
    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            print(f"[Scheduler Error] Loop error: {e}")
        time.sleep(30)


def sync_reminders():
    """
    Clears existing schedule jobs and re-registers all active reminders from DB.
    """
    try:
        from logs.models import Reminder
        schedule.clear()
        
        active_reminders = Reminder.objects.filter(is_active=True)
        for rem in active_reminders:
            # Format time as HH:MM string
            time_str = rem.reminder_time.strftime("%H:%M")
            # Schedule daily job for this reminder
            schedule.every().day.at(time_str).do(send_reminder_email, reminder_id=rem.id)
            
        print(f"[Scheduler] Synced {active_reminders.count()} active reminders.")
    except Exception as e:
        print(f"[Scheduler Error] Sync failed: {e}")


def start_scheduler_thread():
    """
    Initializes the background scheduler thread once during application startup.
    """
    global _scheduler_thread, _scheduler_started
    if not _scheduler_started:
        _scheduler_started = True
        sync_reminders()
        _scheduler_thread = threading.Thread(target=check_and_run_schedule, daemon=True)
        _scheduler_thread.start()
