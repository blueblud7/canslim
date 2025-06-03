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

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketScreener:
    def __init__(self):
        self.analyzer = CANSLIMAnalyzer()
        self.results = []
        
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
                return symbols[:100]  # 테스트용으로 100개만
            
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
                return symbols[:50]  # 테스트용으로 50개만
            
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
            return symbols[:100]  # 테스트용으로 100개만
            
        except Exception as e:
            logger.error(f"S&P 500 주식 리스트 가져오기 실패: {e}")
            # 대표적인 S&P 500 주식들
            return [
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK-B",
                "UNH", "JNJ", "V", "PG", "JPM", "HD", "CVX", "MA", "PFE", "ABBV",
                "BAC", "KO", "PEP", "AVGO", "TMO", "COST", "WMT", "DIS", "ABT"
            ]
    
    def get_nasdaq_stocks(self):
        """나스닥 주요 주식 리스트"""
        # NASDAQ-100 주요 종목들
        return [
            "AAPL", "MSFT", "AMZN", "TSLA", "GOOGL", "GOOG", "META", "NVDA",
            "NFLX", "ADBE", "PYPL", "INTC", "CMCSA", "PEP", "COST", "TMUS",
            "AVGO", "TXN", "QCOM", "CHTR", "SBUX", "INTU", "ISRG", "BKNG",
            "AMD", "GILD", "MU", "FISV", "CSX", "REGN", "ATVI", "MDLZ"
        ]
    
    def analyze_stock_batch(self, symbols, market_name):
        """주식 배치 분석"""
        results = []
        failed_count = 0
        
        logger.info(f"{market_name} 시장 {len(symbols)}개 주식 분석 시작")
        
        for i, symbol in enumerate(symbols):
            try:
                if i % 20 == 0:
                    logger.info(f"{market_name} 진행률: {i}/{len(symbols)} ({i/len(symbols)*100:.1f}%)")
                
                # 분석 실행
                result = self.analyzer.analyze_stock(symbol)
                
                if result and result.get('overall_score', 0) > 0:
                    result['market'] = market_name
                    result['symbol'] = symbol
                    result['analysis_date'] = datetime.now().strftime('%Y-%m-%d')
                    results.append(result)
                
                # API 요청 제한을 위한 딜레이
                time.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                if failed_count % 10 == 0:
                    logger.warning(f"{market_name} {symbol} 분석 실패 (총 {failed_count}개 실패): {str(e)[:100]}")
                continue
        
        logger.info(f"{market_name} 분석 완료: 성공 {len(results)}개, 실패 {failed_count}개")
        return results
    
    def run_daily_screening(self):
        """매일 전체 시장 스크리닝 실행"""
        logger.info("=== CANSLIM 시장 스크리닝 시작 ===")
        start_time = datetime.now()
        
        all_results = []
        
        # 각 시장별 분석
        markets = {
            "KOSPI": self.get_kospi_stocks(),
            "KOSDAQ": self.get_kosdaq_stocks(),
            "NASDAQ": self.get_nasdaq_stocks(),
            "SP500": self.get_sp500_stocks()
        }
        
        for market_name, symbols in markets.items():
            market_results = self.analyze_stock_batch(symbols, market_name)
            all_results.extend(market_results)
        
        # 결과 정렬 (전체 점수 기준)
        all_results.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # 결과 저장
        self.save_screening_results(all_results)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        
        logger.info(f"=== 스크리닝 완료 ===")
        logger.info(f"총 분석 종목: {len(all_results)}개")
        logger.info(f"소요 시간: {duration:.1f}분")
        
        return all_results
    
    def save_screening_results(self, results):
        """스크리닝 결과 저장"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON 파일로 전체 결과 저장
        filename = f"screening_results_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 상위 50개 종목을 CSV로 저장
        if results:
            df = pd.DataFrame(results[:50])
            csv_filename = f"top_stocks_{timestamp}.csv"
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            
            # 간단한 요약 리포트 생성
            self.generate_summary_report(results, timestamp)
        
        logger.info(f"결과 저장 완료: {filename}, {csv_filename}")
    
    def generate_summary_report(self, results, timestamp):
        """요약 리포트 생성"""
        if not results:
            return
        
        report = []
        report.append("# CANSLIM 일일 스크리닝 리포트")
        report.append(f"날짜: {datetime.now().strftime('%Y년 %m월 %d일')}")
        report.append(f"분석 종목 수: {len(results)}개")
        report.append("")
        
        # 시장별 통계
        markets = {}
        for result in results:
            market = result.get('market', 'Unknown')
            if market not in markets:
                markets[market] = []
            markets[market].append(result)
        
        report.append("## 시장별 분석 결과")
        for market, market_results in markets.items():
            avg_score = np.mean([r.get('overall_score', 0) for r in market_results])
            report.append(f"- {market}: {len(market_results)}개 종목, 평균 점수: {avg_score:.1f}")
        report.append("")
        
        # 상위 20개 종목
        report.append("## 상위 20개 종목")
        report.append("| 순위 | 종목 | 시장 | 점수 | C | A | N | S | L | I | M |")
        report.append("|------|------|------|------|---|---|---|---|---|---|---|")
        
        for i, result in enumerate(results[:20], 1):
            symbol = result.get('symbol', 'N/A')
            market = result.get('market', 'N/A')
            score = result.get('overall_score', 0)
            
            # CANSLIM 개별 점수
            canslim_scores = result.get('canslim_scores', {})
            c = canslim_scores.get('C', 0)
            a = canslim_scores.get('A', 0)
            n = canslim_scores.get('N', 0)
            s = canslim_scores.get('S', 0)
            l = canslim_scores.get('L', 0)
            i = canslim_scores.get('I', 0)
            m = canslim_scores.get('M', 0)
            
            report.append(f"| {i} | {symbol} | {market} | {score:.1f} | {c:.1f} | {a:.1f} | {n:.1f} | {s:.1f} | {l:.1f} | {i:.1f} | {m:.1f} |")
        
        # 리포트 저장
        report_filename = f"screening_report_{timestamp}.md"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        logger.info(f"요약 리포트 생성: {report_filename}")

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