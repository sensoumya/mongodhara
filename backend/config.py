import os

# MongoDB URI from env or default
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
