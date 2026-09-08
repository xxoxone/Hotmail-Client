from flask import Flask
from config import SECRET_KEY

def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    from app.routes.main import bp_main
    from app.routes.auth_tools import bp_auth
    from app.routes.fb_tools import bp_fb
    from app.routes.media_tools import bp_media
    from app.routes.admin import bp_admin

    app.register_blueprint(bp_main)
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_fb)
    app.register_blueprint(bp_media)
    app.register_blueprint(bp_admin)

    return app
