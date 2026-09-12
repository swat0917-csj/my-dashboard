import streamlit as st
import datetime
import os
import json
import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup

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

# UI 스타일링 (간결화)
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

# ==========================================
# 실시간 학교 급식 연동 함수
# ==========================================
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
# 3. 종목 검색 및 즐겨찾기
# ==========================================
elif menu == "🔍 종목 검색 & 즐겨찾기":
    st.markdown('<div class="main-header">🔍 실시간 종목 검색 & 즐겨찾기</div>', unsafe_allow_html=True)
    query = st.text_input("종목 코드 또는 심볼 입력 (예: 005930, AAPL)", "005930")
    if st.button("실시간 검색 실행"):
        search_ticker = f"{query}.KS" if query.isdigit() else query.upper()
        hist = yf.Ticker(search_ticker).history(period="1mo")
        if not hist.empty:
            curr = hist['Close'].iloc[-1]
            st.metric(label=f"실시간 현재가 ({search_ticker})", value=f"{curr:,.2f}")
            st.line_chart(hist['Close'])
        else:
            st.error("일치하는 종목 데이터를 찾을 수 없습니다.")

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
# 5. 지역별 날씨 조회
# ==========================================
elif menu == "🌤️ 지역별 날씨 조회":
    st.markdown('<div class="main-header">🌤️ 실시간 기상 정보 조회</div>', unsafe_allow_html=True)
    region = st.text_input("도시 이름", "청주")
    if st.button("실시간 날씨 가져오기"):
        try:
            geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={region}&count=1&language=ko").json()
            if "results" in geo:
                lat, lon = geo['results'][0]['latitude'], geo['results'][0]['longitude']
                w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true").json()
                temp = w['current_weather']['temperature']
                st.metric(label=f"📍 {region} 실시간 기온", value=f"{temp}℃")
            else:
                st.error("해당 지역 정보를 찾을 수 없습니다.")
        except Exception as e:
            st.error(f"조회 실패: {e}")

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
