#!/usr/bin/env python3
"""
CANSLIM 시장 스크리너
코스피, 코스닥, 나스닥, S&P 500 전체 주식을 매일 스크리닝하여 CANSLIM 기준으로 분석
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from canslim_analyzer import CANSLIMAnalyzer
import os
import pytz

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketScreener:
    def __init__(self):
        self.analyzer = CANSLIMAnalyzer()
        self.results = []
    
    def analyze_stock(self, symbol):
        """
        개별 주식의 CANSLIM 분석 및 스코어 계산
        """
        try:
            # 주도주 기준 분석
            leadership_result = self.analyzer.analyze_leadership_criteria(symbol)
            
            if "error" in leadership_result:
                return None
            
            # CANSLIM 개별 점수 계산
            criteria = leadership_result.get("criteria", {})
            canslim_scores = self._calculate_canslim_scores(criteria)
            
            # 전체 점수 계산: 7개 기준의 합계 (0-7점)
            total_canslim_score = sum(canslim_scores.values())
            # 백분율로 변환 (0-100%)
            overall_score = (total_canslim_score / 7.0) * 100
            
            result = {
                "symbol": symbol,
                "overall_score": round(overall_score, 1),
                "canslim_total": round(total_canslim_score, 1),  # 실제 CANSLIM 점수 (0-7)
                "canslim_scores": canslim_scores,
                "analysis_date": datetime.now().strftime('%Y-%m-%d'),
                "leadership_data": leadership_result
            }
            
            return result
            
        except Exception as e:
            logger.error(f"{symbol} 분석 실패: {str(e)}")
            return None
    
    def _calculate_canslim_scores(self, criteria):
        """
        CANSLIM 개별 기준별 점수 계산 (각 1점 만점, 총 7점)
        William O'Neil의 원래 CANSLIM 방식: Pass(1점) or Fail(0점)
        """
        scores = {}
        
        # C - Current Quarterly Earnings (52주 신고가로 대체)
        if "52w_high" in criteria:
            high_data = criteria["52w_high"]
            # 신고가 95% 이상이면 1점, 아니면 0점
            scores["C"] = 1.0 if high_data.get("is_near_high", False) else 0.0
        else:
            scores["C"] = 0.0
        
        # A - Annual Earnings Growth (시장 대비 성과로 대체)
        if "market_performance" in criteria:
            market_perf = criteria["market_performance"]
            rel_strength_6m = market_perf.get("relative_strength_6m", -100)
            # 6개월 상대강도가 양수이면 1점 (시장 대비 우수)
            scores["A"] = 1.0 if rel_strength_6m > 0 else 0.0
        else:
            scores["A"] = 0.0
        
        # N - New Products/Services (거래량 분석으로 대체)
        # 현재는 데이터 부족으로 중간값 할당
        # TODO: 실제로는 거래량 급증, 신제품 출시 등을 확인해야 함
        scores["N"] = 0.5  # 중립
        
        # S - Supply and Demand (이동평균선 지지)
        if "moving_average" in criteria:
            ma_data = criteria["moving_average"]
            # 20주 이평선 위에서 거래하고 이평선이 상승 추세이면 1점
            above_ma = ma_data.get("above_20w_ma", False)
            ma_rising = ma_data.get("ma20_trending_up", False)
            scores["S"] = 1.0 if (above_ma and ma_rising) else 0.0
        else:
            scores["S"] = 0.0
        
        # L - Leader or Laggard (베타값으로 판단)
        if "market_performance" in criteria:
            market_perf = criteria["market_performance"]
            rel_strength_6m = market_perf.get("relative_strength_6m", -100)
            # 상대강도가 20% 이상이면 확실한 주도주로 판단
            scores["L"] = 1.0 if rel_strength_6m > 20 else 0.0
        else:
            scores["L"] = 0.0
        
        # I - Institutional Sponsorship (거래량 강도로 대체)
        if "volatility" in criteria:
            vol_data = criteria["volatility"]
            if "strength_ratio" in vol_data:
                strength = vol_data["strength_ratio"]
                # 상승 강도가 하락 강도보다 1.2배 이상이면 1점
                scores["I"] = 1.0 if strength >= 1.2 else 0.0
            else:
                scores["I"] = 0.0
        else:
            scores["I"] = 0.0
        
        # M - Market Direction (MACD)
        if "macd" in criteria:
            macd_data = criteria["macd"]
            # 매도 신호가 없으면 1점
            no_sell_signal = not macd_data.get("sell_preparation_needed", True)
            scores["M"] = 1.0 if (not macd_data.get("error") and no_sell_signal) else 0.0
        else:
            scores["M"] = 0.0
        
        return scores
        
    def get_kospi_stocks(self):
        """코스피 주식 리스트 가져오기"""
        try:
            # 한국거래소 상장기업 목록 (코스피)
            url = "http://kind.krx.co.kr/corpgeneral/corpList.do"
            params = {
                'method': 'download',
                'searchType': 'B',
                'marketType': 'stockMkt'  # 코스피
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                # 임시 파일로 저장 후 읽기
                with open('temp_kospi.xls', 'wb') as f:
                    f.write(response.content)
                
                df = pd.read_html('temp_kospi.xls')[0]
                symbols = []
                for code in df['종목코드']:
                    # 6자리 코드를 .KS 형식으로 변환
                    symbol = f"{code:06d}.KS"
                    symbols.append(symbol)
                
                logger.info(f"코스피 주식 {len(symbols)}개 수집 완료")
                return symbols[:150]  # 상위 150개 분석
            
        except Exception as e:
            logger.error(f"코스피 주식 리스트 가져오기 실패: {e}")
            # 대표적인 코스피 주식들
            return [
                "005930.KS", "000660.KS", "035420.KS", "005380.KS", "006400.KS",
                "051910.KS", "035720.KS", "028260.KS", "068270.KS", "207940.KS"
            ]
    
    def get_kosdaq_stocks(self):
        """코스닥 주식 리스트 가져오기"""
        try:
            url = "http://kind.krx.co.kr/corpgeneral/corpList.do"
            params = {
                'method': 'download',
                'searchType': 'B',
                'marketType': 'kosdaqMkt'  # 코스닥
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                with open('temp_kosdaq.xls', 'wb') as f:
                    f.write(response.content)
                
                df = pd.read_html('temp_kosdaq.xls')[0]
                symbols = []
                for code in df['종목코드']:
                    symbol = f"{code:06d}.KQ"
                    symbols.append(symbol)
                
                logger.info(f"코스닥 주식 {len(symbols)}개 수집 완료")
                return symbols[:150]  # 상위 150개 분석
            
        except Exception as e:
            logger.error(f"코스닥 주식 리스트 가져오기 실패: {e}")
            # 대표적인 코스닥 주식들
            return [
                "122630.KQ", "091990.KQ", "067310.KQ", "086900.KQ", "041510.KQ"
            ]
    
    def get_sp500_stocks(self):
        """S&P 500 주식 리스트 가져오기"""
        try:
            # Wikipedia에서 S&P 500 리스트 가져오기
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(url)
            sp500_table = tables[0]
            symbols = sp500_table['Symbol'].tolist()
            
            logger.info(f"S&P 500 주식 {len(symbols)}개 수집 완료")
            return symbols  # 전체 503개 분석
            
        except Exception as e:
            logger.error(f"S&P 500 주식 리스트 가져오기 실패: {e}")
            # 대표적인 S&P 500 주식들
            return [
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK-B",
                "UNH", "JNJ", "V", "PG", "JPM", "HD", "CVX", "MA", "PFE", "ABBV",
                "BAC", "KO"
            ]
    
    def get_nasdaq_stocks(self):
        """나스닥 주요 주식 리스트 가져오기 (약 200개)"""
        try:
            # NASDAQ-100과 추가 주요 종목들을 결합
            nasdaq_stocks = []
            
            # NASDAQ-100 주요 종목들
            nasdaq_100 = [
                "AAPL", "MSFT", "AMZN", "TSLA", "GOOGL", "GOOG", "META", "NVDA", 
                "NFLX", "ADBE", "PYPL", "INTC", "CMCSA", "PEP", "COST", "TMUS",
                "AVGO", "TXN", "QCOM", "CHTR", "SBUX", "GILD", "MDLZ", "FISV",
                "BKNG", "INTU", "ISRG", "ADP", "VRTX", "CSX", "ATVI", "REGN",
                "AMD", "MU", "AMAT", "LRCX", "ADI", "KLAC", "MRVL", "ORLY",
                "CDNS", "SNPS", "CTAS", "WDAY", "IDXX", "NXPI", "LULU", "EXC",
                "DXCM", "TEAM", "ZS", "CRWD", "MRNA", "BIIB", "SIRI", "ILMN",
                "MELI", "ROST", "KDP", "CEG", "FAST", "VRSK", "AEP", "PAYX",
                "CPRT", "PCAR", "ODFL", "CSGP", "MNST", "XEL", "DLTR", "ANSS",
                "TTD", "FANG", "WBD", "SGEN", "ALGN", "CTSH", "FTNT", "VRSN"
            ]
            
            nasdaq_stocks.extend(nasdaq_100)
            
            # 추가 나스닥 종목들 (성장주 및 기술주 중심)
            additional_nasdaq = [
                "ABNB", "ADSK", "ASML", "DOCU", "EBAY", "HOOD", "LYFT", "NTES",
                "OKTA", "ROKU", "SHOP", "SPLK", "SPOT", "SQ", "UBER", "ZM",
                "COIN", "DOCN", "DDOG", "NET", "SNOW", "TWLO", "PLTR", "RBLX",
                "SE", "GRAB", "BABA", "JD", "PDD", "BILI", "TCOM", "NTES",
                "WIX", "FVRR", "UPWK", "ETSY", "PINS", "SNAP", "TWTR", "DBX",
                "BOX", "ZEN", "NOW", "CRM", "ORCL", "SAP", "VMW", "RHT",
                "PANW", "CYBR", "OKTA", "ZS", "CRWD", "S", "VEEV", "WDAY",
                "NTNX", "TWLO", "MDB", "DDOG", "NET", "FSLY", "ESTC", "DOCU"
            ]
            
            nasdaq_stocks.extend(additional_nasdaq)
            
            # 중복 제거 및 최대 200개로 제한
            nasdaq_stocks = list(set(nasdaq_stocks))[:200]
            
            logger.info(f"나스닥 주식 {len(nasdaq_stocks)}개 수집 완료")
            return nasdaq_stocks
            
        except Exception as e:
            logger.error(f"나스닥 주식 리스트 생성 실패: {e}")
            # 기본 NASDAQ-100 반환
            return [
                "AAPL", "MSFT", "AMZN", "TSLA", "GOOGL", "GOOG", "META", "NVDA",
                "NFLX", "ADBE", "PYPL", "INTC", "CMCSA", "PEP", "COST", "TMUS"
            ]
    
    def analyze_stock_batch(self, symbols, market_name, max_workers=10):
        """주식 배치 분석 (병렬 처리)"""
        results = []
        failed_count = 0
        
        logger.info(f"{market_name} 시장 {len(symbols)}개 주식 병렬 분석 시작 (워커: {max_workers}개)")
        
        def analyze_single_stock(symbol):
            """단일 주식 분석 함수"""
            try:
                result = self.analyze_stock(symbol)
                if result and result.get('overall_score', 0) > 30:  # 최소 점수 기준
                    result['market'] = market_name
                    return result
                return None
            except Exception as e:
                logger.warning(f"{market_name} {symbol} 분석 실패: {str(e)[:100]}")
                return None
        
        # 병렬 처리 실행
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 모든 심볼에 대해 Future 객체 생성
            future_to_symbol = {executor.submit(analyze_single_stock, symbol): symbol for symbol in symbols}
            
            # 완료된 작업들을 처리
            completed = 0
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                completed += 1
                
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    failed_count += 1
                    if failed_count % 5 == 0:
                        logger.warning(f"{market_name} {symbol} 분석 실패 (총 {failed_count}개 실패): {str(e)[:100]}")
                
                # 진행 상황 로깅 (10개마다)
                if completed % 10 == 0:
                    logger.info(f"{market_name} 진행률: {completed}/{len(symbols)} ({completed/len(symbols)*100:.1f}%)")
        
        logger.info(f"{market_name} 병렬 분석 완료: 성공 {len(results)}개, 실패 {failed_count}개")
        return results
    
    def get_market_schedule(self):
        """캘리포니아 시간 기준 시장별 스케줄"""
        ca_tz = pytz.timezone('America/Los_Angeles')
        current_time = datetime.now(ca_tz)
        
        schedule = {
            "korean_markets": {
                "name": "한국 시장 (코스피/코스닥)",
                "open_time": "16:00",  # 전날 16:00 (한국 09:00)
                "close_time": "22:30", # 전날 22:30 (한국 15:30)
                "markets": ["KOSPI", "KOSDAQ"]
            },
            "us_markets": {
                "name": "미국 시장 (NASDAQ/S&P500)",
                "open_time": "06:30",  # 당일 06:30 (동부 09:30)
                "close_time": "13:00", # 당일 13:00 (동부 16:00)
                "markets": ["NASDAQ", "SP500"]
            }
        }
        
        return schedule, current_time
    
    def should_run_korean_screening(self):
        """한국 시장 스크리닝 실행 시점인지 확인"""
        schedule, current_time = self.get_market_schedule()
        
        # 한국 시장: 장 시작 30분 전 (15:30) 또는 장 마감 후 (22:40)
        hour = current_time.hour
        minute = current_time.minute
        
        # 15:30 (장 시작 30분 전) 또는 22:40 (장 마감 10분 후)
        return (hour == 15 and minute >= 30) or (hour == 22 and minute >= 40)
    
    def should_run_us_screening(self):
        """미국 시장 스크리닝 실행 시점인지 확인"""
        schedule, current_time = self.get_market_schedule()
        
        # 미국 시장: 장 시작 30분 전 (06:00) 또는 장 마감 후 (13:10)
        hour = current_time.hour
        minute = current_time.minute
        
        # 06:00 (장 시작 30분 전) 또는 13:10 (장 마감 10분 후)
        return (hour == 6 and minute >= 0) or (hour == 13 and minute >= 10)
    
    def run_market_specific_screening(self, markets_to_screen):
        """특정 시장만 스크리닝 실행"""
        logger.info(f"=== {', '.join(markets_to_screen)} 시장 스크리닝 시작 ===")
        start_time = datetime.now()
        
        all_results = []
        
        # 시장별 분석
        market_functions = {
            "KOSPI": self.get_kospi_stocks,
            "KOSDAQ": self.get_kosdaq_stocks,
            "NASDAQ": self.get_nasdaq_stocks,
            "SP500": self.get_sp500_stocks
        }
        
        for market_name in markets_to_screen:
            if market_name in market_functions:
                symbols = market_functions[market_name]()
                market_results = self.analyze_stock_batch(symbols, market_name, max_workers=15)
                all_results.extend(market_results)
        
        # 결과 정렬 (전체 점수 기준)
        all_results.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # 결과 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"screening_{'+'.join(markets_to_screen)}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        
        logger.info(f"=== {', '.join(markets_to_screen)} 스크리닝 완료 ===")
        logger.info(f"총 분석 종목: {len(all_results)}개")
        logger.info(f"소요 시간: {duration:.1f}분")
        
        return all_results, filename
    
    def detect_changes(self, new_results, previous_file=None):
        """이전 결과와 비교하여 변동사항 감지"""
        if not previous_file or not os.path.exists(previous_file):
            return {
                "new_entries": new_results[:10] if new_results else [],
                "score_changes": [],
                "dropped_out": []
            }
        
        try:
            with open(previous_file, 'r', encoding='utf-8') as f:
                previous_results = json.load(f)
        except:
            return {"new_entries": [], "score_changes": [], "dropped_out": []}
        
        # 이전 결과를 딕셔너리로 변환
        prev_dict = {r.get('symbol'): r for r in previous_results}
        new_dict = {r.get('symbol'): r for r in new_results}
        
        changes = {
            "new_entries": [],      # 새로 진입한 종목들
            "score_changes": [],    # 점수 변동이 큰 종목들
            "dropped_out": []       # 탈락한 종목들
        }
        
        # 새로 진입한 종목들
        for symbol in new_dict:
            if symbol not in prev_dict:
                changes["new_entries"].append(new_dict[symbol])
        
        # 점수 변동이 큰 종목들 (10점 이상 변동)
        for symbol in new_dict:
            if symbol in prev_dict:
                old_score = prev_dict[symbol].get('overall_score', 0)
                new_score = new_dict[symbol].get('overall_score', 0)
                score_diff = new_score - old_score
                
                if abs(score_diff) >= 10:  # 10점 이상 변동
                    changes["score_changes"].append({
                        'symbol': symbol,
                        'old_score': old_score,
                        'new_score': new_score,
                        'change': score_diff,
                        'market': new_dict[symbol].get('market')
                    })
        
        # 탈락한 종목들 (이전에 있었지만 이번에 없는 것들)
        for symbol in prev_dict:
            if symbol not in new_dict:
                changes["dropped_out"].append(prev_dict[symbol])
        
        return changes
    
    def run_daily_screening(self):
        """매일 전체 시장 스크리닝 실행 (기존 호환성 유지)"""
        return self.run_market_specific_screening(["KOSPI", "KOSDAQ", "NASDAQ", "SP500"])

def main():
    """메인 실행 함수"""
    screener = MarketScreener()
    results = screener.run_daily_screening()
    
    print(f"\n=== 스크리닝 완료 ===")
    print(f"총 {len(results)}개 종목 분석 완료")
    
    if results:
        print("\n상위 10개 종목:")
        for i, result in enumerate(results[:10], 1):
            symbol = result.get('symbol', 'N/A')
            market = result.get('market', 'N/A')
            score = result.get('overall_score', 0)
            print(f"{i:2d}. {symbol:8s} ({market}) - 점수: {score:.1f}")

if __name__ == "__main__":
    main() 