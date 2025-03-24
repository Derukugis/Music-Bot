from librespot.core import Session


session = Session.Builder() \
    .user_pass("Username", "Password") \
    .create()

access_token = session.tokens().get("playlist-read")