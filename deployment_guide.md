# 🚀 Easy Interview: Deployment Guide (Render)

Follow these steps to deploy your application to Render so that it becomes accessible from your phone and anywhere in the world.

## Step 1: Create a GitHub Repository
1. Go to [GitHub](https://github.com/) and create a new private repository.
2. In your local terminal (in the project folder), run:
   ```bash
   git init
   git add .
   git commit -m "Prepare for deployment"
   git remote add origin YOUR_GITHUB_REPO_URL
   git branch -M main
   git push -u origin main
   ```

## Step 2: Set up a Database on Render (Optional but Recommended)
Render's free tier for SQLite will reset your database (users, questions, etc.) every time the server restarts. To keep your data:
1. On Render, click **New** -> **PostgreSQL**.
2. Copy the **Internal Database URL**.
3. *Note: If you stick with SQLite, your data will not persist on Render's free tier.*

## Step 3: Deploy to Render
1. Go to [Render](https://render.com/) and sign in.
2. Click **New** -> **Web Service**.
3. Connect your GitHub repository.
4. **Settings**:
   - **Name**: `easy-interview`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command**: `gunicorn myproject.wsgi`
5. **Environment Variables**:
   Click **Advanced** -> **Add Environment Variable** and add:
   - `SECRET_KEY`: (Copy from your `.env.example`)
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `easy-interview.onrender.com` (Replace with your actual Render URL)
   - `EMAIL_HOST_USER`: (Your email)
   - `EMAIL_HOST_PASSWORD`: (Your App Password)
   - `GEMINI_API_KEY`: (Your Gemini Key)
   - `CSRF_TRUSTED_ORIGINS`: `https://easy-interview.onrender.com`

## Step 4: Access on your Phone
Once the deployment is finished, Render will provide a URL like `https://easy-interview.onrender.com`. Open this on your phone, and the "Live Room" invitations will now work perfectly as they will point to this real web address!
