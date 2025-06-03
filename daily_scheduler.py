#!/usr/bin/env python3
"""
CANSLIM 매일 자동 스크리닝 스케줄러
매일 정해진 시간에 자동으로 시장 스크리닝을 실행
"""

import schedule
import time
import logging
from datetime import datetime
import os
import sys
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

class DailyScheduler:
    def __init__(self):
        self.screener = MarketScreener()
    
    def run_daily_screening(self):
        """매일 스크리닝 실행"""
        try:
            logger.info("=== 매일 자동 스크리닝 시작 ===")
            
            # 주말 제외 (월-금만 실행)
            weekday = datetime.now().weekday()
            if weekday >= 5:  # 토요일(5), 일요일(6)
                logger.info("주말이므로 스크리닝을 건너뜁니다.")
                return
            
            # 스크리닝 실행
            results = self.screener.run_daily_screening()
            
            if results:
                logger.info(f"✅ 자동 스크리닝 완료! {len(results)}개 종목 분석")
                
                # 상위 5개 종목 로그
                logger.info("상위 5개 종목:")
                for i, result in enumerate(results[:5], 1):
                    symbol = result.get('symbol', 'N/A')
                    market = result.get('market', 'N/A')
                    score = result.get('overall_score', 0)
                    logger.info(f"  {i}. {symbol} ({market}) - 점수: {score:.1f}")
            else:
                logger.warning("스크리닝 결과가 없습니다.")
                
        except Exception as e:
            logger.error(f"자동 스크리닝 중 오류 발생: {str(e)}")
    
    def start_scheduler(self):
        """스케줄러 시작"""
        logger.info("CANSLIM 자동 스크리닝 스케줄러 시작")
        
        # 매일 여러 시간에 스크리닝 실행
        schedule.every().day.at("09:30").do(self.run_daily_screening)  # 한국 시장 개장 후
        schedule.every().day.at("15:30").do(self.run_daily_screening)  # 한국 시장 마감 후
        schedule.every().day.at("23:30").do(self.run_daily_screening)  # 미국 시장 마감 후
        
        logger.info("스케줄 등록 완료:")
        logger.info("- 매일 09:30 (한국 시장 개장 후)")
        logger.info("- 매일 15:30 (한국 시장 마감 후)")  
        logger.info("- 매일 23:30 (미국 시장 마감 후)")
        
        # 무한 루프로 스케줄 실행
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
        except KeyboardInterrupt:
            logger.info("스케줄러 종료")

def run_once():
    """즉시 1회 실행"""
    scheduler = DailyScheduler()
    scheduler.run_daily_screening()

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CANSLIM 자동 스크리닝 스케줄러')
    parser.add_argument('--once', action='store_true', help='즉시 1회 실행')
    parser.add_argument('--daemon', action='store_true', help='데몬 모드로 실행')
    
    args = parser.parse_args()
    
    if args.once:
        run_once()
    else:
        scheduler = DailyScheduler()
        if args.daemon:
            # 백그라운드 데몬으로 실행
            import daemon
            with daemon.DaemonContext():
                scheduler.start_scheduler()
        else:
            # 포그라운드에서 실행
            scheduler.start_scheduler()

if __name__ == "__main__":
    main() 