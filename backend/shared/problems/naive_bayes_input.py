# A simple Naive Bayes implementation for text classification
# This code is for educational purposes and is not optimized for performance or accuracy

training_data = [
    {
        "label": "spam",
        "features": {
            "free": 2,
            "win": 1,
            "offer": 1,
            "money": 1
        }
    },
    {
        "label": "spam",
        "features": {
            "free": 1,
            "offer": 2,
            "click": 1,
            "urgent": 1
        }
    },
    {
        "label": "spam",
        "features": {
            "win": 2,
            "money": 1,
            "prize": 1,
            "free": 1
        }
    },
    {
        "label": "ham",
        "features": {
            "meeting": 1,
            "schedule": 1,
            "project": 2,
            "team": 1
        }
    },
    {
        "label": "ham",
        "features": {
            "lunch": 1,
            "team": 1,
            "tomorrow": 1,
            "schedule": 1
        }
    },
    {
        "label": "ham",
        "features": {
            "project": 1,
            "update": 1,
            "meeting": 1,
            "report": 1
        }
    },
    {
        "label": "spam",
        "features": {
            "free": 1,
            "bonus": 1,
            "money": 2,
            "offer": 1
        }
    },
    {
        "label": "ham",
        "features": {
            "report": 1,
            "deadline": 1,
            "project": 1,
            "team": 1
        }
    }
]