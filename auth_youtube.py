"""Run ONCE on your own computer to connect the pipeline to your YouTube channel.

  pip install google-auth-oauthlib
  python auth_youtube.py client_secret.json

A browser opens; sign in with the Google account that owns the LogikMedia channel
(pick the channel if asked). The script prints 3 values to save as GitHub secrets.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

path = sys.argv[1] if len(sys.argv) > 1 else "client_secret.json"
flow = InstalledAppFlow.from_client_secrets_file(path, SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
info = json.load(open(path))["installed"]
print("\nSave these 3 values as GitHub secrets:\n")
print("YT_CLIENT_ID     =", info["client_id"])
print("YT_CLIENT_SECRET =", info["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
