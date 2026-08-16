from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Entry(models.Model):
    """
    Model representing a user's life log entry.
    Contains text, auto-assigned category, user reference, and timestamps.
    """
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Expense', 'Expense'),
        ('Task', 'Task'),
        ('Event', 'Event'),
        ('General', 'General'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='entries')
    text = models.TextField(help_text="Original text entered by the user")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    timestamp = models.DateTimeField(default=timezone.now, help_text="Timestamp of when entry was created")
    original_language = models.CharField(max_length=10, default='en', help_text="Language code: en or ta")
    translated_text = models.TextField(blank=True, null=True, help_text="English translation if original text was Tamil")

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Entries'

    def __str__(self):
        return f"{self.user.username} - [{self.category}] {self.text[:30]}..."


class Reminder(models.Model):
    """
    Model representing a daily scheduled email reminder for a user.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    email = models.EmailField()
    reminder_time = models.TimeField(help_text="Time of day for the reminder (HH:MM)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reminder for {self.user.username} at {self.reminder_time}"

