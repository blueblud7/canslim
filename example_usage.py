#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CANSLIM 주도주 분석기 사용 예제
"""

from canslim_analyzer import CANSLIMAnalyzer
import json
from pprint import pprint

def example_single_stock_analysis():
    """단일 주식 분석 예제"""
    print("=" * 60)
    print("📈 단일 주식 주도주 분석 예제")
    print("=" * 60)
    
    # 분석기 초기화 (한국 시장용)
    analyzer = CANSLIMAnalyzer(benchmark_symbol="^KS11")  # 코스피 지수
    
    # 분석할 주식 (예: 삼성전자)
    symbol = "005930.KS"  # 한국 주식의 야후 파이낸스 심볼 형식
    
    print(f"🔍 {symbol} 주도주 특성 분석 중...")
    
    # 주도주 분석 실행
    result = analyzer.analyze_leadership_criteria(symbol)
    
    if "error" in result:
        print(f"❌ 분석 실패: {result['error']}")
        return
    
    # 결과 출력
    print(f"\n📊 {result['symbol']} 분석 결과 ({result['analysis_date']})")
    print("-" * 50)
    
    # 52주 신고가 분석
    high_52w = result["criteria"]["52w_high"]
    print(f"🎯 52주 신고가 분석:")
    print(f"   현재가: {high_52w['current_price']:,}원")
    print(f"   52주 최고가: {high_52w['52w_high']:,}원")
    print(f"   신고가 대비: {high_52w['distance_from_high']:+.1f}%")
    print(f"   신고가 근처: {'✅' if high_52w['is_near_high'] else '❌'}")
    
    # 시장 대비 성과
    if "market_performance" in result["criteria"]:
        market_perf = result["criteria"]["market_performance"]
        print(f"\n📈 시장 대비 성과:")
        print(f"   베타: {market_perf['beta']}")
        print(f"   3개월 상대강도: {market_perf['relative_strength_3m']:+.1f}%")
        print(f"   6개월 상대강도: {market_perf['relative_strength_6m']:+.1f}%")
        print(f"   시장 대비 우수: {'✅' if market_perf['outperforms_market'] else '❌'}")
    
    # 이동평균선 분석
    ma_analysis = result["criteria"]["moving_average"]
    print(f"\n📊 이동평균선 분석:")
    print(f"   20주 이평선: {ma_analysis['ma20_value']:,}원")
    print(f"   이평선 위 거래: {'✅' if ma_analysis['above_20w_ma'] else '❌'}")
    print(f"   이평선 상승 추세: {'✅' if ma_analysis['ma20_trending_up'] else '❌'}")
    
    # MACD 분석
    macd = result["criteria"]["macd"]
    if "error" not in macd:
        print(f"\n🔄 MACD 분석 (월봉):")
        print(f"   현재 MACD: {macd['current_macd']}")
        print(f"   시그널: {macd['current_signal']}")
        print(f"   히스토그램: {macd['current_histogram']}")
        print(f"   매도 준비 신호: {'⚠️' if macd['sell_preparation_needed'] else '✅'}")
    
    # 종합 점수
    score = result["leadership_score"]
    print(f"\n🏆 주도주 종합 점수:")
    print(f"   점수: {score['score']}/{score['max_score']} ({score['percentage']}%)")
    print(f"   등급: {score['grade']}")
    
    return result

def example_sector_caution_analysis():
    """섹터 조심 기준 분석 예제"""
    print("\n" + "=" * 60)
    print("⚠️  섹터 투자 조심 기준 분석 예제")
    print("=" * 60)
    
    analyzer = CANSLIMAnalyzer()
    
    # 반도체 섹터 주요 종목들 (예시)
    sector_symbols = [
        "005930.KS",  # 삼성전자
        "000660.KS",  # SK하이닉스
        "042700.KS",  # 한미반도체
        "039030.KS",  # 이오테크닉스
    ]
    
    print(f"🔍 반도체 섹터 ({len(sector_symbols)}개 종목) 조심 기준 분석 중...")
    
    # 조심 기준 분석 실행
    caution_result = analyzer.analyze_caution_criteria(sector_symbols, "반도체")
    
    if "error" in caution_result:
        print(f"❌ 분석 실패: {caution_result['error']}")
        return
    
    print(f"\n⚠️  {caution_result['sector']} 섹터 조심 신호 분석 결과")
    print(f"분석일: {caution_result['analysis_date']}")
    print("-" * 50)
    
    signals = caution_result["caution_signals"]
    
    # 후진주 급등 분석
    if "laggard_surge" in signals:
        laggard = signals["laggard_surge"]
        if "error" not in laggard:
            print(f"📊 후진주 급등 분석:")
            print(f"   후진주 평균 6개월 수익률: {laggard['avg_laggard_return_6m']:+.1f}%")
            print(f"   50% 이상 급등: {'⚠️' if laggard['laggards_surge_50pct'] else '✅'}")
    
    # 고평가 지속 분석
    if "high_pbr" in signals:
        pbr = signals["high_pbr"]
        if "error" not in pbr:
            print(f"\n💰 고평가 지속 분석:")
            print(f"   고평가 종목 비율: {pbr['high_valuation_ratio']:.1%}")
            print(f"   위험 신호: {'⚠️' if pbr['warning_signal'] else '✅'}")
    
    # 레버리지 리스크
    if "leverage_risk" in signals:
        leverage = signals["leverage_risk"]
        if "error" not in leverage:
            print(f"\n⚡ 레버리지 리스크 분석:")
            print(f"   극단적 수익 종목: {leverage['extreme_gain_count']}개")
            print(f"   위험 신호: {'⚠️' if leverage['warning_signal'] else '✅'}")
    
    # 시장 과열
    if "market_heat" in signals:
        heat = signals["market_heat"]
        if "error" not in heat:
            print(f"\n🌡️  시장 과열 분석:")
            print(f"   3개월 평균 수익률: {heat['avg_return_3m']:+.1f}%")
            print(f"   6개월 평균 수익률: {heat['avg_return_6m']:+.1f}%")
            print(f"   과열 신호: {'⚠️' if heat['warning_signal'] else '✅'}")
    
    # 종합 조심 점수
    print(f"\n🚨 종합 조심 점수: {caution_result['caution_score']}/7")
    print(f"고위험 상태: {'⚠️ 매우 조심!' if caution_result['high_caution'] else '✅ 양호'}")
    
    return caution_result

def example_comprehensive_report():
    """종합 분석 리포트 예제"""
    print("\n" + "=" * 60)
    print("📋 종합 분석 리포트 예제")
    print("=" * 60)
    
    analyzer = CANSLIMAnalyzer()
    
    # 분석 대상 주식
    target_symbol = "005930.KS"  # 삼성전자
    
    # 같은 섹터 종목들
    sector_symbols = [
        "005930.KS",  # 삼성전자
        "000660.KS",  # SK하이닉스
        "042700.KS",  # 한미반도체
    ]
    
    print(f"🔍 {target_symbol} 종합 분석 중...")
    
    # 종합 리포트 생성
    report = analyzer.generate_report(target_symbol, sector_symbols)
    
    print(f"\n📊 {report['symbol']} 종합 분석 리포트")
    print(f"생성일시: {report['report_date']}")
    print("=" * 50)
    
    # 주도주 분석 요약
    if report["leadership_analysis"]:
        leadership = report["leadership_analysis"]
        score = leadership["leadership_score"]
        print(f"🏆 주도주 점수: {score['score']}/{score['max_score']} ({score['grade']})")
    
    # 조심 신호 요약
    if report["caution_analysis"]:
        caution = report["caution_analysis"]
        print(f"⚠️ 조심 신호: {caution['caution_score']}/7")
    
    # 최종 추천
    if report["recommendation"]:
        rec = report["recommendation"]
        print(f"\n💡 투자 추천:")
        print(f"   결정: {rec['action']}")
        print(f"   이유: {rec['reason']}")
        print(f"   신뢰도: {rec['confidence']}%")
    
    return report

def save_results_to_file(results, filename):
    """분석 결과를 JSON 파일로 저장"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n📁 결과가 {filename}에 저장되었습니다.")
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")

if __name__ == "__main__":
    print("🚀 CANSLIM 주도주 분석기 실행")
    print("William O'Neil의 CANSLIM 투자 기법 기반 정량 분석 도구")
    
    try:
        # 1. 단일 주식 분석
        single_result = example_single_stock_analysis()
        
        # 2. 섹터 조심 기준 분석
        caution_result = example_sector_caution_analysis()
        
        # 3. 종합 분석 리포트
        comprehensive_result = example_comprehensive_report()
        
        # 4. 결과 저장
        all_results = {
            "single_analysis": single_result,
            "caution_analysis": caution_result,
            "comprehensive_report": comprehensive_result
        }
        
        save_results_to_file(all_results, "canslim_analysis_results.json")
        
        print("\n✅ 모든 분석이 완료되었습니다!")
        
    except Exception as e:
        print(f"\n❌ 실행 중 오류 발생: {e}")
        print("패키지 설치 확인: pip install -r requirements.txt") 