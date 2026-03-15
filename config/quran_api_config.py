class QuranApiConfig:
    def __init__(
            self, client_id: str, client_secret: str, base_url: str, oauth_url: str
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self.oauth_url = oauth_url.rstrip("/")
