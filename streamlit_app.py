import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from canslim_analyzer import CANSLIMAnalyzer
import json
from datetime import datetime, timedelta
import os
from market_screener import MarketScreener

# 페이지 설정
st.set_page_config(
    page_title="CANSLIM 주도주 분석기",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 메인 타이틀
st.title("📈 CANSLIM 주도주 분석기")
st.markdown("**William O'Neil의 CANSLIM 투자 기법 기반 정량적 주식 분석 도구**")

# 사이드바 설정
st.sidebar.header("🔧 분석 설정")

# 벤치마크 선택
benchmark_options = {
    "코스피 (^KS11)": "^KS11",
    "코스닥 (^KQ11)": "^KQ11", 
    "S&P 500 (^GSPC)": "^GSPC",
    "나스닥 (^IXIC)": "^IXIC"
}

selected_benchmark = st.sidebar.selectbox(
    "벤치마크 지수 선택",
    list(benchmark_options.keys()),
    index=0
)

benchmark_symbol = benchmark_options[selected_benchmark]

# 분석기 초기화
@st.cache_resource
def get_analyzer(benchmark):
    return CANSLIMAnalyzer(benchmark_symbol=benchmark)

analyzer = get_analyzer(benchmark_symbol)

# 탭 생성
tab1, tab2, tab3, tab4 = st.tabs(["🎯 개별 주식 분석", "⚠️ 섹터 위험 분석", "📊 종합 리포트", "📚 사용 가이드"])

# 탭 1: 개별 주식 분석
with tab1:
    st.header("🎯 개별 주식 주도주 특성 분석")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        symbol_input = st.text_input(
            "주식 심볼 입력 (예: 005930.KS, AAPL, TSLA)",
            value="005930.KS",
            help="한국 주식은 종목코드.KS (코스피) 또는 종목코드.KQ (코스닥) 형태로 입력"
        )
    
    with col2:
        analyze_button = st.button("📈 분석 시작", type="primary")
    
    if analyze_button and symbol_input:
        with st.spinner("주도주 특성 분석 중..."):
            result = analyzer.analyze_leadership_criteria(symbol_input.upper())
        
        if "error" in result:
            st.error(f"❌ 분석 실패: {result['error']}")
        else:
            # 기본 정보
            st.success(f"✅ {result['symbol']} 분석 완료!")
            
            # 종합 점수 표시
            score = result["leadership_score"]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("주도주 점수", f"{score['score']}/{score['max_score']}")
            with col2:
                st.metric("백분율", f"{score['percentage']}%")
            with col3:
                st.metric("등급", score['grade'])
            with col4:
                confidence_color = "green" if score['percentage'] >= 70 else "orange" if score['percentage'] >= 50 else "red"
                st.markdown(f"<h3 style='color: {confidence_color};'>신뢰도: {score['percentage']}%</h3>", unsafe_allow_html=True)
            
            # 상세 분석 결과
            st.subheader("📊 상세 분석 결과")
            
            # 52주 신고가 분석
            high_52w = result["criteria"]["52w_high"]
            with st.expander("🎯 52주 신고가 분석", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("현재가", f"{high_52w['current_price']:,.0f}")
                with col2:
                    st.metric("52주 최고가", f"{high_52w['52w_high']:,.0f}")
                with col3:
                    distance_color = "green" if high_52w['distance_from_high'] >= -5 else "red"
                    st.markdown(f"<p style='color: {distance_color}; font-size: 20px;'>신고가 대비: {high_52w['distance_from_high']:+.1f}%</p>", unsafe_allow_html=True)
                
                # 신고가 근처 여부
                if high_52w['is_near_high']:
                    st.success("✅ 52주 신고가 근처에서 거래 중 (95% 이상)")
                else:
                    st.warning(f"⚠️ 52주 신고가에서 {abs(high_52w['distance_from_high']):.1f}% 하락")
            
            # 시장 대비 성과
            if "market_performance" in result["criteria"]:
                market_perf = result["criteria"]["market_performance"]
                with st.expander("📈 시장 대비 성과", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        beta_color = "green" if 0.8 <= market_perf['beta'] <= 1.2 else "orange"
                        st.markdown(f"<p style='color: {beta_color};'>베타: {market_perf['beta']}</p>", unsafe_allow_html=True)
                    with col2:
                        rs3m_color = "green" if market_perf['relative_strength_3m'] > 0 else "red"
                        st.markdown(f"<p style='color: {rs3m_color};'>3개월 상대강도: {market_perf['relative_strength_3m']:+.1f}%</p>", unsafe_allow_html=True)
                    with col3:
                        rs6m_color = "green" if market_perf['relative_strength_6m'] > 0 else "red"
                        st.markdown(f"<p style='color: {rs6m_color};'>6개월 상대강도: {market_perf['relative_strength_6m']:+.1f}%</p>", unsafe_allow_html=True)
                    with col4:
                        if market_perf['outperforms_market']:
                            st.success("✅ 시장 대비 우수")
                        else:
                            st.error("❌ 시장 대비 부진")
            
            # 이동평균선 분석
            ma_analysis = result["criteria"]["moving_average"]
            with st.expander("📊 이동평균선 분석", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("20주 이평선", f"{ma_analysis['ma20_value']:,.0f}")
                with col2:
                    if ma_analysis['above_20w_ma']:
                        st.success("✅ 이평선 위 거래")
                    else:
                        st.error("❌ 이평선 아래 거래")
                with col3:
                    if ma_analysis['ma20_trending_up']:
                        st.success("✅ 이평선 상승 추세")
                    else:
                        st.error("❌ 이평선 하락 추세")
            
            # MACD 분석
            macd = result["criteria"]["macd"]
            if "error" not in macd:
                with st.expander("🔄 MACD 분석 (월봉)", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("MACD", f"{macd['current_macd']:.4f}" if macd['current_macd'] else "N/A")
                    with col2:
                        st.metric("시그널", f"{macd['current_signal']:.4f}" if macd['current_signal'] else "N/A")
                    with col3:
                        st.metric("히스토그램", f"{macd['current_histogram']:.4f}" if macd['current_histogram'] else "N/A")
                    
                    if macd['sell_preparation_needed']:
                        st.warning("⚠️ 매도 준비 신호 감지!")
                    else:
                        st.success("✅ 매도 신호 없음")
            
            # 변동성 분석
            volatility = result["criteria"]["volatility"]
            if "error" not in volatility:
                with st.expander("📊 변동성 및 강도 분석"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("20일 변동성", f"{volatility['volatility_20d']:.1f}%")
                    with col2:
                        st.metric("상승일 비율", f"{volatility['up_days_ratio']:.1%}")
                    with col3:
                        strength_color = "green" if volatility['strength_ratio'] >= 1.2 else "red"
                        st.markdown(f"<p style='color: {strength_color};'>강도 비율: {volatility['strength_ratio']:.1f}</p>", unsafe_allow_html=True)

# 탭 2: 섹터 위험 분석
with tab2:
    st.header("⚠️ 섹터 투자 조심 기준 분석")
    
    # 섹터 종목 입력
    st.subheader("📝 분석할 섹터 종목들")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        sector_name = st.text_input("섹터명", value="반도체", help="분석할 섹터의 이름을 입력하세요")
        
        # 기본 종목 리스트
        default_symbols = "005930.KS\n000660.KS\n042700.KS\n039030.KS"
        symbols_text = st.text_area(
            "종목 심볼 (한 줄에 하나씩)",
            value=default_symbols,
            height=150,
            help="분석할 종목들의 심볼을 한 줄에 하나씩 입력하세요"
        )
    
    with col2:
        st.write("### 💡 예시 섹터")
        st.write("**반도체:**")
        st.write("- 005930.KS (삼성전자)")
        st.write("- 000660.KS (SK하이닉스)")
        st.write("- 042700.KS (한미반도체)")
        
        st.write("**바이오:**")
        st.write("- 207940.KS (삼성바이오)")
        st.write("- 068270.KS (셀트리온)")
        st.write("- 091990.KS (셀트리온헬스케어)")
    
    sector_analyze_button = st.button("🔍 섹터 위험 분석", type="primary")
    
    if sector_analyze_button and symbols_text.strip():
        symbols_list = [s.strip().upper() for s in symbols_text.split('\n') if s.strip()]
        
        with st.spinner(f"{sector_name} 섹터 위험 분석 중..."):
            caution_result = analyzer.analyze_caution_criteria(symbols_list, sector_name)
        
        if "error" in caution_result:
            st.error(f"❌ 분석 실패: {caution_result['error']}")
        else:
            # 종합 조심 점수
            caution_score = caution_result["caution_score"]
            is_high_caution = caution_result["high_caution"]
            
            # 상단 메트릭
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("조심 신호", f"{caution_score}/7")
            with col2:
                st.metric("분석 종목 수", caution_result["symbol_count"])
            with col3:
                risk_level = "높음" if is_high_caution else "보통" if caution_score >= 3 else "낮음"
                risk_color = "red" if is_high_caution else "orange" if caution_score >= 3 else "green"
                st.markdown(f"<p style='color: {risk_color}; font-size: 20px;'>위험도: {risk_level}</p>", unsafe_allow_html=True)
            with col4:
                if is_high_caution:
                    st.error("🚨 매우 조심!")
                elif caution_score >= 3:
                    st.warning("⚠️ 주의 필요")
                else:
                    st.success("✅ 양호")
            
            # 상세 분석 결과
            signals = caution_result["caution_signals"]
            
            # 후진주 급등 분석
            if "laggard_surge" in signals and "error" not in signals["laggard_surge"]:
                laggard = signals["laggard_surge"]
                with st.expander("📊 후진주 급등 분석", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("후진주 6개월 평균 수익률", f"{laggard['avg_laggard_return_6m']:+.1f}%")
                    with col2:
                        if laggard['laggards_surge_50pct']:
                            st.error("⚠️ 후진주 50% 이상 급등!")
                        else:
                            st.success("✅ 후진주 급등 없음")
            
            # 고평가 지속 분석
            if "high_pbr" in signals and "error" not in signals["high_pbr"]:
                pbr = signals["high_pbr"]
                with st.expander("💰 고평가 지속 분석", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("고평가 종목 비율", f"{pbr['high_valuation_ratio']:.1%}")
                    with col2:
                        if pbr['warning_signal']:
                            st.warning("⚠️ 고평가 위험 신호")
                        else:
                            st.success("✅ 적정 평가 수준")
            
            # 레버리지 리스크
            if "leverage_risk" in signals and "error" not in signals["leverage_risk"]:
                leverage = signals["leverage_risk"]
                with st.expander("⚡ 레버리지 리스크 분석", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("극단적 수익 종목", f"{leverage['extreme_gain_count']}개")
                    with col2:
                        if leverage['warning_signal']:
                            st.error("⚠️ 레버리지 위험!")
                        else:
                            st.success("✅ 레버리지 위험 없음")
            
            # 시장 과열
            if "market_heat" in signals and "error" not in signals["market_heat"]:
                heat = signals["market_heat"]
                with st.expander("🌡️ 시장 과열 분석", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("3개월 평균 수익률", f"{heat['avg_return_3m']:+.1f}%")
                    with col2:
                        st.metric("6개월 평균 수익률", f"{heat['avg_return_6m']:+.1f}%")
                    with col3:
                        if heat['warning_signal']:
                            st.warning("⚠️ 과열 신호")
                        else:
                            st.success("✅ 적정 수준")

# 탭 3: 종합 리포트
with tab3:
    st.header("📊 종합 분석 리포트")
    
    col1, col2 = st.columns([2, 2])
    
    with col1:
        target_symbol = st.text_input(
            "분석 대상 주식",
            value="005930.KS",
            help="종합 분석할 주식의 심볼을 입력하세요"
        )
        
        sector_symbols_for_report = st.text_area(
            "섹터 종목들 (선택사항)",
            value="005930.KS\n000660.KS\n042700.KS",
            height=100,
            help="같은 섹터의 종목들을 입력하면 더 정확한 분석이 가능합니다"
        )
    
    with col2:
        st.write("### 📋 종합 리포트 포함 내용")
        st.write("✅ 주도주 특성 점수")
        st.write("✅ 섹터 위험 신호")
        st.write("✅ 투자 추천 결정")
        st.write("✅ 신뢰도 평가")
        st.write("✅ 상세 근거 제시")
    
    report_button = st.button("📋 종합 리포트 생성", type="primary")
    
    if report_button and target_symbol:
        sector_list = [s.strip().upper() for s in sector_symbols_for_report.split('\n') if s.strip()] if sector_symbols_for_report.strip() else None
        
        with st.spinner("종합 분석 리포트 생성 중..."):
            report = analyzer.generate_report(target_symbol.upper(), sector_list)
        
        # 리포트 헤더
        st.success(f"✅ {report['symbol']} 종합 분석 리포트 완료!")
        st.write(f"**생성일시:** {report['report_date']}")
        
        # 핵심 요약
        st.subheader("🎯 핵심 요약")
        
        if report["recommendation"]:
            rec = report["recommendation"]
            
            # 추천 결정 표시
            action_color = {
                "적극 매수": "green",
                "조건부 매수": "blue", 
                "조심스런 매수": "orange",
                "매수 보류": "red",
                "매우 조심": "red"
            }.get(rec["action"], "gray")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"<h2 style='color: {action_color};'>{rec['action']}</h2>", unsafe_allow_html=True)
            with col2:
                st.metric("주도주 점수", f"{rec['leadership_score']}/6")
            with col3:
                st.metric("조심 신호", f"{rec['caution_score']}/7")
            with col4:
                confidence_color = "green" if rec['confidence'] >= 70 else "orange" if rec['confidence'] >= 50 else "red"
                st.markdown(f"<p style='color: {confidence_color}; font-size: 24px;'>신뢰도: {rec['confidence']}%</p>", unsafe_allow_html=True)
            
            # 추천 근거
            st.info(f"**추천 근거:** {rec['reason']}")
        
        # 상세 분석 토글
        with st.expander("📊 상세 분석 결과 보기"):
            if report["leadership_analysis"]:
                st.json(report["leadership_analysis"])
            
            if report["caution_analysis"]:
                st.json(report["caution_analysis"])
        
        # 결과 다운로드
        report_json = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        st.download_button(
            label="📥 리포트 다운로드 (JSON)",
            data=report_json,
            file_name=f"canslim_report_{target_symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

# 탭 4: 사용 가이드
with tab4:
    st.header("📚 CANSLIM 주도주 점수 완벽 가이드")
    
    try:
        with open('CANSLIM_가이드.md', 'r', encoding='utf-8') as f:
            guide_content = f.read()
        st.markdown(guide_content, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("가이드 파일을 찾을 수 없습니다.")
        
        # 기본 가이드 내용
        st.markdown("""
        ## 🎯 주도주 점수란?
        
        **주도주 점수**는 William O'Neil의 CANSLIM 투자 기법을 바탕으로, 
        역사상 큰 수익을 낸 주식들의 공통 특성 6가지를 점수화한 시스템입니다.
        
        ### 🏆 6가지 주도주 특성 (각 1점)
        
        1. **🎯 52주 신고가**: 현재가 ≥ 최고가의 95%
        2. **📈 시장 우수성**: 6개월 상대강도 > 0%  
        3. **📊 이평선 지지**: 현재가 > 20주 이평선
        4. **⬆️ 이평선 상승**: 20주 이평선 기울기 > 0
        5. **🔄 MACD 안전**: 매도 신호 없음
        6. **💪 상승 강도**: 상승폭 > 하락폭의 1.2배
        
        ### 🎓 점수별 등급
        
        - **6점 (100%)**: A+ 등급 - 완벽한 주도주 → 적극 매수
        - **5점 (83%)**: A 등급 - 우수한 주도주 → 적극 매수  
        - **4점 (67%)**: B+ 등급 - 양호한 수준 → 조건부 매수
        - **3점 (50%)**: B 등급 - 보통 수준 → 신중 검토
        - **1-2점**: C-D 등급 - 부족한 수준 → 매수 보류
        
        ### ⚠️ 중요 주의사항
        
        1. 이 점수는 **투자 참고용**이며, **최종 결정은 본인 책임**입니다.
        2. 주식은 실시간으로 변하므로 **정기적 재평가** 필요합니다.
        3. 전체 시장 하락기에는 **좋은 점수도 하락** 가능합니다.
        4. 점수가 높아도 **섹터 조심 신호** 반드시 확인하세요.
        """)

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
<p>📈 CANSLIM 주도주 분석기 | William O'Neil의 CANSLIM 투자 기법 기반</p>
<p>⚠️ 본 분석 결과는 참고용이며, 투자 결정은 본인 책임하에 이루어져야 합니다.</p>
</div>
""", unsafe_allow_html=True)

def show_market_screening():
    """시장 스크리닝 페이지"""
    st.title("🔍 CANSLIM 시장 스크리닝")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 전체 시장 스크리닝
        코스피, 코스닥, 나스닥, S&P 500의 모든 주식을 CANSLIM 기준으로 분석합니다.
        """)
    
    with col2:
        if st.button("🚀 스크리닝 실행", type="primary"):
            run_market_screening()
    
    # 최신 스크리닝 결과 표시
    display_latest_screening_results()

def run_market_screening():
    """시장 스크리닝 실행"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("스크리닝 초기화 중...")
        screener = MarketScreener()
        
        progress_bar.progress(10)
        status_text.text("시장 데이터 수집 중...")
        
        # 스크리닝 실행
        with st.spinner("전체 시장 분석 중... (수 분 소요될 수 있습니다)"):
            results = screener.run_daily_screening()
        
        progress_bar.progress(100)
        status_text.text("스크리닝 완료!")
        
        if results:
            st.success(f"✅ 스크리닝 완료! {len(results)}개 종목 분석")
            
            # 결과 미리보기
            st.subheader("상위 10개 종목")
            preview_df = pd.DataFrame(results[:10])
            if not preview_df.empty:
                display_columns = ['symbol', 'market', 'overall_score']
                if all(col in preview_df.columns for col in display_columns):
                    st.dataframe(preview_df[display_columns])
        else:
            st.warning("분석된 종목이 없습니다.")
            
    except Exception as e:
        st.error(f"스크리닝 중 오류 발생: {str(e)}")
        progress_bar.progress(0)
        status_text.text("스크리닝 실패")

def display_latest_screening_results():
    """최신 스크리닝 결과 표시"""
    st.subheader("📊 최신 스크리닝 결과")
    
    # 최신 결과 파일 찾기
    result_files = [f for f in os.listdir('.') if f.startswith('screening_results_') and f.endswith('.json')]
    
    if not result_files:
        st.info("아직 스크리닝 결과가 없습니다. 위의 '스크리닝 실행' 버튼을 클릭해주세요.")
        return
    
    # 가장 최신 파일 선택
    latest_file = sorted(result_files, reverse=True)[0]
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        if not results:
            st.warning("스크리닝 결과가 비어있습니다.")
            return
        
        # 기본 통계
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 분석 종목", len(results))
        
        with col2:
            avg_score = sum(r.get('overall_score', 0) for r in results) / len(results)
            st.metric("평균 점수", f"{avg_score:.1f}")
        
        with col3:
            high_score_count = len([r for r in results if r.get('overall_score', 0) >= 70])
            st.metric("고득점 종목 (70+)", high_score_count)
        
        with col4:
            # 분석 날짜
            analysis_date = results[0].get('analysis_date', 'Unknown')
            st.metric("분석 날짜", analysis_date)
        
        # 시장별 분포
        st.subheader("시장별 분포")
        markets = {}
        for result in results:
            market = result.get('market', 'Unknown')
            if market not in markets:
                markets[market] = []
            markets[market].append(result)
        
        market_data = []
        for market, market_results in markets.items():
            avg_score = sum(r.get('overall_score', 0) for r in market_results) / len(market_results)
            market_data.append({
                'Market': market,
                'Count': len(market_results),
                'Avg_Score': avg_score
            })
        
        market_df = pd.DataFrame(market_data)
        
        if not market_df.empty:
            fig = px.bar(market_df, x='Market', y='Count', 
                        title='시장별 분석 종목 수')
            st.plotly_chart(fig, use_container_width=True)
        
        # 상위 종목 표시
        st.subheader("🏆 상위 50개 종목")
        
        # 필터링 옵션
        col1, col2 = st.columns(2)
        
        with col1:
            selected_markets = st.multiselect(
                "시장 선택",
                options=list(markets.keys()),
                default=list(markets.keys())
            )
        
        with col2:
            min_score = st.slider("최소 점수", 0, 100, 50)
        
        # 필터 적용
        filtered_results = [
            r for r in results 
            if r.get('market') in selected_markets and r.get('overall_score', 0) >= min_score
        ]
        
        if filtered_results:
            # 데이터프레임 생성
            df_data = []
            for i, result in enumerate(filtered_results[:50], 1):
                canslim_scores = result.get('canslim_scores', {})
                df_data.append({
                    '순위': i,
                    '종목': result.get('symbol', 'N/A'),
                    '시장': result.get('market', 'N/A'),
                    '총점': result.get('overall_score', 0),
                    'C': canslim_scores.get('C', 0),
                    'A': canslim_scores.get('A', 0),
                    'N': canslim_scores.get('N', 0),
                    'S': canslim_scores.get('S', 0),
                    'L': canslim_scores.get('L', 0),
                    'I': canslim_scores.get('I', 0),
                    'M': canslim_scores.get('M', 0)
                })
            
            df = pd.DataFrame(df_data)
            
            # 색상 코딩을 위한 스타일링
            def color_score(val):
                if val >= 80:
                    return 'background-color: #d4edda'  # 초록
                elif val >= 60:
                    return 'background-color: #fff3cd'  # 노랑
                elif val >= 40:
                    return 'background-color: #f8d7da'  # 빨강
                else:
                    return ''
            
            styled_df = df.style.applymap(color_score, subset=['총점', 'C', 'A', 'N', 'S', 'L', 'I', 'M'])
            st.dataframe(styled_df, use_container_width=True, height=600)
            
            # CSV 다운로드 버튼
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv,
                file_name=f"canslim_screening_{analysis_date}.csv",
                mime="text/csv"
            )
            
        else:
            st.warning("선택한 조건에 맞는 종목이 없습니다.")
    
    except Exception as e:
        st.error(f"결과 로딩 중 오류 발생: {str(e)}")

def show_screening_history():
    """스크리닝 이력 페이지"""
    st.title("📈 스크리닝 이력")
    
    # 모든 결과 파일 찾기
    result_files = [f for f in os.listdir('.') if f.startswith('screening_results_') and f.endswith('.json')]
    
    if not result_files:
        st.info("스크리닝 이력이 없습니다.")
        return
    
    # 파일별 요약 정보
    history_data = []
    for file in sorted(result_files, reverse=True):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            if results:
                timestamp = file.replace('screening_results_', '').replace('.json', '')
                date_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[9:11]}:{timestamp[11:13]}"
                
                avg_score = sum(r.get('overall_score', 0) for r in results) / len(results)
                top_symbol = results[0].get('symbol', 'N/A') if results else 'N/A'
                top_score = results[0].get('overall_score', 0) if results else 0
                
                history_data.append({
                    '날짜': date_str,
                    '분석 종목 수': len(results),
                    '평균 점수': f"{avg_score:.1f}",
                    '최고 종목': top_symbol,
                    '최고 점수': f"{top_score:.1f}",
                    '파일명': file
                })
        except:
            continue
    
    if history_data:
        df = pd.DataFrame(history_data)
        
        # 파일 선택
        selected_file = st.selectbox(
            "분석 결과 선택",
            options=df['파일명'].tolist(),
            format_func=lambda x: df[df['파일명']==x]['날짜'].iloc[0]
        )
        
        # 선택된 파일의 상세 정보 표시
        if selected_file:
            with open(selected_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("분석 종목 수", len(results))
            
            with col2:
                avg_score = sum(r.get('overall_score', 0) for r in results) / len(results)
                st.metric("평균 점수", f"{avg_score:.1f}")
            
            with col3:
                high_score_count = len([r for r in results if r.get('overall_score', 0) >= 70])
                st.metric("고득점 종목", high_score_count)
            
            # 상위 20개 종목 표시
            st.subheader("상위 20개 종목")
            if results:
                top_20 = results[:20]
                df_data = []
                for i, result in enumerate(top_20, 1):
                    df_data.append({
                        '순위': i,
                        '종목': result.get('symbol', 'N/A'),
                        '시장': result.get('market', 'N/A'),
                        '점수': result.get('overall_score', 0)
                    })
                
                st.dataframe(pd.DataFrame(df_data), use_container_width=True)

# 메인 앱 수정
def main():
    st.set_page_config(
        page_title="CANSLIM Stock Analyzer", 
        page_icon="📈", 
        layout="wide"
    )
    
    # 사이드바 메뉴
    st.sidebar.title("📈 CANSLIM 분석 도구")
    
    menu = st.sidebar.selectbox(
        "메뉴 선택",
        ["개별 주식 분석", "시장 스크리닝", "스크리닝 이력", "CANSLIM 가이드"]
    )
    
    if menu == "개별 주식 분석":
        show_stock_analysis()
    elif menu == "시장 스크리닝":
        show_market_screening()
    elif menu == "스크리닝 이력":
        show_screening_history()
    elif menu == "CANSLIM 가이드":
        show_canslim_guide()

# ... rest of existing code ... 