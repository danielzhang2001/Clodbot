flow = Flow.from_client_config(
        client_config["web"], scopes=SCOPES, redirect_uri=FLASK_REDIRECT_URI
    )