import os
import logging
from app import app  # noqa: F401

# Configure logging for production deployment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Check required environment variables for deployment
required_env_vars = ["DATABASE_URL"]
missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

if missing_vars:
    logger.warning(f"Missing environment variables: {missing_vars}")
    logger.info("App will attempt to start with defaults")
else:
    logger.info("All required environment variables are set")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    
    logger.info(f"Starting Flask app on port {port}, debug={debug}")
    app.run(host="0.0.0.0", port=port, debug=debug)
