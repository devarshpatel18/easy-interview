import requests
import json
import os
from django.conf import settings

def send_email_api(subject, message, recipient_email):
    """
    Sends an email using the Brevo (Sendinblue) API via HTTP POST.
    This bypasses Render's SMTP block.
    """
    # Use Brevo API Key instead
    api_key = getattr(settings, 'BREVO_API_KEY', os.getenv('BREVO_API_KEY', ''))
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'devarshrupareliya07@gmail.com')

    if not api_key:
        print("BREVO ERROR: BREVO_API_KEY not found.")
        return False, "API Key missing"

    url = "https://api.brevo.com/v3/smtp/email"
    
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    
    data = {
        "sender": {"email": from_email, "name": "Easy Interview"},
        "to": [{"email": recipient_email}],
        "subject": subject,
        "textContent": message
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code in [201, 200, 202]:
            print(f"Email successfully sent via Brevo API to {recipient_email}")
            return True, "Sent"
        else:
            error_data = response.json()
            print(f"BREVO API ERROR: {response.status_code} - {error_data}")
            return False, f"Brevo Error: {response.status_code}"
    except Exception as e:
        print(f"BREVO REQUEST FAILED: {e}")
        return False, str(e)
