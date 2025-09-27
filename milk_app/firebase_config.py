
# milk_app/firebase_config.py
import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class FirebaseConfig:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            try:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
                self._initialized = True
                logger.info("Firebase Admin SDK initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {e}")
                raise
    
    @staticmethod
    def verify_id_token(id_token):
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Firebase token verification failed: {e}")
            return None
