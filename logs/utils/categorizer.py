"""
Smart categorization engine using keyword dictionary matching.
Categorizes entries into Food, Expense, Task, Event, or General.
"""

import re

# Dictionary mapping categories to keyword sets (lowercased)
CATEGORY_KEYWORDS = {
    'Food': [
        'ate', 'eat', 'eaten', 'eating', 'food', 'breakfast', 'lunch', 'dinner', 
        'snack', 'snacks', 'coffee', 'tea', 'eggs', 'egg', 'rice', 'fruit', 
        'drink', 'drinking', 'unavu', 'sapadu', 'biryani', 'pizza', 'burger', 'sandwich'
    ],
    'Expense': [
        'spent', 'spend', 'cost', 'bought', 'buy', 'expense', 'paid', 'pay', 
        'price', 'rupees', 'rupee', 'rs', '$', 'dollar', 'cash', 'card', 
        'bill', 'selavu', 'purchase', 'purchased', 'ticket', 'fee', 'rent'
    ],
    'Task': [
        'todo', 'task', 'meeting', 'call', 'work', 'finish', 'complete', 
        'project', 'submit', 'assignment', 'fix', 'bug', 'velai', 'study', 
        'remind', 'reminder', 'prepare', 'send', 'write', 'email', 'code'
    ],
    'Event': [
        'played', 'play', 'party', 'went', 'go', 'event', 'movie', 'concert', 
        'match', 'travel', 'trip', 'visited', 'visit', 'fun', 'show', 
        'celebrated', 'celebration', 'game', 'gym', 'workout', 'walk', 'run'
    ]
}

def categorize_entry(text, translated_text=None):
    """
    Categorizes the entry text into Food, Expense, Task, Event, or General.
    Uses scoring based on keyword frequency and priority.
    """
    combined_text = (text + " " + (translated_text or "")).lower()
    
    # Category score dictionary
    scores = {
        'Expense': 0,
        'Food': 0,
        'Task': 0,
        'Event': 0
    }

    # Expense high-priority triggers (money, prices, cost)
    expense_triggers = ['spent', 'expense', 'cost', 'paid', 'rupees', 'rupee', 'rs', '$', 'dollar', 'bill', 'selavu']
    for trig in expense_triggers:
        if re.search(r'\b' + re.escape(trig) + r'\b', combined_text) or trig in combined_text:
            scores['Expense'] += 2 # Extra weight for explicit money/cost terms

    # Check all category keywords
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', combined_text):
                scores[category] += 1

    # Find highest scoring category
    max_category = max(scores, key=scores.get)
    if scores[max_category] > 0:
        return max_category
        
    return 'General'

