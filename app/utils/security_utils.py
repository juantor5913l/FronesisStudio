from itsdangerous import URLSafeSerializer
from app.config import Config

serializer = URLSafeSerializer(Config.SECRET_KEY)

def encriptar_id(id_cita):
    return serializer.dumps(id_cita)

def desencriptar_id(token):
    try:
        return serializer.loads(token)
    except Exception:
        return None
