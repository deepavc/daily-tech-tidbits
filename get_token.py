"""Run ONCE on your laptop to get a Google refresh token. Needs client_secret.json (OAuth Desktop app)."""
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json", ["https://www.googleapis.com/auth/drive.file"])
c = flow.run_local_server(port=0, access_type="offline", prompt="consent")
print("\nGOOGLE_CLIENT_ID     =", c.client_id)
print("GOOGLE_CLIENT_SECRET =", c.client_secret)
print("GOOGLE_REFRESH_TOKEN =", c.refresh_token)
