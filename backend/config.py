import os
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()

# Get the API key from environment variables
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not GOOGLE_MAPS_API_KEY:
    raise ValueError("No Google Maps API key set. Please define it in your .env file or environment.")
