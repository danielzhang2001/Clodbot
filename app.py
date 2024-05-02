import os
from flask import Flask

app = Flask(__name__)


@app.route("/auth/callback")
def auth_callback():
    # Handle authentication callback logic here
    return "Authentication callback received!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
