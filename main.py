from app.factory import create_app
from dotenv import load_dotenv

app = create_app()

load_dotenv("/home/arpit_createx/m360-backend/.env")

# if __name__ == "__main__":
#     import uvicorn
#
#     from app.core.config import get_settings
#
#     settings = get_settings()
#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=settings.server_port,
#         reload=True,
#         log_level=settings.logging_level.lower(),
#     )
