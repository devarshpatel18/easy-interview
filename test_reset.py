import os
import django
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.test import RequestFactory

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

User = get_user_model()
user = User.objects.filter(email='max3@gmail.com').first()

if user:
    print(f"Found user: {user.email}")
    form = PasswordResetForm(data={'email': user.email})
    if form.is_valid():
        print("Form is valid, sending email...")
        # Mock request for domain/protocol
        rf = RequestFactory()
        request = rf.get('/')
        form.save(
            request=request,
            use_https=False,
            from_email='support@easyinterview.com',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt'
        )
        print("Done.")
    else:
        print(f"Form errors: {form.errors}")
else:
    print("User not found.")
