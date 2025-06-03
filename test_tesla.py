#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from canslim_analyzer import CANSLIMAnalyzer
import json

def test_tesla():
    """테슬라 분석 테스트"""
    print("🚗 테슬라(TSLA) CANSLIM 분석 테스트")
    print("=" * 50)
    
    # S&P 500을 기준으로 분석
    analyzer = CANSLIMAnalyzer(benchmark_symbol='^GSPC')
    result = analyzer.analyze_leadership_criteria('TSLA')
    
    if "error" in result:
        print(f"❌ 분석 실패: {result['error']}")
        return
    
    print(f"📊 심볼: {result['symbol']}")
    print(f"📅 분석일: {result['analysis_date']}")
    
    # 주도주 점수
    score = result['leadership_score']
    print(f"\n🏆 주도주 점수: {score['score']}/6 ({score['percentage']}%, {score['grade']})")
    
    # 52주 신고가 분석
    high_52w = result['criteria']['52w_high']
    print(f"\n🎯 52주 신고가 분석:")
    print(f"   현재가: ${high_52w['current_price']:,.2f}")
    print(f"   52주 최고가: ${high_52w['52w_high']:,.2f}")
    print(f"   신고가 대비: {high_52w['distance_from_high']:+.1f}%")
    print(f"   신고가 근처: {'✅' if high_52w['is_near_high'] else '❌'}")
    
    # 시장 대비 성과
    if 'market_performance' in result['criteria']:
        market = result['criteria']['market_performance']
        print(f"\n📈 시장 대비 성과:")
        print(f"   베타: {market['beta']}")
        print(f"   3개월 상대강도: {market['relative_strength_3m']:+.1f}%")
        print(f"   6개월 상대강도: {market['relative_strength_6m']:+.1f}%")
        print(f"   시장 대비 우수: {'✅' if market['outperforms_market'] else '❌'}")
    
    # 이동평균선
    ma = result['criteria']['moving_average']
    print(f"\n📊 이동평균선:")
    print(f"   20주 이평선: ${ma['ma20_value']:,.2f}")
    print(f"   이평선 위 거래: {'✅' if ma['above_20w_ma'] else '❌'}")
    print(f"   이평선 상승: {'✅' if ma['ma20_trending_up'] else '❌'}")
    
    # 최종 평가
    print(f"\n💡 분석 결과:")
    if score['score'] >= 4:
        print("   🟢 양호한 주도주 특성")
    elif score['score'] >= 3:
        print("   🟡 보통 수준의 주도주 특성")
    else:
        print("   🔴 부족한 주도주 특성")
    
    return result

if __name__ == "__main__":
    test_tesla() 