# Daily Tech Tidbits (100% free setup)
Runs daily 7:00 AM IST -> gathers last-24h AI news -> Gemini free tier writes a <=5 page brief
-> saved as a Google Doc in Drive folder "Daily Tech Tidbits".

## Setup (about 20 min, one time)
1. **Gemini key (free):** https://aistudio.google.com/apikey -> Create API key (no card needed).
2. **Google Drive access:**
   - console.cloud.google.com -> new project -> enable "Google Drive API".
   - OAuth consent screen -> External -> add yourself as test user, then click **"Publish app"** (In production).
     (Needed, otherwise the token expires every 7 days. drive.file scope needs no Google verification.)
   - Credentials -> Create OAuth client ID -> **Desktop app** -> download JSON as `client_secret.json` into this folder.
   - `pip install -r requirements.txt && python get_token.py` -> sign in -> copy the 3 printed values.
3. **GitHub:** create a repo (public = unlimited free minutes), push these files.
   Settings -> Secrets and variables -> Actions -> add: GEMINI_API_KEY, GOOGLE_CLIENT_ID,
   GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN. Do NOT commit client_secret.json.
4. Actions tab -> "Daily Tech Tidbits" -> **Run workflow** to test. Check Drive.

## Notes
- GitHub cron can run a few minutes late; public repos pause schedules after 60 days of no repo activity (just click re-enable).
- The app only sees files it created (drive.file scope). If you already made a folder named "Daily Tech Tidbits" by hand, it will create a new one; move/rename accordingly.
- Free Gemini tier may use your prompts for training - fine here, since only public news is sent.
- Change PROFILE in agent.py to tailor the brief. Change GEMINI_MODEL env if Google retires a model.
