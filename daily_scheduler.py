#!/usr/bin/env python3
"""
CANSLIM 시간대별 자동 스크리닝 스케줄러
캘리포니아 시간 기준으로 한국/미국 시장별 최적 시간에 자동 실행
"""

import schedule
import time
import logging
from datetime import datetime
import pytz
from market_screener import MarketScreener

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_korean_market_screening():
    """한국 시장 스크리닝 실행"""
    try:
        logger.info("=== 한국 시장 스크리닝 시작 ===")
        screener = MarketScreener()
        results, filename = screener.run_market_specific_screening(["KOSPI", "KOSDAQ"])
        logger.info(f"한국 시장 스크리닝 완료: {len(results)}개 종목, 파일: {filename}")
    except Exception as e:
        logger.error(f"한국 시장 스크리닝 실패: {str(e)}")

def run_us_market_screening():
    """미국 시장 스크리닝 실행"""
    try:
        logger.info("=== 미국 시장 스크리닝 시작 ===")
        screener = MarketScreener()
        results, filename = screener.run_market_specific_screening(["NASDAQ", "SP500"])
        logger.info(f"미국 시장 스크리닝 완료: {len(results)}개 종목, 파일: {filename}")
    except Exception as e:
        logger.error(f"미국 시장 스크리닝 실패: {str(e)}")

def setup_scheduler():
    """스케줄러 설정 (캘리포니아 시간 기준)"""
    
    # 한국 시장 스케줄
    # 장 시작 30분 전: 15:30 (한국 09:00 - 30분)
    # 장 마감 10분 후: 22:40 (한국 15:30 + 10분)
    schedule.every().monday.at("15:30").do(run_korean_market_screening).tag("korean_premarket")
    schedule.every().tuesday.at("15:30").do(run_korean_market_screening).tag("korean_premarket")
    schedule.every().wednesday.at("15:30").do(run_korean_market_screening).tag("korean_premarket")
    schedule.every().thursday.at("15:30").do(run_korean_market_screening).tag("korean_premarket")
    schedule.every().friday.at("15:30").do(run_korean_market_screening).tag("korean_premarket")
    
    schedule.every().monday.at("22:40").do(run_korean_market_screening).tag("korean_postmarket")
    schedule.every().tuesday.at("22:40").do(run_korean_market_screening).tag("korean_postmarket")
    schedule.every().wednesday.at("22:40").do(run_korean_market_screening).tag("korean_postmarket")
    schedule.every().thursday.at("22:40").do(run_korean_market_screening).tag("korean_postmarket")
    schedule.every().friday.at("22:40").do(run_korean_market_screening).tag("korean_postmarket")
    
    # 미국 시장 스케줄
    # 장 시작 30분 전: 06:00 (동부 09:30 - 30분)
    # 장 마감 10분 후: 13:10 (동부 16:00 + 10분)
    schedule.every().monday.at("06:00").do(run_us_market_screening).tag("us_premarket")
    schedule.every().tuesday.at("06:00").do(run_us_market_screening).tag("us_premarket")
    schedule.every().wednesday.at("06:00").do(run_us_market_screening).tag("us_premarket")
    schedule.every().thursday.at("06:00").do(run_us_market_screening).tag("us_premarket")
    schedule.every().friday.at("06:00").do(run_us_market_screening).tag("us_premarket")
    
    schedule.every().monday.at("13:10").do(run_us_market_screening).tag("us_postmarket")
    schedule.every().tuesday.at("13:10").do(run_us_market_screening).tag("us_postmarket")
    schedule.every().wednesday.at("13:10").do(run_us_market_screening).tag("us_postmarket")
    schedule.every().thursday.at("13:10").do(run_us_market_screening).tag("us_postmarket")
    schedule.every().friday.at("13:10").do(run_us_market_screening).tag("us_postmarket")
    
    logger.info("시간대별 스케줄러 설정 완료")
    logger.info("한국 시장: 15:30 (장 시작 전), 22:40 (장 마감 후)")
    logger.info("미국 시장: 06:00 (장 시작 전), 13:10 (장 마감 후)")

def check_current_time():
    """현재 시간과 다음 스케줄 확인"""
    ca_tz = pytz.timezone('America/Los_Angeles')
    current_time = ca_tz.localize(datetime.now())
    
    logger.info(f"현재 시간 (캘리포니아): {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # 다음 스케줄 확인
    next_run = schedule.next_run()
    if next_run:
        logger.info(f"다음 스크리닝 예정: {next_run}")

def run_scheduler(daemon_mode=False):
    """스케줄러 실행"""
    setup_scheduler()
    check_current_time()
    
    if daemon_mode:
        logger.info("데몬 모드로 스케줄러 시작...")
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
    else:
        logger.info("대화형 모드로 스케줄러 시작... (Ctrl+C로 종료)")
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)  # 30초마다 체크
        except KeyboardInterrupt:
            logger.info("스케줄러 종료")

if __name__ == "__main__":
    import sys
    
    daemon_mode = "--daemon" in sys.argv
    run_scheduler(daemon_mode) 