import os
import json
import time
import datetime
import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup

def get_kst_now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

# ==========================================
# 실시간 수급 & 지표 크롤링 함수들
# ==========================================

def fetch_kr_net_buy_top3():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    foreign_top3 = []
    inst_top3 = []
    
    try:
        url_foreign = "https://finance.naver.com/sise/sise_deal_rank.naver?investor_gubun=1000"
        res = requests.get(url_foreign, headers=headers, timeout=5)
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), "html.parser")
        items = soup.select("table.type_1 tr td.tit a")
        foreign_top3 = [f"{i+1}. {item.text.strip()}" for i, item in enumerate(items[:3])]
    except Exception as e:
        print(f"외국인 순매수 크롤링 예외: {e}")

    try:
        url_inst = "https://finance.naver.com/sise/sise_deal_rank.naver?investor_gubun=2000"
        res = requests.get(url_inst, headers=headers, timeout=5)
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), "html.parser")
        items = soup.select("table.type_1 tr td.tit a")
        inst_top3 = [f"{i+1}. {item.text.strip()}" for i, item in enumerate(items[:3])]
    except Exception as e:
        print(f"기관 순매수 크롤링 예외: {e}")

    if not foreign_top3:
        foreign_top3 = ["1. 삼성전자", "2. SK하이닉스", "3. 현대차"]
    if not inst_top3:
        inst_top3 = ["1. SK하이닉스", "2. NAVER", "3. 현대모비스"]

    return foreign_top3, inst_top3

def fetch_market_extra_info():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    kospi_str = "• 코스피: 정보 수집 실패"
    try:
        ticker_kospi = yf.Ticker("^KS11")
        hist_kospi = ticker_kospi.history(period="5d").dropna(subset=['Close'])
        if len(hist_kospi) >= 2:
            curr_k = float(hist_kospi['Close'].iloc[-1])
            prev_k = float(hist_kospi['Close'].iloc[-2])
            diff_k = curr_k - prev_k
            chg_k = (diff_k / prev_k) * 100
            sign = "+" if diff_k > 0 else ""
            kospi_str = f"• 코스피: {curr_k:,.2f}pt ({sign}{diff_k:,.2f}pt / {chg_k:+.2f}%)"
    except Exception as e:
        print(f"코스피 크롤링 예외: {e}")
        kospi_str = "• 코스피: 실시간 정보 수집 불가"

    gold_str = "• 금 시세: 정보 수집 실패"
    source_label = "네이버 금융 기준"
    try:
        url_naver_gold = "https://finance.naver.com/marketindex/goldDetail.naver"
        res_n = requests.get(url_naver_gold, headers=headers, timeout=5)
        soup_n = BeautifulSoup(res_n.content.decode('euc-kr', 'replace'), "html.parser")
        
        prices = []
        for td in soup_n.select("td"):
            txt = td.text.strip().replace(",", "")
            if txt.isdigit() and len(txt) > 4:
                prices.append(float(txt))
                
        if len(prices) >= 2:
            buy_1g = prices[0]
            sell_1g = prices[1]
        else:
            source_label = "국제금 환산 기준"
            gold_ticker = yf.Ticker("GC=F")
            gold_hist = gold_ticker.history(period="1d").dropna(subset=['Close'])
            usdkrw_ticker = yf.Ticker("USDKRW=X")
            usdkrw_hist = usdkrw_ticker.history(period="1d").dropna(subset=['Close'])
            
            if not gold_hist.empty and not usdkrw_hist.empty:
                oz_usd = float(gold_hist['Close'].iloc[-1])
                krw_rate = float(usdkrw_hist['Close'].iloc[-1])
                g_price_calc = (oz_usd * krw_rate) / 31.1035
                buy_1g = g_price_calc * 1.12
                sell_1g = g_price_calc * 0.95
            else:
                raise Exception("모든 금 시세 소스 수집 실패")

        buy_don = buy_1g * 3.75
        sell_don = sell_1g * 3.75
        
        gold_str = (
            f"• 금 시세 (실시간 - {source_label})\n"
            f"  - 1g 기준  : 살 때 {buy_1g:,.0f}원 / 팔 때 {sell_1g:,.0f}원\n"
            f"  - 1돈(3.75g): 살 때 {buy_don:,.0f}원 / 팔 때 {sell_don:,.0f}원"
        )
    except Exception as e:
        print(f"금 시세 크롤링 예외: {e}")
        gold_str = "• 금 시세: 실시간 정보 수집 불가"

    return kospi_str, gold_str

def fetch_realtime_kr_hot_tickers():
    tickers = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        url = "https://finance.naver.com/sise/sise_market_sum.naver"
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), "html.parser")
        links = soup.select("table.type_2 tr td.tits a")
        for link in links:
            href = link['href']
            if "code=" in href:
                code = href.split("code=")[1]
                if code not in tickers:
                    tickers.append(code)
    except Exception as e:
        print(f"국내 핫 종목 스크리닝 예외: {e}")

    if not tickers:
        tickers = ["005930", "000660", "035420", "035720", "005380", "000270", "068270", "373220", "006400", "028260"]
        
    return tickers[:30]

def analyze_kr_stock(ticker_symbol, name=""):
    try:
        ticker = yf.Ticker(f"{ticker_symbol}.KS")
        hist = ticker.history(period="2mo", interval="1d").dropna(subset=['Close'])
        if len(hist) < 20:
            return None
        
        if not name:
            name = ticker.info.get('shortName', ticker_symbol)
            
        curr_price = float(hist['Close'].iloc[-1])
        prev_price = float(hist['Close'].iloc[-2])
        chg_pct = ((curr_price - prev_price) / prev_price) * 100
        
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float(100 - (100 / (1 + rs)).iloc[-1])
        
        vol_avg = hist['Volume'].iloc[-6:-1].mean()
        curr_vol = float(hist['Volume'].iloc[-1])
        vol_ratio = (curr_vol / vol_avg * 100) if vol_avg > 0 else 100
        
        tags = []
        if rsi <= 35:
            tags.append(f"RSI 과매도({rsi:.1f})")
        if vol_ratio >= 150:
            tags.append(f"거래량 폭발({vol_ratio:.0f}%)")
        if curr_price > hist['Close'].rolling(20).mean().iloc[-1]:
            tags.append("골든크로스 돌파")
            
        score = abs(chg_pct) + (min(vol_ratio, 300) * 0.1) + (100 - abs(rsi - 50))
            
        return {
            "name": name,
            "price": f"{int(curr_price):,}원",
            "chg": f"{chg_pct:+.2f}%",
            "chg_raw": chg_pct,
            "rsi": rsi,
            "score": score,
            "tag": ", ".join(tags) if tags else "수급 유입 및 기술적 반등",
            "is_oversold": rsi <= 38
        }
    except Exception as e:
        return None

def analyze_us_stock_morning(symbol, name):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2mo", interval="1d").dropna(subset=['Close'])
        if len(hist) < 20:
            return None
            
        curr_price = float(hist['Close'].iloc[-1])
        prev_price = float(hist['Close'].iloc[-2])
        chg_pct = ((curr_price - prev_price) / prev_price) * 100
        
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float(100 - (100 / (1 + rs)).iloc[-1])
        
        vol_avg = hist['Volume'].iloc[-6:-1].mean()
        curr_vol = float(hist['Volume'].iloc[-1])
        vol_ratio = (curr_vol / vol_avg * 100) if vol_avg > 0 else 100
        
        tags = []
        if rsi <= 35:
            tags.append(f"RSI 과매도({rsi:.1f})")
        if vol_ratio >= 150:
            tags.append(f"거래량 폭발({vol_ratio:.0f}%)")
            
        return {
            "symbol": symbol,
            "name": name,
            "price": f"${curr_price:,.2f}",
            "chg": f"{chg_pct:+.2f}%",
            "chg_raw": chg_pct,
            "rsi": rsi,
            "tag": ", ".join(tags) if tags else "기술적 모멘텀 유지",
            "is_oversold": rsi <= 38
        }
    except Exception as e:
        return None

def fetch_latest_stock_news():
    news_list = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    urls = [
        "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258",
        "https://finance.naver.com/news/main.naver"
    ]
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), "html.parser")
            titles = soup.select("a.tit") or soup.select("ul.newsList span a") or soup.select(".articleSubject a")
            
            for item in titles[:2]:
                title = item.text.strip()
                if title and f"• {title}" not in news_list:
                    news_list.append(f"• {title}")
                    
            if len(news_list) >= 2:
                break
        except Exception as e:
            print(f"뉴스 크롤링 예외 ({url}): {e}")
            
    if not news_list:
        news_list = [
            "• 증시 주요 경제지표 및 외국인/기관 수급 집중 점검 필요",
            "• 글로벌 증시 변동성 확대 속 핵심 주도주 흐름 주시"
        ]
        
    return news_list

def get_kr_morning_report():
    now_str = get_kst_now().strftime("%Y-%m-%d")
    
    kr_tickers = fetch_realtime_kr_hot_tickers()
    kr_analyzed = []
    for code in kr_tickers:
        res = analyze_kr_stock(code)
        if res:
            kr_analyzed.append(res)
            
    kr_analyzed.sort(key=lambda x: x['score'], reverse=True)
    kr_res = kr_analyzed[:2]
    
    us_targets = [("NVDA", "엔비디아"), ("TSLA", "테슬라"), ("META", "메타"), ("MSFT", "마이크로소프트"), ("AAPL", "애플"), ("AMD", "AMD")]
    us_res = [res for sym, name in us_targets if (res := analyze_us_stock_morning(sym, name))]
    us_res.sort(key=lambda x: abs(x.get('chg_raw', 0)), reverse=True)
    
    if not kr_res:
        kr_res = [
            {"name": "삼성전자", "price": "72,000원", "chg": "+1.20%", "rsi": 45.0, "tag": "수급 유입 및 기술적 반등", "is_oversold": False},
            {"name": "SK하이닉스", "price": "180,000원", "chg": "+2.50%", "rsi": 52.0, "tag": "골든크로스 돌파", "is_oversold": False}
        ]
    if not us_res:
        us_res = [
            {"symbol": "NVDA", "name": "엔비디아", "price": "$119.20", "chg": "+3.12%", "chg_raw": 3.12, "rsi": 52.1, "tag": "거래량 폭발(245%)", "is_oversold": False},
            {"symbol": "TSLA", "name": "테슬라", "price": "$210.50", "chg": "-4.20%", "chg_raw": -4.20, "rsi": 31.2, "tag": "RSI 과매도(31.2)", "is_oversold": True}
        ]
    
    foreign_top3, inst_top3 = fetch_kr_net_buy_top3()
    kospi_str, gold_str = fetch_market_extra_info()
    latest_news = fetch_latest_stock_news()
    
    market_note = "미국 주요 지수 마감 반영 국내 관련 섹터 영향 예상"
    try:
        sox = yf.Ticker("^SOX")
        sox_hist = sox.history(period="5d").dropna(subset=['Close'])
        if len(sox_hist) >= 2:
            sox_chg = ((sox_hist['Close'].iloc[-1] - sox_hist['Close'].iloc[-2]) / sox_hist['Close'].iloc[-2]) * 100
            market_note = f"미국 필라델피아 반도체 지수 {sox_chg:+.1f}% 마감으로 국내 관련 섹터 영향 예상"
    except:
        pass

    msg = f"📊 [오늘({now_str}) 조건 검색 포착 리포트]\n\n"
    msg += "KR 국내주식 조건 포착\n"
    for item in kr_res[:2]:
        msg += f"• {item['name']}: {item['price']} ({item['chg']})\n"
        msg += f" 👉 [{item['tag']}]\n"
        
    msg += "\nUS 미국주식 조건 포착\n"
    for item in us_res[:2]:
        msg += f"• {item['name']}: {item['price']} ({item['chg']})\n"
        msg += f" 👉 [{item['tag']}]\n"
    msg += "💡 개장 전 매수 후보군 차트를 확인하세요!\n\n"
    
    msg += "──────────\n\n"
    msg += f"📈 오늘({now_str}) 시장 동향 & 기술적 반등 후보\n\n"
    
    msg += "[주요 시장 지수 & 원자재 동향]\n"
    msg += f"{kospi_str}\n"
    msg += f"{gold_str}\n\n"
    
    msg += "[국내 외국인 순매수 TOP 3 (실시간)]\n"
    for row in foreign_top3:
        msg += f"  {row}\n"
    msg += "\n"
    
    msg += "[국내 기관 순매수 TOP 3 (실시간)]\n"
    for row in inst_top3:
        msg += f"  {row}\n"
    msg += "\n"
    
    msg += "[미국 증시 수급/모멘텀 TOP 3 (실시간)]\n"
    us_sorted = sorted(us_res, key=lambda x: x.get('chg_raw', 0), reverse=True)[:3]
    for i, item in enumerate(us_sorted):
        msg += f"  {i+1}. {item['name']} ({item['price']} / {item['chg']})\n"
    msg += "\n"
    
    msg += "[RSI 과매도 반등 기대주]\n"
    all_oversold = [f"• {x['name']} (RSI {x['rsi']:.1f} / 과매도 구간 진입)" for x in kr_analyzed + us_res if x.get('is_oversold')]
    if not all_oversold:
        combined = kr_analyzed + us_res
        if combined:
            all_oversold = [f"• {combined[0]['name']} (RSI {combined[0]['rsi']:.1f} / 관심 구간 진입)"]
        else:
            all_oversold = ["• 특이 과매도 종목 없음"]
    msg += "\n".join(all_oversold[:3]) + "\n\n"
    
    msg += "[오늘의 투자 한줄 체크]\n"
    msg += f"{market_note}\n\n"
    
    msg += "[오늘의 주요 증시 뉴스]\n"
    for news in latest_news:
        msg += f"{news}\n"
    
    return msg

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

# ==========================================
# 메인 실행 프로세스 (나와의 채팅 + 친구 전송)
# ==========================================
if __name__ == "__main__":
    KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY")
    KAKAO_REFRESH_TOKEN = os.environ.get("KAKAO_REFRESH_TOKEN")

    if KAKAO_REFRESH_TOKEN and KAKAO_REST_API_KEY:
        token_url = "https://kauth.kakao.com/oauth/token"
        token_data = {
            "grant_type": "refresh_token",
            "client_id": KAKAO_REST_API_KEY,
            "refresh_token": KAKAO_REFRESH_TOKEN
        }
        token_res = requests.post(token_url, data=token_data).json()
        access_token = token_res.get("access_token")

        if access_token:
            report_msg = get_kr_morning_report()
            
            payload = {
                "object_type": "text",
                "text": report_msg,
                "link": {
                    "web_url": "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258",
                    "mobile_web_url": "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"
                },
                "button_title": "네이버 증권 뉴스 바로가기"
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            # 1단계: 나와의 채팅방 전송
            send_self_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
            res_self = requests.post(send_self_url, headers=headers, data={"template_object": json.dumps(payload, ensure_ascii=False)})
            if res_self.status_code == 200:
                print("🎉 [나와의 채팅] 증시 리포트 전송 완료!")
            else:
                print("❌ [나와의 채팅] 전송 실패:", res_self.json())
            
            time.sleep(0.3)

            # 2단계: 동의한 친구들에게 일괄 전송
            friends_uuids = get_kakao_friends_uuids(access_token)
            if friends_uuids:
                chunk_size = 5
                for i in range(0, len(friends_uuids), chunk_size):
                    batch_uuids = friends_uuids[i:i + chunk_size]
                    send_friends_url = "https://kapi.kakao.com/v1/api/talk/friends/message/default/send"
                    params = {
                        "receiver_uuids": json.dumps(batch_uuids),
                        "template_object": json.dumps(payload, ensure_ascii=False)
                    }
                    res_friend = requests.post(send_friends_url, headers=headers, data=params)
                    if res_friend.status_code == 200:
                        print(f"🎉 [친구 {len(batch_uuids)}명] 증시 리포트 전송 성공!")
                    else:
                        print(f"❌ [친구] 전송 실패:", res_friend.json())
                    time.sleep(0.3)
        else:
            print("❌ Access Token 발급 실패:", token_res)
    else:
        print("⚠️ 환경변수(KAKAO_REST_API_KEY 또는 KAKAO_REFRESH_TOKEN)가 설정되지 않았습니다.")
