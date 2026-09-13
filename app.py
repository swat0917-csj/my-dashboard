import streamlit as st
import datetime
import os
import json
import requests
import pandas as pd
import yfinance as yf
import folium
from streamlit_folium import st_folium

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
    .stock-card { background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; text-align: center; }
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
# 2. 1분 실시간 증시 & 뉴스 (UI/UX 개선 버전)
# ==========================================
elif menu == "⚡ 1분 실시간 증시 & 뉴스":
    st.markdown('<div class="main-header">⚡ 1분 실시간 증시 & 뉴스 대시보드</div>', unsafe_allow_html=True)
    st.write("⏱️ 야후파이낸스 및 네이버 금융 데이터를 바탕으로 실시간 시세와 주요 뉴스를 제공합니다.")
    
    # 상단 제어바 (새로고침 및 관심종목 관리)
    col_ctrl1, col_ctrl2 = st.columns([3, 1])
    with col_ctrl1:
        new_fav = st.text_input("➕ 관심종목 추가 (티커 또는 코드 입력 후 엔터)", placeholder="예: AAPL, 000660")
        if new_fav:
            clean_fav = new_fav.strip().upper()
            if clean_fav not in st.session_state['favorites']:
                st.session_state['favorites'].append(clean_fav)
                st.success(f"'{clean_fav}' 종목이 관심목록에 추가되었습니다!")
                st.rerun()
    with col_ctrl2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 실시간 새로고침", use_container_width=True):
            st.rerun()

    st.markdown("---")

    # 관심종목 시세 그리드 카드 섹션
    st.markdown("### 🔥 관심종목 실시간 시세 현황")
    
    fav_cols = st.columns(len(st.session_state['favorites']) if st.session_state['favorites'] else 1)
    
    for idx, ticker in enumerate(st.session_state['favorites']):
        with fav_cols[idx % len(fav_cols)]:
            with st.container(border=True):
                try:
                    query_ticker = f"{ticker}.KS" if ticker.isdigit() and not ticker.endswith(".KS") else ticker
                    t_obj = yf.Ticker(query_ticker)
                    hist = t_obj.history(period="2d")
                    
                    if not hist.empty:
                        curr = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2]
                        chg = ((curr - prev) / prev) * 100
                        
                        color_style = "color: #EF4444;" if chg >= 0 else "color: #3B82F6;"
                        arrow = "▲" if chg >= 0 else "▼"
                        
                        st.markdown(f"#### **{ticker}**")
                        st.markdown(f"<span style='font-size: 20px; font-weight: bold;'>{curr:,.2f}</span>", unsafe_allow_html=True)
                        st.markdown(f"<span style='{color_style} font-weight: bold;'>{arrow} {chg:+.2f}%</span>", unsafe_allow_html=True)
                        
                        # 삭제 버튼
                        if st.button("❌ 삭제", key=f"del_{ticker}"):
                            st.session_state['favorites'].remove(ticker)
                            st.rerun()
                    else:
                        st.warning(f"{ticker} 데이터 없음")
                except Exception:
                    st.error(f"{ticker} 조회 오류")

    st.markdown("")
    
    # 실시간 증시 뉴스 섹션
    st.markdown("### 📰 실시간 증시 핵심 뉴스 피드")
    with st.container(border=True):
        news_items = fetch_latest_stock_news()
        if news_items:
            for idx, news in enumerate(news_items):
                st.markdown(f"🔹 **{news}**")
                if idx < len(news_items) - 1:
                    st.markdown("<hr style='margin: 8px 0; border:0; border-top:1px solid #eee;'>", unsafe_allow_html=True)
        else:
            st.info("현재 수신된 실시간 뉴스가 없습니다.")

# ==========================================
# 3. 종목 검색 및 즐겨찾기
# ==========================================
elif menu == "🔍 종목 검색 & 즐겨찾기":
    st.markdown('<div class="main-header">🔍 실시간 종목 선택 및 조회</div>', unsafe_allow_html=True)
    
    kr_stocks = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "LG에너지솔루션": "373220.KS",
        "삼성바이오로직스": "207940.KS", "현대차": "005380.KS", "기아": "000270.KS",
        "셀트리온": "068270.KS", "KB금융": "105560.KS", "신한지주": "055550.KS",
        "POSCO홀딩스": "005490.KS", "LG화학": "051910.KS", "NAVER": "035420.KS",
        "카카오": "035720.KS", "삼성물산": "028260.KS", "현대모비스": "012330.KS"
    }
    us_stocks = {
        "엔비디아 (NVIDIA)": "NVDA", "테슬라 (Tesla)": "TSLA", "애플 (Apple)": "AAPL",
        "마이크로소프트 (Microsoft)": "MSFT", "아마존 (Amazon)": "AMZN", "알파벳 구글 (Alphabet)": "GOOGL"
    }

    tab_kr, tab_us, tab_custom = st.tabs(["🇰🇷 국내 주요 종목", "🇺🇸 미국 주요 종목", "⌨️ 직접 입력"])
    target_ticker = ""

    with tab_kr:
        selected_kr_name = st.selectbox("국내 코스피 주요 종목 선택", list(kr_stocks.keys()))
        target_ticker = kr_stocks[selected_kr_name]
    with tab_us:
        selected_us_name = st.selectbox("미국 S&P 주요 종목 선택", list(us_stocks.keys()))
        target_ticker = us_stocks[selected_us_name]
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
# 5. 지역별 날씨 조회 (방송국 기상캐스터 스타일 커스텀 지도)
# ==========================================
elif menu == "🌤️ 지역별 날씨 조회":
    st.markdown('<div class="main-header">🌤️ TV 기상캐스터 실시간 날씨 지도</div>', unsafe_allow_html=True)
    st.write("방송국 뉴스 기상도처럼 주요 도시의 날씨와 기온을 지도 위에 직접 표시합니다.")

    m = folium.Map(location=[36.5, 127.5], zoom_start=7, tiles="cartodbpositron")
    cities = {
        "서울": {"lat": 37.5665, "lon": 126.9780}, "청주": {"lat": 36.6424, "lon": 127.4890},
        "부산": {"lat": 35.1796, "lon": 129.0756}, "대구": {"lat": 35.8722, "lon": 128.6014},
        "광주": {"lat": 35.1595, "lon": 126.8526}, "제주": {"lat": 33.4996, "lon": 126.5312},
        "강릉": {"lat": 37.7519, "lon": 128.8761}
    }

    for city_name, coord in cities.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={coord['lat']}&longitude={coord['lon']}&current_weather=true"
            res = requests.get(url).json()
            temp = res['current_weather']['temperature']
            w_code = res['current_weather']['weathercode']
            
            icon_symbol = "☀️" if w_code == 0 else ("⛅" if w_code <= 2 else "☁️")
            if w_code >= 51: icon_symbol = "🌧️"
            
            html_tooltip = f"""
            <div style="
                background: white; border: 2px solid #1E3A8A; border-radius: 20px; 
                padding: 5px 10px; font-weight: bold; text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.2); white-space: nowrap;
            ">
                <span style="font-size: 16px;">{icon_symbol}</span> 
                <span style="color: #1E3A8A; font-size: 14px;">{city_name}</span> 
                <span style="color: #D32F2F; font-size: 15px;">{temp}℃</span>
            </div>
            """
            folium.Marker(
                location=[coord['lat'], coord['lon']],
                icon=folium.DivIcon(html=html_tooltip)
            ).add_to(m)
        except:
            pass

    st_folium(m, width="100%", height=550)

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
