from django.urls import path
from logs import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('api/add-entry/', views.add_entry_view, name='add_entry'),
    path('api/search/', views.search_entries_view, name='search_entries'),
    path('api/voice-summary/', views.generate_summary_voice_view, name='voice_summary'),
    path('api/speech-to-text/', views.speech_to_text_view, name='speech_to_text'),
    path('api/set-reminder/', views.set_reminder_view, name='set_reminder'),
]
