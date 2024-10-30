import hashlib
import base64
import requests
import os
from dotenv import load_dotenv


load_dotenv()  # Load biến môi trường từ .env file
# Lấy giá trị của các biến môi trường
USERNAME_CHAT = os.getenv("USERNAME_CHAT", "default_db_name")
PASSWORD = os.getenv("PASSWORD", "default_db_name")
CLIENTID = os.getenv("CLIENTID", "default_db_name")
ACCESSKEY = os.getenv("ACCESSKEY", "default_db_name")
GET_UNIXTIME = os.getenv("GET_UNIXTIME", "default_db_name")
# Chuỗi bạn muốn băm
username = "Autobot"
password = PASSWORD
clientId = CLIENTID
Accesskey = ACCESSKEY

# hash password
# Tạo MD5 hash
md5_hash = hashlib.md5(password.encode()).digest()
# Mã hóa MD5 hash bằng Base64
base64_encoded = base64.b64encode(md5_hash).decode('utf-8')
print("hash_pasword",base64_encoded)
def get_unixtime():
    # Gửi yêu cầu GET đến API
    
    response = requests.get(GET_UNIXTIME)
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

# Gọi hàm get_unixtime
unixtime = get_unixtime()

if unixtime:
    # Tạo hash raw
    hashraw = username + clientId + base64_encoded + unixtime + Accesskey
    md5_hashraw = hashlib.md5(hashraw.encode()).digest()
    base64_hashraw = base64.b64encode(md5_hashraw).decode('utf-8')

    print("Hash raw:", hashraw)
    print("Base64 hash raw:", base64_hashraw)

# Hàm get token
def get_token(client_id, hash_value):
    # URL của API
    url = "http://108.108.110.22:4100/auth/get-token"

    # Tham số header
    headers = {
        'ClientId': client_id,
        'Hash': hash_value,
        'Content-Type': 'application/json',
    }
    body = {
        'username': username,
        'passWord': password
    }

    response = requests.post(url, headers=headers,json=body)

    # Kiểm tra mã trạng thái HTTP
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Yêu cầu không thành công. Mã trạng thái: {response.status_code}")
        print("Dữ liệu trả về:", response.text)  # In toàn bộ dữ liệu trả về
        return None

token_data = get_token(clientId, base64_hashraw)
print("Dữ liệu trả về:", token_data)

def extract_tour_details(tours):
    result =""
    for tour in tours:
        tourName = tour.get("tourName") # tên tour
        tourCode = tour.get("tourCode") # tour code
        tourUrl = tour.get("tourUrl") # đường dẫn liên kết tour
        departureName = tour.get("departureName") # địa điểm khởi hành
        departureDate = tour.get("departureDate") # ngày khỏi hành tour
        endDate = tour.get("endDate") # ngày kết thúc tour
        salePrice = tour.get("salePrice")
        salePrice_vnd = f"{salePrice:,.0f} VND".replace(",", ".")
        discountAmount = tour.get("discountAmount") # số tiền giảm
        discountPrice = salePrice - discountAmount
        discountPrice_vnd = f"{discountPrice:,.0f} VND".replace(",", ".")
        discountTitle = tour.get("discountTitle") # tiêu đề mô tả giảm giá tour
        durationTime = tour.get("durationTime") # thời gian ở
        remaxPax = tour.get("remaxPax") # số lượng khách tối đa
        expirationDate = tour.get("expirationDate") # ngày hết hạn ưu đãi
        dayStay = tour.get("dayStay") # số ngày lưu trú tour
        rating = tour.get("rating") # điểm đánh giá
        rateCount = tour.get("rateCount") # số lượng đánh giá
        result += f"\tTên tour:  {tourName} , mã tour: {tourCode}, đường dẫn đến tour: {tourUrl}, địa điểm khởi hành: {departureName}, ngày khởi hành: {departureDate}, ngày kết thúc tour: {endDate}, giá tour: {salePrice_vnd}, giá tour sau khi giảm: {discountPrice_vnd}, tiêu đề mô tả: {discountTitle}, thời gian của tour: {durationTime}, số lượng tối đa có thể đặt: {remaxPax}, ngày hết hạn ưu đãi: {expirationDate}, điểm đánh giá: {rating}, số lượng đánh giá: {rateCount}. \n\n"
    return result

def extract_combo_details(combos):
    result =""
    for cb in combos:
        title = cb.get("title")
        hotelName = cb.get("hotelName")
        price = cb.get("price")
        departureDate = cb.get("departureDate")
        departureName = cb.get("departureName")
        loaiComboName = cb.get("loaiComboName")
        tourCode = cb.get("tourCode")
        comboCode = cb.get("comboCode")

    return result


def get_last_minute_tours():
    url = "http://vtvtest:4100/core/tour/get-list-tour-last-minute"

    # Gửi yêu cầu GET
    response = requests.get(url)

    # Kiểm tra mã trạng thái HTTP
    if response.status_code == 200:
        data = response.json()
        tours = data["response"]
        return tours
    else:
        print(f"Yêu cầu không thành công. Mã trạng thái: {response.status_code}")
        print("Dữ liệu trả về:", response.text)
        return None

def get_list_tour_special():
    url = "http://vtvtest:4100/core/core/Combo/get-list-tour-special"

    # Gửi yêu cầu GET
    response = requests.get(url)

    # Kiểm tra mã trạng thái HTTP
    if response.status_code == 200:
        data = response.json()
        combos = data["response"]
        return combos
    else:
        print(f"Yêu cầu không thành công. Mã trạng thái: {response.status_code}")
        print("Dữ liệu trả về:", response.text)
        return None

def get_id_by_name(location_name):
    url = "http://vtvtest:4100/core/Menu/get-departure-from"
    headers = {
        'Authorization': f'bearer PozqqYJWGJxBmggIjErwuvl/rhQBK+oM/ZHub+sBIvgTeaXfejublJKrEwfZ/LCKbl/cCXRR999edmnV5UtUHhZ/BF6ro31bpn8RZNlQ3NDRWSmuuRQ3/SMVZuA8XBRq2sbMmf1Ddqkf1dH5m2NfC6Pb8wsLaXHniIq7wFDu7qyrMgr+LL2Mw+OFGMzBEQNysAiikIUBCiuLpgSzZ5tTVn6RUpWZgCFQqN6llug9DzyjaWF4HkZOan+qk3nTBqReUFHKEWWdwd20Hc5PJaZKiVIv5f2bgrUs9JPCCQlp4K4/ismQyCOuFSHA5R9cOS3Doz6KLwBNnV1UiJ9EGZpZ/e5ORqQjW5Uykd/li2lizCxcX7Ju9G5sHQRPOdKiafUumYOxZTsi97cUivoEafiIduHLjSeIbGkYer5DyTXdk3Q=',
        'ClientId': CLIENTID,
        'Content-Type': 'application/json',
        'Accept-Language': 'vi-VN'
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    print("\n\n\n")
    departure = data["response"]
    # Tìm trong danh sách địa điểm
    for location in departure:
        if location_name in location["name"]:
            return location["id"]
    return 0

kq = get_id_by_name("hồ chí minh")
print(kq)