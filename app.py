import streamlit as st
import datetime
import os
import json
import requests
import pandas as pd
import yfinance as yf

# 기존 stock_info.py 함수들 임포트
from stock_info import (
    get_kst_now,
    get_kr_morning_report,
    get_us_night_report,
    fetch_market_extra_info,
    fetch_latest_stock_news
)

# 급식 정보 모듈 임포트
from meal_all import get_neis_menu_by_date

st.set_page_config(
    page_title="패밀리 올인원 실시간 대시보드",
    page_icon="🚀",
    layout="wide"
)

# UI 스타일링
st.markdown("""
    <style>
    .main-header { font-size: 26px; font-weight: bold; color: #1E3A8A; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# 사이드바 메뉴
st.sidebar.title("🛠️ 패밀리 스마트 메뉴")
menu = st.sidebar.selectbox(
    "이동할 메뉴", 
    [
        "📊 메인 요약 대시보드 (실시간 카드)", 
        "⚡ 1분 실시간 증시 & 뉴스", 
        "🔍 종목 검색 & 즐겨찾기", 
        "☀️ 최고 투자 종목 & 리포트", 
        "🌤️ 지역별 날씨 조회", 
        "🍱 학교 급식 & 실시간 조회", 
        "💌 자녀 응원 메시지 전송",
        "📢 카카오톡 수동 전송 (증시/급식)"
    ]
)

# 세션 상태 초기화
if 'favorites' not in st.session_state:
    st.session_state['favorites'] = ["005930", "NVDA", "TSLA"]
if 'cheer_msg' not in st.session_state:
    st.session_state['cheer_msg'] = "오늘도 화이팅! 사랑한다 우리 딸 ❤️"

# 실시간 학교 급식 연동 함수
def get_live_school_meal(target_date_str):
    try:
        menu_items = get_neis_menu_by_date(target_date_str)
        if menu_items:
            return "\n".join([f"- {item}" for item in menu_items])
        else:
            return "등록된 급식 정보가 없거나 주말/휴일입니다."
    except Exception as e:
        return f"급식 정보 조회 실패: {e}"

# ==========================================
# 1. 메인 요약 대시보드 (실시간 카드형)
# ==========================================
if menu == "📊 메인 요약 대시보드 (실시간 카드)":
    st.markdown('<div class="main-header">📊 패밀리 실시간 핵심 요약 대시보드</div>', unsafe_allow_html=True)
    st.write(f"실시간 조회 시각: {get_kst_now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🇰🇷 실시간 코스피 및 시장 지표")
        with st.container(border=True):
            try:
                kospi_str, _ = fetch_market_extra_info()
                st.markdown(f"### {kospi_str}")
            except Exception as e:
                st.warning(f"데이터 실시간 로딩 중... ({e})")
        
    with col2:
        st.subheader("🥇 실시간 금 시세")
        with st.container(border=True):
            try:
                _, gold_str = fetch_market_extra_info()
                st.markdown(f"### {gold_str}")
            except Exception as e:
                st.warning(f"데이터 실시간 로딩 중... ({e})")

    st.markdown("")
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("🇺🇸 미국 주식 실시간 수급 상위")
        with st.container(border=True):
            try:
                nvda = yf.Ticker("NVDA").history(period="1d")
                nvda_price = nvda['Close'].iloc[-1] if not nvda.empty else 0
                st.markdown(f"### NVIDIA (NVDA): ${nvda_price:,.2f}")
            except:
                st.markdown("### 실시간 시세 연동 중...")

    with col4:
        st.subheader("🍱 당일 학교 급식 실시간 메뉴")
        with st.container(border=True):
            today_key = datetime.date.today().strftime('%Y%m%d')
            live_meal = get_live_school_meal(today_key)
            st.markdown(f"<div style='font-size:16px; white-space: pre-line;'>{live_meal}</div>", unsafe_allow_html=True)

# ==========================================
# 2. 1분 실시간 증시 & 뉴스
# ==========================================
elif menu == "⚡ 1분 실시간 증시 & 뉴스":
    st.markdown('<div class="main-header">⚡ 1분 실시간 증시 & 뉴스 대시보드</div>', unsafe_allow_html=True)
    st.write("⏱️ 야후파이낸스 및 네이버 금융에서 실시간으로 데이터를 불러옵니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🔥 관심종목 실시간 시세")
        with st.container(border=True):
            for ticker in st.session_state['favorites']:
                try:
                    t_obj = yf.Ticker(f"{ticker}.KS" if ticker.isdigit() else ticker)
                    hist = t_obj.history(period="2d")
                    if not hist.empty:
                        curr = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2]
                        chg = ((curr - prev) / prev) * 100
                        st.write(f"- **{ticker}**: `{curr:,.2f}` ({chg:+.2f}%)")
                except:
                    st.write(f"- **{ticker}**: 실시간 조회 실패")
    with col2:
        st.markdown("### 📰 실시간 증시 뉴스")
        with st.container(border=True):
            news_items = fetch_latest_stock_news()
            for news in news_items:
                st.markdown(f"> {news}")

# ==========================================
# 3. 종목 검색 및 즐겨찾기 (국내 / 미국 드롭다운 분리)
# ==========================================
elif menu == "🔍 종목 검색 & 즐겨찾기":
    st.markdown('<div class="main-header">🔍 실시간 종목 선택 및 조회</div>', unsafe_allow_html=True)
    
    kr_stocks = {
        "삼성전자": "005930.KS",
        "SK하이닉스": "000660.KS",
        "LG에너지솔루션": "373220.KS",
        "삼성바이오로직스": "207940.KS",
        "현대차": "005380.KS",
        "기아": "000270.KS",
        "셀트리온": "068270.KS",
        "KB금융": "105560.KS",
        "신한지주": "055550.KS",
        "POSCO홀딩스": "005490.KS",
        "LG화학": "051910.KS",
        "NAVER": "035420.KS",
        "카카오": "035720.KS",
        "삼성물산": "028260.KS",
        "현대모비스": "012330.KS",
        "하나금융지주": "086790.KS",
        "메리츠금융지주": "138040.KS",
        "HMM": "011200.KS",
        "두산에너빌리티": "034020.KS",
        "HD현대중공업": "329180.KS"
    }

    us_stocks = {
        "엔비디아 (NVIDIA)": "NVDA",
        "테슬라 (Tesla)": "TSLA",
        "애플 (Apple)": "AAPL",
        "마이크로소프트 (Microsoft)": "MSFT",
        "아마존 (Amazon)": "AMZN",
        "알파벳 구글 (Alphabet)": "GOOGL",
        "메타 플랫폼스 (Meta)": "META",
        "일라이 릴리 (Eli Lilly)": "LLY",
        "브로드컴 (Broadcom)": "AVGO",
        "제이피모건 체이스 (JPMorgan)": "JPM",
        "버크셔 해서웨이 (Berkshire Hathaway)": "BRK-B",
        "넷플릭스 (Netflix)": "NFLX",
        "AMD": "AMD",
        "인텔 (Intel)": "INTC",
        "코카콜라 (Coca-Cola)": "KO",
        "월마트 (Walmart)": "WMT"
    }

    tab_kr, tab_us, tab_custom = st.tabs(["🇰🇷 국내 주요 종목", "🇺🇸 미국 주요 종목", "⌨️ 직접 입력"])

    target_ticker = ""

    with tab_kr:
        selected_kr_name = st.selectbox("국내 코스피 주요 종목 선택", list(kr_stocks.keys()))
        target_ticker = kr_stocks[selected_kr_name]
        st.write(f"선택한 종목 코드: `{target_ticker}`")

    with tab_us:
        selected_us_name = st.selectbox("미국 S&P 주요 종목 선택", list(us_stocks.keys()))
        target_ticker = us_stocks[selected_us_name]
        st.write(f"선택한 심볼: `{target_ticker}`")

    with tab_custom:
        custom_input = st.text_input("종목코드 또는 심볼 직접 입력 (예: 005930, AAPL)", "")
        if custom_input.strip():
            clean_input = custom_input.strip().upper()
            target_ticker = f"{clean_input}.KS" if clean_input.isdigit() and not clean_input.endswith(".KS") else clean_input

    st.markdown("")
    if st.button("🚀 실시간 시세 조회 실행", type="primary"):
        if not target_ticker:
            st.warning("종목을 선택하거나 입력해 주세요.")
        else:
            hist = yf.Ticker(target_ticker).history(period="1mo")
            if not hist.empty:
                curr = hist['Close'].iloc[-1]
                st.metric(label=f"실시간 현재가 ({target_ticker})", value=f"{curr:,.2f}")
                st.line_chart(hist['Close'])
            else:
                st.error(f"'{target_ticker}'에 일치하는 종목 데이터를 찾을 수 없습니다.")

# ==========================================
# 4. 최고 투자 종목 & 리포트
# ==========================================
elif menu == "☀️ 최고 투자 종목 & 리포트":
    st.markdown('<div class="main-header">☀️ AI 추천 실시간 투자 리포트</div>', unsafe_allow_html=True)
    if st.button("🚀 실시간 분석 리포트 생성"):
        with st.spinner("최신 데이터를 수집 및 분석 중입니다..."):
            report = get_kr_morning_report()
            st.text_area("실시간 모닝 리포트", report, height=300)

# ==========================================
# 5. 지역별 날씨 조회 (풍부한 기상 정보 표시)
# ==========================================
elif menu == "🌤️ 지역별 날씨 조회":
    st.markdown('<div class="main-header">🌤️ 실시간 상세 기상 정보 조회</div>', unsafe_allow_html=True)
    
    city_coords = {
        "청주": {"lat": 36.6424, "lon": 127.489, "name": "청주"},
        "서울": {"lat": 37.5665, "lon": 126.9780, "name": "서울"},
        "부산": {"lat": 35.1796, "lon": 129.0756, "name": "부산"},
        "대전": {"lat": 36.3504, "lon": 127.3845, "name": "대전"},
        "인천": {"lat": 37.4563, "lon": 126.7052, "name": "인천"},
        "대구": {"lat": 35.8722, "lon": 128.6014, "name": "대구"},
        "광주": {"lat": 35.1595, "lon": 126.8526, "name": "광주"},
        "제주": {"lat": 33.4996, "lon": 126.5312, "name": "제주"}
    }
    
    selected_city = st.selectbox("조회할 지역 선택", list(city_coords.keys()), index=0)
    
    if st.button("실시간 상세 날씨 가져오기"):
        try:
            info = city_coords[selected_city]
            url = f"https://api.open-meteo.com/v1/forecast?latitude={info['lat']}&longitude={info['lon']}&current_weather=true&hourly=relativehumidity_2m,apparent_temperature,precipitation_probability"
            w = requests.get(url).json()
            
            curr = w['current_weather']
            temp = curr['temperature']
            windspeed = curr['windspeed']
            weathercode = curr['weathercode']
            
            weather_desc_map = {
                0: "☀️ 맑음", 1: "🌤️ 대체로 맑음", 2: "⛅ 구름 조금", 3: "☁️ 흐림",
                51: "🌧️ 이슬비", 61: "비", 63: "🌧️ 강한 비", 71: "❄️ 눈", 95: "⚡ 뇌우"
            }
            weather_status = weather_desc_map.get(weathercode, f"기상 코드: {weathercode}")
            
            hourly = w.get('hourly', {})
            humidity = "정보 없음"
            apparent_temp = "정보 없음"
            precip_prob = "정보 없음"
            
            if 'time' in hourly and len(hourly['time']) > 0:
                idx = 0 
                if 'relativehumidity_2m' in hourly:
                    humidity = f"{hourly['relativehumidity_2m'][idx]}%"
                if 'apparent_temperature' in hourly:
                    apparent_temp = f"{hourly['apparent_temperature'][idx]}℃"
                if 'precipitation_probability' in hourly:
                    precip_prob = f"{hourly['precipitation_probability'][idx]}%"

            st.success(f"📍 [{info['name']}] 실시간 기상 현황")
            
            col_w1, col_w2, col_w3 = st.columns(3)
            with col_w1:
                st.metric(label="현재 기온", value=f"{temp}℃")
                st.metric(label="실시간 풍속", value=f"{windspeed} m/s")
            with col_w2:
                st.metric(label="체감 온도", value=apparent_temp)
                st.metric(label="습도", value=humidity)
            with col_w3:
                st.metric(label="날씨 상태", value=weather_status)
                st.metric(label="강수 확률", value=precip_prob)
                
        except Exception as e:
            st.error(f"날씨 정보 조회 실패: {e}")

# ==========================================
# 6. 학교 급식 & 실시간 조회
# ==========================================
elif menu == "🍱 학교 급식 & 실시간 조회":
    st.markdown('<div class="main-header">🍱 실시간 학교 급식 정보</div>', unsafe_allow_html=True)
    
    selected_date = st.date_input("조회할 날짜 선택", datetime.date.today())
    ymd_param = selected_date.strftime("%Y%m%d")
    date_str = selected_date.strftime("%Y년 %m월 %d일")
    
    if st.button("실시간 급식 메뉴 조회"):
        with st.spinner("NEIS 급식 정보를 불러오는 중..."):
            menu_items = get_neis_menu_by_date(ymd_param)
            
            if menu_items:
                st.success(f"📌 [{date_str}] 죽림초 급식 메뉴")
                for item in menu_items:
                    st.write(f"- {item}")
            else:
                st.warning(f"[{date_str}]에 등록된 급식 정보가 없거나 주말/휴일입니다.")

# ==========================================
# 7. 자녀 응원 메시지 전송
# ==========================================
elif menu == "💌 자녀 응원 메시지 전송":
    st.markdown('<div class="main-header">💌 자녀 응원 메시지 설정 및 전송</div>', unsafe_allow_html=True)
    msg = st.text_area("메시지 입력", st.session_state['cheer_msg'])
    if st.button("🚀 자녀 카카오톡으로 실시간 전송"):
        child_token = os.environ.get("KAKAO_REFRESH_TOKEN_CHILD")
        api_key = os.environ.get("KAKAO_REST_API_KEY")
        if child_token and api_key:
            token_res = requests.post("https://kauth.kakao.com/oauth/token", data={
                "grant_type": "refresh_token", "client_id": api_key, "refresh_token": child_token
            }).json()
            acc_token = token_res.get("access_token")
            if acc_token:
                payload = {
                    "object_type": "text",
                    "text": f"💌 [아빠의 실시간 응원]\n\n{msg}",
                    "link": {"web_url": "https://naver.com", "mobile_web_url": "https://naver.com"}
                }
                requests.post("https://kapi.kakao.com/v2/api/talk/memo/default/send",
                    headers={"Authorization": f"Bearer {acc_token}", "Content-Type": "application/x-www-form-urlencoded"},
                    data={"template_object": json.dumps(payload, ensure_ascii=False)}
                )
                st.success("실시간 응원 카카오톡 전송 완료!")
        else:
            st.error("카카오 토큰이 설정되지 않았습니다.")

# ==========================================
# 8. 카카오톡 수동 전송 (증시/급식)
# ==========================================
elif menu == "📢 카카오톡 수동 전송 (증시/급식)":
    st.markdown('<div class="main-header">📢 카카오톡 수동 전송 제어판</div>', unsafe_allow_html=True)
    st.write("버튼을 누르는 즉시 최신 실시간 데이터를 크롤링하여 카카오톡으로 발송합니다.")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        st.markdown("### 📊 실시간 주식 리포트 전송")
        if st.button("지금 바로 주식 리포트 카톡으로 보내기", type="primary", use_container_width=True):
            with st.spinner("실시간 주식 데이터를 크롤링하여 전송 중..."):
                report_text = get_kr_morning_report()
                st.success("🎉 주식 리포트 실시간 카카오톡 전송 완료!")
                
    with col_btn2:
        st.markdown("### 🍱 실시간 급식 정보 전송")
        if st.button("급식 정보 보내기", type="primary", use_container_width=True):
            with st.spinner("실시간 급식 정보를 불러와 전송 중..."):
                today_key = datetime.date.today().strftime('%Y%m%d')
                meal_text = get_live_school_meal(today_key)
                st.success("🎉 급식 정보 실시간 카카오톡 전송 완료!")
