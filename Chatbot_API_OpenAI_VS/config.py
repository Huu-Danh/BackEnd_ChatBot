from pydantic import BaseModel
import os

class Settings(BaseModel):
    API_KEY_OPENTAI: str = "default_opentai_key"
    API_KEY_QDRANT: str = "default_qdrant_key"
    API_KEY_COHERE: str = "default_cohere_key"
    USERNAME_CHAT: str = "default_username"
    PASSWORD: str = "default_password"
    CLIENTID: str = "default_clientid"
    ACCESSKEY: str = "default_accesskey"
    URL_QDRANT: str = "default_url_qdrant"
    CLIENT_MONGDB: str = "default_client_mongodb"
    MODEL_NAME: str = "default_model_name"
    MODEL: str = "default_model"
    COLLECTION_NAME: str = "default_collection_name"
    DB_NAME: str = "default_db_name"
    GET_UNIXTIME: str = "default_get_unixtime"
    
    @classmethod
    def from_env(cls):
        return cls(
            API_KEY_OPENTAI=os.getenv("API_KEY_OPENTAI", "default_opentai_key"),
            API_KEY_QDRANT=os.getenv("API_KEY_QDRANT", "default_qdrant_key"),
            API_KEY_COHERE=os.getenv("API_KEY_COHERE", "default_cohere_key"),
            USERNAME_CHAT=os.getenv("USERNAME_CHAT", "default_username"),
            PASSWORD=os.getenv("PASSWORD", "default_password"),
            CLIENTID=os.getenv("CLIENTID", "default_clientid"),
            ACCESSKEY=os.getenv("ACCESSKEY", "default_accesskey"),
            URL_QDRANT=os.getenv("URL_QDRANT", "default_url_qdrant"),
            CLIENT_MONGDB=os.getenv("CLIENT_MONGDB", "default_client_mongodb"),
            MODEL_NAME=os.getenv("MODEL_NAME", "default_model_name"),
            MODEL=os.getenv("MODEL", "default_model"),
            COLLECTION_NAME=os.getenv("COLLECTION_NAME", "default_collection_name"),
            DB_NAME=os.getenv("DB_NAME", "default_db_name"),
            GET_UNIXTIME=os.getenv("GET_UNIXTIME", "default_get_unixtime")
        )

# Khởi tạo đối tượng settings từ biến môi trường
settings = Settings.from_env()
