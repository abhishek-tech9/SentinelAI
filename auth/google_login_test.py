import json
from google_auth_oauthlib.flow import InstalledAppFlow

with open("auth/oauth_config.json", "r") as f:
    config = json.load(f)

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    },
    scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"]
)

credentials = flow.run_local_server(port=0)

print("\nGoogle Login SUCCESS!")
print("Token received:", bool(credentials.token))