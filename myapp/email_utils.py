import requests
import json
from django.conf import settings

def send_email_api(subject, message, recipient_email):
    """
    Sends an email using the SendGrid API via HTTP POST.
    This bypasses SMTP port blocking on Render.
    """
    api_key = getattr(settings, 'SENDGRID_API_KEY', None)
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)

    if not api_key:
        print("SENDGRID ERROR: SENDGRID_API_KEY not found in settings.")
        return False, "API Key missing"

    url = "https://api.sendgrid.com/v3/mail/send"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "personalizations": [
            {
                "to": [{"email": recipient_email}],
                "subject": subject
            }
        ],
        "from": {"email": from_email},
        "content": [
            {
                "type": "text/plain",
                "value": message
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
        if response.status_code == 202:
            print(f"Email successfully queued via SendGrid API to {recipient_email}")
            return True, "Sent"
        else:
            error_data = response.json()
            print(f"SENDGRID API ERROR: {response.status_code} - {error_data}")
            return False, f"SendGrid Error: {response.status_code}"
    except Exception as e:
        print(f"SENDGRID REQUEST FAILED: {e}")
        return False, str(e)
