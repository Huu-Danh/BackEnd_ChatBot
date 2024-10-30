from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import openai
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams
from qdrant_client.http.models import PointStruct
import os
from uuid import uuid4  # Thêm thư viện UUID để tạo ID duy nhất
from typing import List, Dict
from config import settings


# Khai báo biến
model = settings.MODEL_NAME
collection_name = settings.COLLECTION_NAME

# Set the OpenAI API key
openai.api_key = settings.API_KEY_OPENTAI

# Khởi tạo Qdrant
qdrant_client = QdrantClient(
    url=settings.URL_QDRANT,
    api_key=settings.API_KEY_QDRANT
)

# # Tạo mới collection hoặc kiểm tra sự tồn tại của nó
# try:
#     qdrant_client.create_collection(
#         collection_name=collection_name,
#         vectors_config=VectorParams(size=3072, distance="Cosine"),
#     )
# except Exception as e:
#     print(f"Collection already exists or could not be created: {e}")

# Chuyển đổi nội dung thành vectors và lưu vào Qdrant
def add_vector_db(content):
    if not content:
        print("Không có dữ liệu")
        return None

    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n", "."],
        chunk_size=3072,
    )

    # Chia nhỏ văn bản
    chunks = text_splitter.split_text(content)
    print(len(chunks))
    print(chunks)

    # Tạo embedding cho từng chunk
    embeddings = []
    for chunk in chunks:
        response = openai.Embedding.create(input=chunk, model=model)
        
        # Kiểm tra xem phản hồi có phải là một từ điển không
        if isinstance(response, dict):
            # Lấy danh sách data
            data = response.get('data', [])
            
            # Kiểm tra xem data có phải là danh sách và chứa phần tử không
            if data and isinstance(data, list):
                first_data = data[0]

                # Kiểm tra nếu first_data chứa trường embedding
                if isinstance(first_data, dict) and 'embedding' in first_data:
                    embedding = first_data.get('embedding')  # Lấy giá trị embedding
                    embeddings.append(embedding)  # Thêm embedding vào danh sách


        # Lưu các vector vào Qdrant
        points = [
            PointStruct(
                id=str(uuid4()),  # Tạo UUID duy nhất cho mỗi điểm
                vector=embedding,
                payload={"text": chunk}
            )
            for embedding, chunk in zip(embeddings, chunks)
        ]

        qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
