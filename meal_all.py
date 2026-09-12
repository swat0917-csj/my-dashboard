import os
import requests
import json
import re
import time
import io
from PIL import Image
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 1. KST (한국 표준시) 기준 오늘 & 내일 날짜 설정
kst = timezone(timedelta(hours=9))
now = datetime.now(kst)

today_dt = now
tomorrow_dt = now + timedelta(days=1)

today = today_dt.strftime("%Y%m%d")
today_display = today_dt.strftime("%Y-%m-%d")

tomorrow = tomorrow_dt.strftime("%Y%m%d")
tomorrow_display = tomorrow_dt.strftime("%m-%d")

current_hour = now.hour

# 2. GitHub Secrets 환경변수 로드
NEIS_API_KEY = os.environ.get("NEIS_API_KEY")
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY")
KAKAO_REFRESH_TOKEN = os.environ.get("KAKAO_REFRESH_TOKEN")

ATPT_OFCDC_SC_CODE = "M10"
SD_SCHUL_CODE = "8011201"

# 3. NEIS 급식 API 조회 함수 (날짜별 파라미터 지원)
def get_neis_menu_by_date(ymd_str):
    neis_url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": NEIS_API_KEY,
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "MLSV_YMD": ymd_str
    }
    try:
        res = requests.get(neis_url, params=params, timeout=10)
        data = res.json()
        if "mealServiceDietInfo" in data:
            raw_menu = data["mealServiceDietInfo"][1]["row"][0]["DDISH_NM"].replace("<br/>", "\n")
            clean_menu = re.sub(r'\([0-9\.]+\)', '', raw_menu)
            items = [line.strip() for line in clean_menu.splitlines() if line.strip()]
            return items
    except Exception as e:
        print(f"⚠️ NEIS API 오류 ({ymd_str}): {e}")
    return None

# 기존 호환용 함수
def get_neis_menu(ymd):
    return get_neis_menu_by_date(ymd)

# 4. 이미지 1:1 정사각형 가공 함수
def process_image_to_square(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = img.size
        max_dim = max(width, height)

        new_img = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
        offset = ((max_dim - width) // 2, (max_dim - height) // 2)
        new_img.paste(img, offset)

        new_img = new_img.resize((800, 800), Image.Resampling.LANCZOS)

        output = io.BytesIO()
        new_img.save(output, format="JPEG", quality=90)
        return output.getvalue()
    except Exception as e:
        print(f"⚠️ 이미지 가공 오류: {e}")
        return image_bytes

# 5. 학교 급식 식판 사진 수집 함수
def get_school_meal_image_bytes():
    target_url = "https://school.cbe.go.kr/jukrim-e/M01030401/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": "https://school.cbe.go.kr/"
    }

    try:
        res = requests.get(target_url, headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            img_src = None

            for img in soup.find_all("img"):
                src = img.get("src", "")
                if not src:
                    continue
                src_lower = src.lower()
                if any(k in src_lower for k in ["upload", "meal", "diet", "board", "file", "atch"]):
                    if not any(x in src_lower for x in ["icon", "btn", "banner", "logo", "common", "bg_"]):
                        img_src = urljoin(target_url, src)
                        break

            if not img_src:
                for img in soup.find_all("img"):
                    src = img.get("src", "")
                    if (src.startswith("http") or src.startswith("/")) and not any(x in src.lower() for x in ["icon", "btn", "banner", "logo", "common", "main"]):
                        img_src = urljoin(target_url, src)
                        break

            if img_src:
                print(f"📸 식판 이미지 URL 발견: {img_src}")
                img_res = requests.get(img_src, headers=headers, timeout=15)
                if img_res.status_code == 200 and len(img_res.content) > 1000:
                    print(f"✅ 이미지 다운로드 성공 ({len(img_res.content)} bytes)")
                    return process_image_to_square(img_res.content)
    except Exception as e:
        print(f"⚠️ 이미지 수집 예외 발생: {e}")

    return None

# 6. 카카오 CDN 이미지 업로드 함수
def upload_image_to_kakao(image_bytes, access_token):
    upload_url = "https://kapi.kakao.com/v2/api/talk/message/image/upload"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {"file": ("meal.jpg", image_bytes, "image/jpeg")}
    try:
        res = requests.post(upload_url, headers=headers, files=files, timeout=15)
        data = res.json()
        if "infos" in data and "original" in data["infos"]:
            cdn_url = data["infos"]["original"]["url"].replace("http://", "https://")
            print(f"✅ 카카오 CDN 업로드 성공: {cdn_url}")
            return cdn_url
    except Exception as e:
        print(f"⚠️ 카카오 이미지 업로드 예외: {e}")
    return None

# 7. 수신 동의한 카카오 친구 UUID 목록 조회 함수
def get_kakao_friends_uuids(access_token):
    friends_url = "https://kapi.kakao.com/v1/api/talk/friends"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        res = requests.get(friends_url, headers=headers, timeout=10)
        data = res.json()
        if "elements" in data:
            uuids = [friend["uuid"] for friend in data["elements"]]
            print(f"👥 수신 동의한 친구 수: {len(uuids)}명")
            return uuids
        else:
            print(f"⚠️ 친구 목록 응답 확인: {data}")
    except Exception as e:
        print(f"⚠️ 친구 목록 조회 실패: {e}")
    return []

# 8. 메인 실행 프로세스 (GitHub Actions 자동화용)
if __name__ == "__main__" and KAKAO_REFRESH_TOKEN and KAKAO_REST_API_KEY:
    token_url = "https://kauth.kakao.com/oauth/token"
    token_data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN
    }
    token_res = requests.post(token_url, data=token_data).json()
    access_token = token_res.get("access_token")

    if access_token:
        today_menu = get_neis_menu(today)

        if today_menu:
            payloads = []

            if current_hour < 10:
                text_template = {
                    "object_type": "text",
                    "text": f"🍱 오늘({today_display}) 죽림초 급식\n\n" + "\n".join(today_menu),
                    "link": {
                        "web_url": "https://school.cbe.go.kr/jukrim-e/M01030401/",
                        "mobile_web_url": "https://school.cbe.go.kr/jukrim-e/M01030401/"
                    }
                }
                payloads.append(text_template)

            else:
                image_bytes = get_school_meal_image_bytes()
                kakao_cdn_url = None
                if image_bytes:
                    kakao_cdn_url = upload_image_to_kakao(image_bytes, access_token)

                if current_hour < 13 and not kakao_cdn_url:
                    print("⏳ [12:50 1차 시도] 식판 사진 미등록 상태. 14:00에 재시도합니다.")
                    exit(0)

                if kakao_cdn_url:
                    if len(today_menu) > 3:
                        half = (len(today_menu) + 1) // 2
                        line1 = ", ".join(today_menu[:half])
                        line2 = ", ".join(today_menu[half:])
                        today_desc = f"{line1}\n{line2}"
                    else:
                        today_desc = ", ".join(today_menu)

                    feed_template = {
                        "object_type": "feed",
                        "content": {
                            "title": f"🍱 오늘({today_display}) 죽림초 급식",
                            "description": today_desc,
                            "image_url": kakao_cdn_url,
                            "link": {
                                "web_url": "https://school.cbe.go.kr/jukrim-e/M01030401/",
                                "mobile_web_url": "https://school.cbe.go.kr/jukrim-e/M01030401/"
                            }
                        }
                    }
                    payloads.append(feed_template)
                else:
                    text_template = {
                        "object_type": "text",
                        "text": f"🍱 오늘({today_display}) 죽림초 급식 (사진 미등록)\n\n" + "\n".join(today_menu),
                        "link": {
                            "web_url": "https://school.cbe.go.kr/jukrim-e/M01030401/",
                            "mobile_web_url": "https://school.cbe.go.kr/jukrim-e/M01030401/"
                        }
                    }
                    payloads.append(text_template)

                tomorrow_menu = get_neis_menu(tomorrow)
                if tomorrow_menu:
                    tomorrow_text = f"📅 내일({tomorrow_display}) 죽림초 급식 미리보기\n\n" + "\n".join(tomorrow_menu)
                else:
                    tomorrow_text = f"📅 내일({tomorrow_display})은 급식이 없습니다. (주말/휴일)"

                tomorrow_template = {
                    "object_type": "text",
                    "text": tomorrow_text,
                    "link": {
                        "web_url": "https://school.cbe.go.kr/jukrim-e/M01030401/",
                        "mobile_web_url": "https://school.cbe.go.kr/jukrim-e/M01030401/"
                    }
                }
                payloads.append(tomorrow_template)

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            for template in payloads:
                send_self_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
                requests.post(send_self_url, headers=headers, data={"template_object": json.dumps(template, ensure_ascii=False)})
                time.sleep(0.3)
            print("🎉 [나와의 채팅] 전송 완료!")

            friends_uuids = get_kakao_friends_uuids(access_token)
            if friends_uuids:
                chunk_size = 5
                for i in range(0, len(friends_uuids), chunk_size):
                    batch_uuids = friends_uuids[i:i + chunk_size]
                    for template in payloads:
                        send_friends_url = "https://kapi.kakao.com/v1/api/talk/friends/message/default/send"
                        params = {
                            "receiver_uuids": json.dumps(batch_uuids),
                            "template_object": json.dumps(template, ensure_ascii=False)
                        }
                        res = requests.post(send_friends_url, headers=headers, data=params)
                        if res.status_code == 200:
                            print(f"🎉 [친구 {len(batch_uuids)}명] 전송 성공!")
                        else:
                            print(f"❌ [친구] 전송 실패:", res.json())
                        time.sleep(0.3)
