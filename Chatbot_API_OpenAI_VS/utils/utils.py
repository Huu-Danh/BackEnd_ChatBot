import openai
import cohere
import json
import requests
import base64
import hashlib
from config import settings
from qdrant_client import QdrantClient
from pymongo import MongoClient
from datetime import datetime
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor

openai.api_key = settings.API_KEY_OPENTAI
# Khởi tạo Qdrant client
qdrant_client = QdrantClient(
    url=settings.URL_QDRANT,
    api_key=settings.API_KEY_QDRANT
)

# Kết nối với MongoDB
client = MongoClient(settings.CLIENT_MONGDB)  # Sử dụng URI kết nối đúng của bạn
db = client[settings.DB_NAME]
chat_history_collection = db["chats"]
co = cohere.Client(settings.API_KEY_COHERE)



# hash password
# Tạo MD5 hash
md5_hash = hashlib.md5(settings.PASSWORD.encode()).digest()
# Mã hóa MD5 hash bằng Base64
base64_encoded = base64.b64encode(md5_hash).decode('utf-8')

def get_unixtime():
    # Gửi yêu cầu GET đến API
    response = requests.get("http://vtvtest:4100/auth/get-unixtime")
    # Kiểm tra mã trạng thái HTTP
    if response.status_code == 200:
        # Lấy dữ liệu từ phản hồi và chuyển đổi thành đối tượng Python
        data = response.json()

        # Trích xuất giá trị từ trường 'response'
        unixtime = data.get('response')

        if unixtime:
            # In ra giá trị
            print("Unix time:", unixtime)
            return unixtime
        else:
            print("Không tìm thấy giá trị 'response' trong dữ liệu.")
            return None
    else:
        print(f"Yêu cầu không thành công. Mã trạng thái: {response.status_code}")
        return None

# Hàm get token
def get_token():
    # URL của API
    url = "http://vtvtest:4100/auth/get-token"

    # Gọi hàm get_unixtime
    unixtime = get_unixtime()

    if unixtime:
        # Tạo hash raw
        hashraw = settings.USERNAME_CHAT + settings.CLIENTID + base64_encoded + unixtime + settings.ACCESSKEY
        md5_hashraw = hashlib.md5(hashraw.encode()).digest()
        base64_hashraw = base64.b64encode(md5_hashraw).decode('utf-8')

        print("Hash raw:", hashraw)
        print("Base64 hash raw:", base64_hashraw)
    # Tham số header
    headers = {
        'ClientId': settings.CLIENTID,
        'Hash': base64_hashraw,
        'Content-Type': 'application/json',
    }

    body = {
        'username': settings.USERNAME_CHAT,
        'passWord': settings.PASSWORD
    }

    response = requests.post(url, headers=headers,json=body)

    # Kiểm tra mã trạng thái HTTP
    if response.status_code == 200:
        data = response.json()
        print(data["response"]["token"])
        return data["response"]["token"]
    else:
        print(f"Yêu cầu không thành công. Mã trạng thái: {response.status_code}")
        print("Dữ liệu trả về:", response.text)  # In toàn bộ dữ liệu trả về
        return None


gettoken = get_token()
# Hàm để tạo embedding cho văn bản
def get_embedding(text, model):
    try:
        response = openai.Embedding.create(input=text, model=model)
        
        # Đảm bảo response là dictionary
        if not isinstance(response, dict):
            raise ValueError("Loại phản hồi không như mong đợi từ OpenAI API.")
        
        # Kiểm tra xem có khóa 'data' trong phản hồi không
        if 'data' not in response:
            raise KeyError("Không tìm thấy khóa 'data' trong phản hồi.")
        
        # Trích xuất embedding
        embedding = response['data'][0]['embedding']
        
        return embedding
    except Exception as e:
        print(f"Đã xảy ra lỗi: {e}")
        return None

# Hàm tìm kiếm vectors trong Qdrant
def search_vector(query, top_k=5):
    # Tạo embedding cho truy vấn
    query_embedding = get_embedding(query, settings.MODEL_NAME)
    
    # Kiểm tra nếu query_embedding là None
    if query_embedding is None:
        raise ValueError("Không thể tạo embedding cho truy vấn. Vui lòng kiểm tra hàm get_embedding.")
    
    # Tìm kiếm trong Qdrant
    search_result = qdrant_client.search(
        collection_name=settings.COLLECTION_NAME,
        query_vector=query_embedding,
        limit=top_k
    )

 # Kết hợp các kết quả thành một ngữ cảnh
    context = []
    for result in search_result:
        # Kiểm tra nếu result.payload không phải là None
        if result.payload and 'text' in result.payload:
            context.append(result.payload['text'])
        else:
            # Xử lý trường hợp không có 'text' trong payload hoặc payload là None
            context.append("No text available")
    return context

# hàm xếp hạng lại vector db
def rank_vector(context, query):
    response = co.rerank(
        model="rerank-multilingual-v3.0",
        query=query,
        documents=context,
        top_n=5,
    )

    indexes = None
    for item in response:
        if item[0] == 'results':
            results = item[1]
            indexes = [result.index for result in results]
            
    # Kiểm tra nếu indexes là None trước khi sử dụng
    if indexes is None:
        raise ValueError("Không tìm thấy kết quả xếp hạng trong phản hồi.")
    
    content = []
    for index in indexes:
        # Kiểm tra xem chỉ mục có hợp lệ không trước khi truy cập context
        if index < len(context):
            content.append(context[index])
        else:
            # Xử lý trường hợp chỉ mục không hợp lệ
            content.append("Nội dung không có sẵn")

    return content

def extract_tour_details(tours):
    result =""
    for tour in tours:
        tourCode = tour.get("tourCode") # tour code
        tourUrl = tour.get("tourUrl") # đường dẫn liên kết tour
        departureName = tour.get("departureName") # địa điểm khởi hành
        departureDate = tour.get("departureDate") # ngày khỏi hành tour
        discountPrice = tour.get("discountPrice") # gia tour sau khi giam
        discountPrice_vnd = f"{discountPrice:,.0f} VND".replace(",", ".")
        discountTitle = tour.get("discountTitle") # tiêu đề mô tả giảm giá tour
        expirationDate = tour.get("expirationDate") # ngày hết hạn ưu đãi
        remaxPax = tour.get("remaxPax") # số lượng nhận
        pageId = tour.get("pageId") # pageID

        result += f"""Tiêu đề mô tả: {discountTitle},
                      Xem chi tiết tại đây: https://travel.com.vn/chuong-trinh/{tourUrl}-pid-{pageId}?tourCode={tourCode},
                      Địa điểm khởi hành: {departureName},
                      Ngày khởi hành: {departureDate},
                      Giá tour: {discountPrice_vnd},
                      Số chỗ còn nhận: {remaxPax},
                      Ngày hết hạn ưu đãi: {expirationDate}.\n\n"""
    return result

def extract_tour_combo(combos):
    result =""
    for combo in combos:
        comboTypeName = combo.get("comboTypeName")
        title = combo.get("title")
        hotelName = combo.get("hotelName")
        transTypeName = combo.get("transTypeName")
        price = combo.get("price")
        departureDate = combo.get("departureDate")
        departureName = combo.get("departureName")
        loaiComboName = combo.get("loaiComboName")

        result += f"""Loại combo: {comboTypeName},
                      Tiêu đề: {title},
                      Tên khách sạn: {hotelName},
                      Phương tiện: {transTypeName},
                      Giá: {price},
                      Ngày khởi hành: {departureDate},
                      Nơi khởi hành: {departureName},
                      Tên loai nghỉ dưỡng: {loaiComboName}.\n\n"""
    return result

def extract_new_listest(news):
    result =""
    for new in news:
        newsId = new.get("newsId")
        title = new.get("title")
        sumarry = new.get("sumarry")
        newsURL = new.get("newsURL")
        result += f"""Tiêu đề: {title},
                      Mô tả: {sumarry},
                      Xem chi tiết tại: https://travel.com.vn/tin-tuc-du-lich/{newsURL}-v{newsId}.aspx\n\n"""
    return result

# Hàm gọi API để lấy thông tin các tour giờ chót
def get_last_minute_tours():
    url = "http://vtvtest:4100/core/tour/get-list-tour-last-minute"
    token = gettoken
    headers = {
        'Authorization': f'Bearer {token}',
        'ClientId': settings.CLIENTID,
        'Content-Type': 'application/json',
        'Accept-Language': 'vi-VN'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        tours = data["response"]
        #   print(extract_tour_details(tours))
        return extract_tour_details(tours)
    else:
        print(f"Yêu cầu không thành công. Mã trạng thái: {response.status_code}")
        print("Dữ liệu trả về:", response.text)
        return None

# hàm gọi các combo
def get_list_tour_special():
    url = "http://vtvtest:4100/core/Combo/get-list-tour-special"
    token = gettoken
    headers = {
        'Authorization': f'Bearer {token}',
        'ClientId': settings.CLIENTID,
        'Content-Type': 'application/json',
        'Accept-Language': 'vi-VN'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        combos = data["response"]
        print(extract_tour_combo(combos))
        return extract_tour_combo(combos)
    else:
        print(f"Yêu cầu không thành công. Mã trạng thái: {response.status_code}")
        print("Dữ liệu trả về:", response.text)
        return None

#hàm gọi các tin tức theo số lượng
def get_news_list_lastest(toprecord: int = 5):
    url = "http://vtvtest:4100/core/News/get-news-list-lastest"
    token = gettoken
    headers = {
        'Authorization': f'Bearer {token}',
        'ClientId': settings.CLIENTID,
        'Content-Type': 'application/json',
        'Accept-Language': 'vi-VN'
    }
    params = {'TopRecord': int(toprecord)}  # Thêm từ khóa như tham số truy vấn
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        news = data["response"]
        print(extract_new_listest(news))
        return extract_new_listest(news)
    else:
        print(f"Yêu cầu không thành công. Mã trạng thái: {response.status_code}")
        print("Dữ liệu trả về:", response.text)
        return None

#hàm gọi các tin tức theo từ khóa
def get_news_search_keyword(keyword):
    url = "http://vtvtest:4100/core/News/get-news-search-keyword"
    token = gettoken
    headers = {
        'Authorization': f'Bearer {token}',
        'ClientId': settings.CLIENTID,
        'Content-Type': 'application/json',
        'Accept-Language': 'vi-VN'
    }
    params = {'keyword': keyword}  # Thêm từ khóa như tham số truy vấn
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        news = data["response"]
        print(extract_new_listest(news))
        return extract_new_listest(news)
    else:
        print(f"Yêu cầu không thành công. Mã trạng thái: {response.status_code}")
        print("Dữ liệu trả về:", response.text)
        return None

# hàm gọi lấy id của tỉnh thành
def get_id_by_name(location_name):
    url = "http://vtvtest:4100/core/Menu/get-departure-from"
    token = gettoken
    headers = {
        'Authorization': f'Bearer {token}',
        'ClientId': settings.CLIENTID,
        'Content-Type': 'application/json',
        'Accept-Language': 'vi-VN'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        departure = data["response"]
    # Tìm trong danh sách địa điểm
    for location in departure:
        if location_name in location["name"]:
            return location["id"]
    return 0

# hàm tạo url
def answer_url(departureFrom: int, destinationTo: str, date: str =""):
    if not date:
        now = datetime.now()
        # Định dạng ngày theo định dạng YYYY-MM-DD
        get_date =  now.strftime('%Y-%m-%d')
    else:
        get_date = date
    encoded_destination = quote(destinationTo)
    answer = f"""Danh sách tour khởi hành từ {departureFrom}, vui lòng tham khảo theo link sau: 'https://travel.com.vn/du-lich-vietravel.aspx?fromDate={get_date}&text={encoded_destination}&departureFrom={departureFrom}'"""
    return answer

# Hàm tạo câu trả lời từ model GPT 4o mini
def generate_answer(context, query, chat_history):

    # Sử dụng GPT 4o mini để tạo câu trả lời
    messages = [
        {"role": "system",
         "content": """Bạn là trợ lý ảo thông minh hỗ trợ và tư vấn cho khách hàng về các dịch vụ du lịch của Công ty Vietravel.Hãy dựa vào nội dung tìm thấy và trả lời cho khách hàng một cách chính xác nhất
         Khi khách hàng nhắn địa điểm (ví dụ: tìm tour Hà Nội, tour Nhật bản) thì yêu cầu khách hàng cung cấp thêm:
            -Địa điểm khởi hành
            -Thời gian khởi hành
        để biết thêm thông tin chi tiết. Những câu hỏi khác vẫn trả lời bình thường cho khách hàng.
         Nếu không trả lời được câu hỏi,thông báo rằng bạn chỉ hỗ trợ các nghiệp vụ của Vietravel. Ví dụ: "Xin lỗi bạn! Hiện tại trợ lý ảo Vietravel chỉ hỗ trợ các nghiệp vụ của Vietravel." 
         Luôn kèm theo đường dẫn để khách hàng có thể tự tìm hiểu thêm chi tiết.
         Bạn có thể trả lời bằng nhiều ngôn ngữ khác, hãy trả lời lại bằng ngôn ngữ mà người dùng sử dụng."""},
        {"role": "user", "content": f"Ngữ cảnh:\n{context}\n\nCâu hỏi: {query}\nCâu trả lời:"}
    ]

    # Thêm lịch sử trò chuyện vào messages
    for msg in chat_history:
        print({"role": msg['role'], "content": msg['msg']})
        messages.append({"role": msg['role'], "content": msg['msg']})

    # Thêm truy vấn hiện tại vào messages
    messages.append({"role": "user", "content": query})

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_last_minute_tours",
                "description": "Trả về kết quả các tour giờ chót. Khi khách hàng hỏi 'Hãy tìm giúp tôi các tour giờ chót'.Những câu hỏi không liên quan thì yêu cầu khách hàng cung cấp thêm thông tin",
                "parameters": {}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_list_tour_special",
                "description": "Trả về kết quả là các tour combo. Khi khách hàng tìm tour combo hoặc tour ưu đãi.",
                "parameters": {}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_news_list_lastest",
                "description": "Trả về kết quả là các tin tức mới. Khi khách hàng tìm 'Tìm giúp tôi bảng tin mới về du lịch.'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "toprecord": {
                            "type": "string",
                            "description": "Toprecord ví dụ: 5, 10,...",
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_news_search_keyword",
                "description": "Trả về kết quả là các tin tức mới theo địa điểm mà khách hàng yêu cầu ví dụ như: 'Tin tức Hồ Chí Minh",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "keyword là các địa điểm ví dụ:Hồ Chí Minh, Hà Nội, v.v",
                        }
                    },
                    "required": ["keyword"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "answer_url",
                "description": "Trả về cho khách hành đường danh sách tour có điểm khởi hành và thời điểm khởi hành đến đâu. Ví dụ khi khách hàng hỏi tour đi Nhật, sau đó khách hàng cung cấp thêm địa điểm khởi hành là TP. Hồ Chí Minh",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "departureFrom": {
                            "type": "integer",
                            "description": "departureFrom là các địa điểm xuất phát ví dụ:TP. Hồ Chí Minh - 1, Huế - 10, Quy Nhơn - 11, Phú Quốc - 13, Long Xuyên - 14, Quảng Ngãi - 15, Vũng Tàu - 16, Quảng Ninh - 17, Buôn Ma Thuột - 18, Vinh - 19, Cà Mau - 20, Rạch Giá - 22, Đà Lạt - 24, Thanh Hóa - 29, Hà Nội - 3, Đà Nẵng - 4, Thái Nguyên - 40, Cần Thơ - 5, Hải Phòng - 6, Bình Dương - 7, Nha Trang - 8. Tự chuyển đổi thành số nguyên",
                        },
                        "destinationTo": {
                            "type": "string",
                            "description": "destinationTo là các địa điểm đến ví dụ: Nhật Bản, Hàn Quốc, v.v",
                        },
                        "date": {
                            "type": "string",
                            "description": "Ngày khởi hành theo định dạng YYYY-MM-DD."
                        },
                    },
                    "required": ["destinationTo"],
                    "required": ["departureFrom"]
                },
            },
        },
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
    except Exception as e:
        print(f"Error during API call: {e}")
        return "Không thể tạo câu trả lời do lỗi hệ thống."
    
    # Truy cập nội dung phản hồi
    if isinstance(response, dict):
        choices = response.get('choices', [])
        if choices and isinstance(choices, list):
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                response_message = first_choice.get('message', {})
                if isinstance(response_message, dict):
                    tool_calls = response_message.get('tool_calls', [])
                    
    print(tool_calls)

    function_list = {
        "get_last_minute_tours": get_last_minute_tours,
        "get_list_tour_special": get_list_tour_special,
        "get_news_list_lastest": get_news_list_lastest,
        "get_news_search_keyword": get_news_search_keyword,
        "answer_url": answer_url,
    }


    with ThreadPoolExecutor() as executor:
        futures = []
        for tool_call in tool_calls:
            function_name = tool_call['function']['name']
            function_to_call = function_list.get(function_name)
            function_agrs = json.loads(tool_call['function']['arguments'])
            if function_to_call:
                if function_agrs:
                    # kiểm tra nếu nếu tìm địa điểm đến, điểm khởi hàng với từng thời gian khác nhau
                    if function_name == "answer_url" and "date" in function_agrs:
                        dates = function_agrs['date'].split(",")# Giả sử từ khóa được phân tách bởi dấu phẩy
                        for date in dates:
                            function_agrs_copy = function_agrs.copy()
                            function_agrs_copy['date'] = date.strip() #loai bo khoang trang
                            # Kiểm tra biến function_to_call trước khi submit
                            if function_to_call is not None:
                                future = executor.submit(function_to_call, **function_agrs_copy)
                            futures.append(future)
                    elif function_name == "answer_url" and "departureFrom" in function_agrs:
                        departureFroms = function_agrs['departureFrom'].split(",")
                        for dep in departureFroms:
                            function_agrs_copy = function_agrs.copy()
                            function_agrs_copy['departureFrom'] = dep.strip() #loai bo khoang trang
                            # Kiểm tra biến function_to_call trước khi submit
                            if function_to_call is not None:
                                future = executor.submit(function_to_call, **function_agrs_copy)
                                futures.append(future)
                else:
                    function_response = function_to_call()
                          
                        
        # Chờ các hàm hoàn thành và lấy kết quả
        for future in futures:
            function_response = future.result()
            messages.append({
                "role": "function",
                "name": function_name,
                "content": function_response
            })

    second_response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=2024,
        temperature=0.5,
    )

    if isinstance(second_response, dict):
        choices = second_response.get('choices', [])
        if choices and isinstance(choices, list):
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                message = first_choice.get('message', {})
                if isinstance(message, dict):
                    return message.get('content', '').strip()
