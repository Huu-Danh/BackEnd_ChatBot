from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from pymongo import MongoClient
from utils.utils import search_vector, rank_vector, generate_answer
import openai
import cohere
from datetime import datetime
from config import settings

router = APIRouter() 

openai.api_key = settings.API_KEY_OPENTAI
# Khởi tạo Qdrant client
qdrant_client = QdrantClient(
    url= settings.URL_QDRANT,
    api_key= settings.API_KEY_QDRANT
)

# Kết nối với MongoDB 
client = MongoClient(settings.CLIENT_MONGDB)  # Sử dụng URI kết nối đúng của bạn
db = client[settings.DB_NAME]
chat_history_collection = db["chats"]
co = cohere.Client(settings.API_KEY_COHERE)

class QueryRequest(BaseModel):
    query: str
    roomchat: str
    time: datetime
    
class Query(BaseModel):
    query: str
    roomchat: str
    time: datetime
    role: str
    
@router.post("/chatbox")
async def chatbox_response(request: Query):
    print(request)
    try:
        print(request.query)
        user_message = {
            "role": request.role,
            "msg": request.query,
            "time": request.time,
            "isNew": True
        }
         # Tìm kiếm phòng chat
        room = chat_history_collection.find_one({"roomchat": request.roomchat})
        
        if room:
            # Chèn tin nhắn của User và Bot vào mảng Messages của phòng đã tồn tại
            result_user = chat_history_collection.update_one(
                {"roomchat": request.roomchat},
                {
                    "$push": {"Messages": user_message},
                    "$inc": {"newMessageCount": 1}  # Tăng tổng số tin nhắn mới
                }
            )
            
            # Kiểm tra nếu tin nhắn đã được chèn thành công
            if result_user.modified_count == 0:
                raise HTTPException(status_code=500, detail="Không thể chèn tin nhắn")

            print(f"Lưu user_message: {result_user}")
        else:
            raise HTTPException(status_code=404, detail=f"Room '{request.roomchat}' not found")
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/chatbot/")
async def chatbot_response(request: QueryRequest):
    print(request)
    try:
        # Tìm kiếm ngữ cảnh liên quan
        content = search_vector(request.query, top_k=100)
        # Gọi hàm để lọc dữ liệu thêm lần nữa
        context = rank_vector(content, request.query)
        # in ra dữ liệu đã rank
        for ct in context:
            print(ct)
            print("\n\n")
         # Lấy lịch sử trò chuyện (hoặc chỉ lấy của phòng nếu muốn)
        chat_history = list(chat_history_collection.find({"roomchat": request.roomchat}, {"Messages": 1}))
        if chat_history:
            messages = chat_history[0].get("Messages", [])
             # Lọc tin nhắn chỉ của user và assistant (giả sử role của user là "user" và assistant là "assistant")
            filtered_messages = [msg for msg in messages if msg['role'] in ['user', 'assistant']]
        #chat_history = list(chat_history_collection.find({}, {"_id": 0}))
        # Tạo câu trả lời từ model GPT 4o mini
        answer = generate_answer(context, request.query,filtered_messages)
        
        # Tạo tin nhắn của User và Bot
        user_message = {
            "role": "user",
            "msg": request.query,
            "time": request.time
        }
        bot_message = {
            "role": "assistant",
            "msg": answer,
            "time": datetime.now()
        }
        
        # Tìm kiếm phòng chat
        room = chat_history_collection.find_one({"roomchat": request.roomchat})
        
        if room:
            # Chèn tin nhắn của User và Bot vào mảng Messages của phòng đã tồn tại
            result_user = chat_history_collection.update_one(
                {"roomchat": request.roomchat},
                {"$push": {"Messages": user_message}}
            )
            result_bot = chat_history_collection.update_one(
                {"roomchat": request.roomchat},
                {"$push": {"Messages": bot_message}}
            )

            # Kiểm tra nếu tin nhắn đã được chèn thành công
            if result_user.modified_count == 0 or result_bot.modified_count == 0:
                raise HTTPException(status_code=500, detail="Không thể chèn tin nhắn")
            print(f"Lưu user_message: {result_user}")
            print(f"Lưu assistant_message: {result_bot}")
        else:
            raise HTTPException(status_code=404, detail=f"Room '{request.roomchat}' not found")
        return {"query": request.query, "answer": answer}
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    