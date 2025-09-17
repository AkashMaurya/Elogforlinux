Setup Microsoft Office 365 SSO (django-allauth)

1. Ensure env vars are set (e.g., in .env):
   MICROSOFT_CLIENT_ID=your-client-id
   MICROSOFT_CLIENT_SECRET=your-client-secret

2. Activate virtualenv:
   source myenv/bin/activate

3. Install requirements (if needed):
   pip install -r requirements.txt

4. Run migrations:
   python manage.py migrate

5. Create/update SocialApp from env:
   python manage.py create_ms_socialapp

6. In Azure App Registration, configure Redirect URI (Web):
   https://<your-domain>/accounts/microsoft/login/callback/
   (If running locally with http, add http://localhost:8000/accounts/microsoft/login/callback/)

7. Start server:
   python manage.py runserver

Notes:
- The login button in `publicpage/templates/login.html` now points to the allauth microsoft provider login URL.
- Users can still login manually with email + password via the existing form.
