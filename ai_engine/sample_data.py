SAMPLE_TASKS = [
    {"id": 1, "title": "Prepare vegetables and meal prep for the week", "priority": "high", "assigned_to": "Mom", "status": "open"},
    {"id": 2, "title": "Buy school stationery and after-school snacks", "priority": "medium", "assigned_to": "Dad", "status": "open"},
    {"id": 3, "title": "Schedule pediatrician appointment", "priority": "high", "assigned_to": "Mom", "status": "open"},
]

SAMPLE_REMINDERS = [
    {"id": 1, "note": "Take prenatal vitamins after breakfast.", "due": "today", "priority": "high"},
    {"id": 2, "note": "Call the childcare provider about Friday pick-up.", "due": "tomorrow", "priority": "medium"},
]

SAMPLE_MEALS = [
    {"id": 1, "description": "Vegetable quinoa bowl with lentils", "tags": ["vegetarian", "high-protein", "quick"]},
    {"id": 2, "description": "Spinach dal with brown rice and a side salad", "tags": ["comfort", "family"]},
]

SAMPLE_SAFETY = [
    {"id": 1, "note": "Keep emergency contacts updated and visible.", "last_checked": "yesterday"},
    {"id": 2, "note": "Store first aid kit near the kitchen and bedroom.", "last_checked": "2 days ago"},
]

seed_documents = [
    {
        "text": "Mother prefers vegetarian meals with high protein and low preparation time. Family loves lentil and vegetable bowls for dinner.",
        "metadata": {"type": "meal_preference", "source": "seed"},
    },
    {
        "text": "The household includes two adults and one child. Responsibilities are shared between Mom and Dad, with Mom managing medical reminders and cooking.",
        "metadata": {"type": "profile", "source": "seed"},
    },
    {
        "text": "Important reminder: schedule doctor visits, buy healthy snacks, and prepare school supplies early.",
        "metadata": {"type": "reminder_history", "source": "seed"},
    },
    {
        "text": "Previous chat: balance cooking, cleaning, and school runs while keeping nutrition diverse and predictable.",
        "metadata": {"type": "chat_history", "source": "seed"},
    },
]
