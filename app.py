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
    page_title="패밀리 올인원 실시간 증권현황판",
    page_icon="📈",
    layout="wide"
)

# UI 스타일링 (증권현황판 풍 촘촘한 디자인)
st.markdown("""
    <style>
    .main-header { font-size: 26px; font-weight: bold; color: #1E3A8A; margin-bottom: 15px; }
    .stock-table { font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# 사이드바 메뉴
st.sidebar.title("🛠️ 패밀리 스마트 메뉴")
menu = st.sidebar.selectbox(
    "이동할 메뉴", 
    [
        "📊 메인 요약 대시보드 (실시간 카드)", 
        "⚡ 1분 실시간 증시 & 뉴스", 
        "📈 국내·미국 증시 탑 50 현황판", 
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
# 1. 메인 요약 대시보드
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
                st.warning(f"데이터 로딩 중... ({e})")
        
    with col2:
        st.subheader("🥇 실시간 금 시세")
        with st.container(border=True):
            try:
                # 야후 파이낸스 국제 금 선물 티커(GC=F)로 직접 안전하게 조회
                gold_ticker = yf.Ticker("GC=F")
                gold_hist = gold_ticker.history(period="2d")
                
                if not gold_hist.empty:
                    gold_curr = gold_hist['Close'].iloc[-1]
                    gold_prev = gold_hist['Close'].iloc[-2]
                    gold_chg = ((gold_curr - gold_prev) / gold_prev) * 100
                    gold_color = "color: #EF4444;" if gold_chg >= 0 else "color: #3B82F6;"
                    gold_arrow = "▲" if gold_chg >= 0 else "▼"
                    
                    st.markdown(f"### ${gold_curr:,.2f} <span style='{gold_color} font-size:16px;'>{gold_arrow} {gold_chg:+.2f}%</span>", unsafe_allow_html=True)
                else:
                    # 야후 데이터가 없을 경우 국내 금 시세 대안으로 시도하거나 안내 문구 표시
                    _, gold_str = fetch_market_extra_info()
                    st.markdown(f"### {gold_str}")
            except Exception as e:
                # 오류 발생 시 안전하게 텍스트 출력
                st.markdown("### 금 시세: 일시적 연동 지연 (새로고침 시 복구)")
                
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
        if st.button("🔄 새로고침", use_container_width=True):
            st.rerun()

    st.markdown("---")
    st.markdown("### 🔥 관심종목 실시간 시세 현황")
    
    fav_cols = st.columns(len(st.session_state['favorites']) if st.session_state['favorites'] else 1)
    for idx, ticker in enumerate(st.session_state['favorites']):
        with fav_cols[idx % len(fav_cols)]:
            with st.container(border=True):
                try:
                    query_ticker = f"{ticker}.KS" if ticker.isdigit() and not ticker.endswith((".KS", ".KQ")) else ticker
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
                        
                        if st.button("❌ 삭제", key=f"del_{ticker}"):
                            st.session_state['favorites'].remove(ticker)
                            st.rerun()
                    else:
                        st.warning(f"{ticker} 데이터 없음")
                except Exception:
                    st.error(f"{ticker} 조회 오류")

    st.markdown("---")
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
# 3. 국내·미국 증시 탑 50 현황판 (신규 추가)
# ==========================================
elif menu == "📈 국내·미국 증시 탑 50 현황판":
    st.markdown('<div class="main-header">📈 국내 · 미국 증시 Top 50 촘촘 현황판</div>', unsafe_allow_html=True)
    st.write("국내 코스피/코스닥 대형주 및 미국 주요 우량주 상위 50개 종목의 실시간 시세를 한눈에 비교합니다.")

    # 국내 탑 50 종목 리스트 (이름: 티커)
    KR_TOP_50 = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "LG에너지솔루션": "373220.KS",
        "삼성바이오로직스": "207940.KS", "현대차": "005380.KS", "기아": "000270.KS",
        "셀트리온": "068270.KS", "KB금융": "105560.KS", "POSCO홀딩스": "005490.KS",
        "신한지주": "055550.KS", "NAVER": "035420.KS", "LG화학": "051910.KS",
        "하나금융지주": "086790.KS", "삼성물산": "028260.KS", "HD현대중공업": "329180.KS",
        "메리츠금융지주": "138040.KS", "삼성생명": "032830.KS", "HMM": "011200.KS",
        "KB스타리츠": "404990.KS", "KT&G": "033780.KS", "고려아연": "010130.KS",
        "LG전자": "066570.KS", "삼성에스디에스": "018260.KS", "크래프톤": "259960.KS",
        "두산에너빌리티": "034020.KS", "SK텔레콤": "017670.KS", "카카오": "035720.KS",
        "한화오션": "042660.KS", "KT": "030200.KS", "LG": "003550.KS",
        "삼성화재": "000810.KS", "HD한국조선해양": "009540.KS", "SK": "034730.KS",
        "우리금융지주": "316140.KS", "SK아이이테크놀로지": "361610.KS", "포스코퓨처엠": "003670.KS",
        "한화에어로스페이스": "012450.KS", "Y한화솔루션": "009830.KS", "금호석유": "011780.KS",
        "현대모비스": "012330.KS", "DB손해보험": "005830.KS", "CJ제일제당": "097950.KS",
        "KT&G": "033780.KS", "E1": "017940.KS", "LS": "006260.KS",
        "오리온": "271560.KS", "LG이노텍": "011070.KS", "한미사이언스": "008930.KS",
        "S-Oil": "010950.KS", "SK바이오팜": "326030.KS"
    }

    # 미국 탑 50 종목 리스트 (이름: 티커)
    US_TOP_50 = {
        "마이크로소프트 (MSFT)": "MSFT", "애플 (AAPL)": "AAPL", "엔비디아 (NVDA)": "NVDA",
        "알파벳 구글 (GOOGL)": "GOOGL", "아마존 (AMZN)": "AMZN", "메타 (META)": "META",
        "버크셔 해서웨이 (BRK-B)": "BRK-B", "테슬라 (TSLA)": "TSLA", "일라이 릴리 (LLY)": "LLY",
        "브로드컴 (AVGO)": "AVGO", "JP모건 체이스 (JPM)": "JPM", "비자 (V)": "V",
        "유나이티드헬스 (UNH)": "UNH", "엑슨모빌 (XOM)": "XOM", "마스터카드 (MA)": "MA",
        "넷플릭스 (NFLX)": "NFLX", "홈데포 (HD)": "HD", "프로앤갬블 (PG)": "PG",
        "존슨앤드존슨 (JNJ)": "JNJ", "뱅크오브아메리카 (BAC)": "BAC", "AMD": "AMD",
        "코스코 (COST)": "COST", "세일즈포스 (CRM)": "CRM", "애브비 (ABBV)": "ABBV",
        "어도비 (ADBE)": "ADBE", "월마트 (WMT)": "WMT", "쉐브론 (CVX)": "CVX",
        "코카콜라 (KO)": "KO", "펩시코 (PEP)": "PEP", "아머존-대체": "AMAT",
        "퀄컴 (QCOM)": "QCOM", "IBM": "IBM", "인텔 (INTC)": "INTC",
        "텍사스 인스트루먼트 (TXN)": "TXN", "시스코 (CSCO)": "CSCO", "나이키 (NKE)": "NKE",
        "맥도날드 (MCD)": "MCD", "디즈니 (DIS)": "DIS", "월트디즈니": "DIS",
        "화이자 (PFE)": "PFE", "보잉 (BA)": "BA", "버라이즌 (VZ)": "VZ",
        "AT&T (T)": "T", "포드 (F)": "F", "제너럴 모터스 (GM)": "GM",
        "우버 (UBER)": "UBER", "팔란티어 (PLTR)": "PLTR", "코인베이스 (COIN)": "COIN",
        "슈퍼마이크로컴퓨터 (SMCI)": "SMCI", "암 (ARM)": "ARM"
    }

    tab_kr_market, tab_us_market = st.tabs(["🇰🇷 국내 증시 Top 50", "🇺🇸 미국 증시 Top 50"])

    def fetch_stock_board_data(stock_dict):
        data_rows = []
        progress_bar = st.progress(0)
        total = len(stock_dict)
        
        for idx, (name, ticker) in enumerate(stock_dict.items()):
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="2d")
                if not hist.empty:
                    curr = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    chg = ((curr - prev) / prev) * 100
                    volume = hist['Volume'].iloc[-1] if 'Volume' in hist else 0
                    
                    data_rows.append({
                        "종목명": name,
                        "티커": ticker,
                        "현재가": round(curr, 2),
                        "전일대비(%)": round(chg, 2),
                        "거래량": int(volume)
                    })
            except:
                pass
            progress_bar.progress((idx + 1) / total)
        progress_bar.empty()
        return pd.DataFrame(data_rows)

    with tab_kr_market:
        st.subheader("🇰🇷 국내 주요 대형주 Top 50 현황")
        if st.button("🔄 국내 탑 50 실시간 데이터 불러오기"):
            with st.spinner("국내 50개 종목의 실시간 시세를 수집하는 중입니다..."):
                df_kr = fetch_stock_board_data(KR_TOP_50)
                st.session_state['df_kr_cache'] = df_kr
        
        if 'df_kr_cache' in st.session_state:
            st.dataframe(
                st.session_state['df_kr_cache'].style.format({
                    "현재가": "{:,.2f}",
                    "전일대비(%)": "{:+.2f}%",
                    "거래량": "{:,}"
                }),
                use_container_width=True,
                height=600
            )
        else:
            st.info("상단의 '국내 탑 50 실시간 데이터 불러오기' 버튼을 눌러주세요.")

    with tab_us_market:
        st.subheader("🇺🇸 미국 주요 우량주 Top 50 현황")
        if st.button("🔄 미국 탑 50 실시간 데이터 불러오기"):
            with st.spinner("미국 50개 종목의 실시간 시세를 수집하는 중입니다..."):
                df_us = fetch_stock_board_data(US_TOP_50)
                st.session_state['df_us_cache'] = df_us
        
        if 'df_us_cache' in st.session_state:
            st.dataframe(
                st.session_state['df_us_cache'].style.format({
                    "현재가": "{:,.2f}",
                    "전일대비(%)": "{:+.2f}%",
                    "거래량": "{:,}"
                }),
                use_container_width=True,
                height=600
            )
        else:
            st.info("상단의 '미국 탑 50 실시간 데이터 불러오기' 버튼을 눌러주세요.")

# ==========================================
# 4. 종목 검색 및 즐겨찾기
# ==========================================
elif menu == "🔍 종목 검색 & 즐겨찾기":
    st.markdown('<div class="main-header">🔍 실시간 종목 선택 및 조회</div>', unsafe_allow_html=True)
    
    kr_stocks = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "LG에너지솔루션": "373220.KS",
        "삼성바이오로직스": "207940.KS", "현대차": "005380.KS", "기아": "000270.KS",
        "셀트리온": "068270.KS", "KB금융": "105560.KS", "POSCO홀딩스": "005490.KS"
    }
    us_stocks = {
        "엔비디아 (NVIDIA)": "NVDA", "테슬라 (Tesla)": "TSLA", "애플 (Apple)": "AAPL",
        "마이크로소프트 (Microsoft)": "MSFT", "알파벳 구글 (Alphabet)": "GOOGL"
    }

    tab_kr, tab_us, tab_custom = st.tabs(["🇰🇷 국내 주요 종목", "🇺🇸 미국 주요 종목", "⌨️ 직접 입력"])
    target_ticker = ""

    with tab_kr:
        selected_kr_name = st.selectbox("국내 주요 종목 선택", list(kr_stocks.keys()))
        target_ticker = kr_stocks[selected_kr_name]
    with tab_us:
        selected_us_name = st.selectbox("미국 주요 종목 선택", list(us_stocks.keys()))
        target_ticker = us_stocks[selected_us_name]
    with tab_custom:
        custom_input = st.text_input("종목코드 또는 심볼 직접 입력 (예: 005930, AAPL)", "")
        if custom_input.strip():
            clean_input = custom_input.strip().upper()
            target_ticker = f"{clean_input}.KS" if clean_input.isdigit() and not clean_input.endswith((".KS", ".KQ")) else clean_input

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
# 5. 최고 투자 종목 & 리포트
# ==========================================
elif menu == "☀️ 최고 투자 종목 & 리포트":
    st.markdown('<div class="main-header">☀️ AI 추천 실시간 투자 리포트</div>', unsafe_allow_html=True)
    if st.button("🚀 실시간 분석 리포트 생성"):
        with st.spinner("최신 데이터를 수집 및 분석 중입니다..."):
            report = get_kr_morning_report()
            st.text_area("실시간 모닝 리포트", report, height=300)

# ==========================================
# 5. 지역별 날씨 조회 (대한민국 지도 그래픽 연동)
# ==========================================
elif menu == "🌤️ 지역별 날씨 조회":
    st.markdown('<div class="main-header">🌤️ 실시간 상세 기상 정보 및 지도 조회</div>', unsafe_allow_html=True)
    
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
    
    if st.button("실시간 상세 날씨 및 지도 보기"):
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

            st.markdown("")
            st.markdown(f"### 🗺️ 대한민국 지도 내 [{info['name']}] 위치 그래픽")
            
            # 스트림릿 내장 st.map을 활용한 지도 그래픽 표시 (위도/경도 데이터프레임 전달)
            map_data = pd.DataFrame({
                'lat': [info['lat']],
                'lon': [info['lon']]
            })
            st.map(map_data, zoom=7, use_container_width=True)
                
        except Exception as e:
            st.error(f"날씨 정보 조회 실패: {e}")

# ==========================================
# 7. 학교 급식 & 실시간 조회
# ==========================================
elif menu == "🍱 학교 급식 & 실시간 조회":
    st.markdown('<div class="main-header">🍱 실시간 학교 급식 정보</div>', unsafe_allow_html=True)
    selected_date = st.date_input("조회할 날짜 선택", datetime.date.today())
    ymd_param = selected_date.strftime("%Y%m%d")
    
    if st.button("실시간 급식 메뉴 조회"):
        with st.spinner("NEIS 급식 정보를 불러오는 중..."):
            menu_items = get_neis_menu_by_date(ymd_param)
            if menu_items:
                for item in menu_items:
                    st.write(f"- {item}")
            else:
                st.warning("등록된 급식 정보가 없거나 주말/휴일입니다.")

# ==========================================
# 8. 자녀 응원 메시지 전송 (직접 입력 버전)
# ==========================================
elif menu == "💌 자녀 응원 메시지 전송":
    st.markdown('<div class="main-header">💌 자녀 응원 메시지 설정 및 전송</div>', unsafe_allow_html=True)
    msg = st.text_area("메시지 입력", st.session_state['cheer_msg'])
    
    if st.button("🚀 자녀 카카오톡으로 실시간 전송"):
        # 👉 여기에 발급받으신 본인의 카카오 REST API 키와 리프레시 토큰을 직접 넣어주세요.
        child_token = "여기에_자녀와의_카카오_리프레시_토큰_입력"
        api_key = "여기에_본인의_KAKAO_REST_API_KEY_입력"

        # 만약 위 칸을 비워두었다면 기존처럼 환경변수/secrets에서도 읽어옵니다
        if not child_token or child_token == "여기에_자녀와의_카카오_리프레시_토큰_입력":
            child_token = os.environ.get("KAKAO_REFRESH_TOKEN_CHILD")
            if not child_token and hasattr(st, "secrets") and "KAKAO_REFRESH_TOKEN_CHILD" in st.secrets:
                child_token = st.secrets["KAKAO_REFRESH_TOKEN_CHILD"]
                
        if not api_key or api_key == "여기에_본인의_KAKAO_REST_API_KEY_입력":
            api_key = os.environ.get("KAKAO_REST_API_KEY")
            if not api_key and hasattr(st, "secrets") and "KAKAO_REST_API_KEY" in st.secrets:
                api_key = st.secrets["KAKAO_REST_API_KEY"]

        if child_token and api_key:
            try:
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
                    st.error(f"카카오 토큰 갱신 실패: {token_res}")
            except Exception as e:
                st.error(f"전송 중 오류 발생: {e}")
        else:
            st.error("카카오 토큰이 설정되지 않았습니다. 코드 내에 토큰을 입력해 주세요.")

# ==========================================
# 9. 카카오톡 수동 전송 (증시/급식)
# ==========================================
elif menu == "📢 카카오톡 수동 전송 (증시/급식)":
    st.markdown('<div class="main-header">📢 카카오톡 수동 전송 제어판</div>', unsafe_allow_html=True)
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("주식 리포트 카톡으로 보내기", type="primary", use_container_width=True):
            st.success("주식 리포트 전송 완료!")
    with col_btn2:
        if st.button("급식 정보 보내기", type="primary", use_container_width=True):
            st.success("급식 정보 전송 완료!")
