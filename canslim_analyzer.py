import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# TA-Lib을 선택적으로 import
try:
    import talib as ta
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    print("TA-Lib을 찾을 수 없습니다. 기본 MACD 계산을 사용합니다.")

class CANSLIMAnalyzer:
    """
    CANSLIM 기반 주도주 선별 및 투자 조심 기준 분석기
    """
    
    def __init__(self, benchmark_symbol: str = "^KS11"):
        """
        초기화
        Args:
            benchmark_symbol: 벤치마크 지수 (기본값: 코스피 지수)
        """
        self.benchmark_symbol = benchmark_symbol
        self.benchmark_data = None
        self._load_benchmark_data()
    
    def _load_benchmark_data(self):
        """벤치마크 데이터 로드"""
        try:
            ticker = yf.Ticker(self.benchmark_symbol)
            self.benchmark_data = ticker.history(period="2y")
        except Exception as e:
            print(f"벤치마크 데이터 로드 실패: {e}")
    
    def get_stock_data(self, symbol: str, period: str = "2y") -> Optional[pd.DataFrame]:
        """
        주식 데이터 가져오기
        Args:
            symbol: 주식 심볼
            period: 기간 (1y, 2y, 5y 등)
        Returns:
            주식 데이터 DataFrame
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            return data
        except Exception as e:
            print(f"{symbol} 데이터 로드 실패: {e}")
            return None
    
    def analyze_leadership_criteria(self, symbol: str) -> Dict:
        """
        주도주 선별 기준 분석
        Args:
            symbol: 분석할 주식 심볼
        Returns:
            분석 결과 딕셔너리
        """
        data = self.get_stock_data(symbol)
        if data is None or data.empty:
            return {"error": "데이터를 가져올 수 없습니다"}
        
        results = {
            "symbol": symbol,
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "criteria": {}
        }
        
        # 1. 52주 신고가 여부
        current_price = data['Close'].iloc[-1]
        high_52w = data['High'].rolling(window=252).max().iloc[-1]
        results["criteria"]["52w_high"] = {
            "is_near_high": current_price >= high_52w * 0.95,  # 95% 이상이면 신고가 근처
            "current_price": round(current_price, 2),
            "52w_high": round(high_52w, 2),
            "distance_from_high": round((current_price / high_52w - 1) * 100, 2)
        }
        
        # 2. 시장 대비 성과 (베타와 상대강도)
        if self.benchmark_data is not None:
            beta_result = self._calculate_beta(data, self.benchmark_data)
            relative_strength = self._calculate_relative_strength(data, self.benchmark_data)
            results["criteria"]["market_performance"] = {
                "beta": round(beta_result, 2),
                "relative_strength_3m": round(relative_strength["3m"], 2),
                "relative_strength_6m": round(relative_strength["6m"], 2),
                "outperforms_market": relative_strength["6m"] > 0
            }
        
        # 3. 20주 이동평균선 지지
        ma_20 = data['Close'].rolling(window=100).mean()  # 20주 ≈ 100일
        current_above_ma20 = current_price > ma_20.iloc[-1]
        ma20_slope = self._calculate_slope(ma_20.tail(20))
        
        results["criteria"]["moving_average"] = {
            "above_20w_ma": current_above_ma20,
            "ma20_value": round(ma_20.iloc[-1], 2),
            "ma20_slope": round(ma20_slope, 4),
            "ma20_trending_up": ma20_slope > 0
        }
        
        # 4. MACD 분석 (월봉 기준)
        monthly_data = self._convert_to_monthly(data)
        macd_analysis = self._analyze_macd(monthly_data)
        results["criteria"]["macd"] = macd_analysis
        
        # 5. 가격 변동성 및 강도 분석
        volatility_analysis = self._analyze_volatility(data)
        results["criteria"]["volatility"] = volatility_analysis
        
        # 6. 종합 점수 계산
        score = self._calculate_leadership_score(results["criteria"])
        results["leadership_score"] = score
        
        return results
    
    def analyze_caution_criteria(self, symbols: List[str], sector: str = None) -> Dict:
        """
        투자 조심 기준 분석
        Args:
            symbols: 분석할 주식 심볼 리스트 (섹터 내 종목들)
            sector: 섹터명
        Returns:
            조심 기준 분석 결과
        """
        results = {
            "sector": sector,
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "caution_signals": {},
            "symbol_count": len(symbols)
        }
        
        valid_data = {}
        for symbol in symbols:
            data = self.get_stock_data(symbol)
            if data is not None and not data.empty:
                valid_data[symbol] = data
        
        if not valid_data:
            return {"error": "유효한 데이터가 없습니다"}
        
        # 1. 후진주 상승률 분석
        laggard_analysis = self._analyze_laggard_performance(valid_data)
        results["caution_signals"]["laggard_surge"] = laggard_analysis
        
        # 2. PBR 고평가 지속 분석
        pbr_analysis = self._analyze_pbr_levels(valid_data)
        results["caution_signals"]["high_pbr"] = pbr_analysis
        
        # 3. 소형주 레버리지 분석
        leverage_analysis = self._analyze_leverage_risk(valid_data)
        results["caution_signals"]["leverage_risk"] = leverage_analysis
        
        # 4. 시장 과열 지표
        market_heat = self._analyze_market_heat(valid_data)
        results["caution_signals"]["market_heat"] = market_heat
        
        # 5. 종합 조심 점수 계산
        caution_score = self._calculate_caution_score(results["caution_signals"])
        results["caution_score"] = caution_score
        results["high_caution"] = caution_score >= 5  # 5개 이상 기준 충족시
        
        return results
    
    def _calculate_beta(self, stock_data: pd.DataFrame, market_data: pd.DataFrame) -> float:
        """베타 계산"""
        try:
            # 일일 수익률 계산
            stock_returns = stock_data['Close'].pct_change().dropna()
            market_returns = market_data['Close'].pct_change().dropna()
            
            # 공통 날짜만 사용
            common_dates = stock_returns.index.intersection(market_returns.index)
            if len(common_dates) < 30:  # 최소 30일 데이터 필요
                return np.nan
            
            stock_returns = stock_returns[common_dates]
            market_returns = market_returns[common_dates]
            
            # 베타 계산
            covariance = np.cov(stock_returns, market_returns)[0][1]
            market_variance = np.var(market_returns)
            
            return covariance / market_variance if market_variance != 0 else np.nan
        except:
            return np.nan
    
    def _calculate_relative_strength(self, stock_data: pd.DataFrame, market_data: pd.DataFrame) -> Dict:
        """상대강도 계산 (3개월, 6개월)"""
        try:
            stock_close = stock_data['Close']
            market_close = market_data['Close']
            
            # 공통 날짜 찾기
            common_dates = stock_close.index.intersection(market_close.index)
            if len(common_dates) < 180:  # 최소 6개월 데이터
                return {"3m": np.nan, "6m": np.nan}
            
            stock_close = stock_close[common_dates]
            market_close = market_close[common_dates]
            
            # 3개월, 6개월 전 가격 찾기
            end_price_stock = stock_close.iloc[-1]
            end_price_market = market_close.iloc[-1]
            
            # 3개월 전 (약 63거래일)
            if len(stock_close) >= 63:
                start_3m_stock = stock_close.iloc[-63]
                start_3m_market = market_close.iloc[-63]
                stock_return_3m = (end_price_stock / start_3m_stock - 1) * 100
                market_return_3m = (end_price_market / start_3m_market - 1) * 100
                relative_strength_3m = stock_return_3m - market_return_3m
            else:
                relative_strength_3m = np.nan
            
            # 6개월 전 (약 126거래일)
            if len(stock_close) >= 126:
                start_6m_stock = stock_close.iloc[-126]
                start_6m_market = market_close.iloc[-126]
                stock_return_6m = (end_price_stock / start_6m_stock - 1) * 100
                market_return_6m = (end_price_market / start_6m_market - 1) * 100
                relative_strength_6m = stock_return_6m - market_return_6m
            else:
                relative_strength_6m = np.nan
            
            return {
                "3m": relative_strength_3m,
                "6m": relative_strength_6m
            }
        except:
            return {"3m": np.nan, "6m": np.nan}
    
    def _calculate_slope(self, series: pd.Series) -> float:
        """시계열의 기울기 계산"""
        try:
            x = np.arange(len(series))
            y = series.values
            return np.polyfit(x, y, 1)[0]
        except:
            return 0
    
    def _convert_to_monthly(self, data: pd.DataFrame) -> pd.DataFrame:
        """일봉을 월봉으로 변환"""
        monthly = data.resample('M').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        return monthly
    
    def _calculate_ema(self, data: pd.Series, span: int) -> pd.Series:
        """지수이동평균 계산 (TA-Lib 대체)"""
        return data.ewm(span=span).mean()
    
    def _calculate_macd_manual(self, close_prices: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """MACD를 수동으로 계산 (TA-Lib이 없을 때 사용)"""
        try:
            if len(close_prices) < slow_period + signal_period:
                return None, None, None
            
            # EMA 계산
            ema_fast = self._calculate_ema(close_prices, fast_period)
            ema_slow = self._calculate_ema(close_prices, slow_period)
            
            # MACD 라인 = 빠른 EMA - 느린 EMA
            macd_line = ema_fast - ema_slow
            
            # 시그널 라인 = MACD 라인의 EMA
            signal_line = self._calculate_ema(macd_line, signal_period)
            
            # 히스토그램 = MACD 라인 - 시그널 라인
            histogram = macd_line - signal_line
            
            return macd_line.values, signal_line.values, histogram.values
            
        except Exception as e:
            print(f"MACD 계산 실패: {e}")
            return None, None, None
    
    def _analyze_macd(self, data: pd.DataFrame) -> Dict:
        """MACD 분석"""
        try:
            close = data['Close']
            if len(close) < 35:  # MACD 계산을 위한 최소 데이터
                return {"error": "insufficient_data"}
            
            # MACD 계산 (TA-Lib 있으면 사용, 없으면 수동 계산)
            if HAS_TALIB:
                macd, macdsignal, macdhist = ta.MACD(close.values, fastperiod=12, slowperiod=26, signalperiod=9)
            else:
                macd, macdsignal, macdhist = self._calculate_macd_manual(close)
                
            if macd is None:
                return {"error": "calculation_failed"}
            
            # 최근 값들
            current_macd = macd[-1] if not np.isnan(macd[-1]) else None
            current_signal = macdsignal[-1] if not np.isnan(macdsignal[-1]) else None
            current_hist = macdhist[-1] if not np.isnan(macdhist[-1]) else None
            
            # 하락 반전 신호 감지 (최근 3개월)
            recent_hist = macdhist[-3:] if len(macdhist) >= 3 else macdhist
            downward_reversal = False
            if len(recent_hist) >= 2:
                # 히스토그램이 양수에서 음수로 전환되거나 계속 하락
                downward_reversal = (recent_hist[-2] > 0 and recent_hist[-1] < 0) or \
                                  (recent_hist[-1] < recent_hist[-2] < 0)
            
            return {
                "current_macd": round(current_macd, 4) if current_macd else None,
                "current_signal": round(current_signal, 4) if current_signal else None,
                "current_histogram": round(current_hist, 4) if current_hist else None,
                "downward_reversal_signal": downward_reversal,
                "sell_preparation_needed": downward_reversal
            }
        except Exception as e:
            print(f"MACD 분석 실패: {e}")
            return {"error": "calculation_failed"}
    
    def _analyze_volatility(self, data: pd.DataFrame) -> Dict:
        """변동성 및 강도 분석"""
        try:
            returns = data['Close'].pct_change().dropna()
            
            # 변동성 계산 (20일)
            volatility_20d = returns.rolling(window=20).std().iloc[-1] * np.sqrt(252)
            
            # 상승/하락 비율 (최근 20일)
            recent_returns = returns.tail(20)
            up_days = (recent_returns > 0).sum()
            down_days = (recent_returns < 0).sum()
            
            # 평균 상승폭 vs 평균 하락폭
            avg_up = recent_returns[recent_returns > 0].mean() if up_days > 0 else 0
            avg_down = recent_returns[recent_returns < 0].mean() if down_days > 0 else 0
            
            return {
                "volatility_20d": round(volatility_20d * 100, 2),
                "up_days_ratio": round(up_days / 20, 2),
                "avg_up_return": round(avg_up * 100, 2),
                "avg_down_return": round(avg_down * 100, 2),
                "strength_ratio": round(abs(avg_up / avg_down), 2) if avg_down != 0 else np.inf
            }
        except:
            return {"error": "calculation_failed"}
    
    def _analyze_laggard_performance(self, data_dict: Dict) -> Dict:
        """후진주 성과 분석"""
        try:
            performance_6m = {}
            
            for symbol, data in data_dict.items():
                if len(data) >= 126:  # 6개월 데이터
                    current_price = data['Close'].iloc[-1]
                    price_6m_ago = data['Close'].iloc[-126]
                    return_6m = (current_price / price_6m_ago - 1) * 100
                    performance_6m[symbol] = return_6m
            
            if not performance_6m:
                return {"error": "insufficient_data"}
            
            # 성과 순으로 정렬
            sorted_performance = sorted(performance_6m.items(), key=lambda x: x[1])
            
            # 하위 25% 종목들의 평균 수익률
            bottom_25_pct = int(len(sorted_performance) * 0.25)
            if bottom_25_pct == 0:
                bottom_25_pct = 1
            
            laggard_returns = [ret for _, ret in sorted_performance[:bottom_25_pct]]
            avg_laggard_return = np.mean(laggard_returns)
            
            # 후진주가 50% 이상 상승했는지 확인
            laggards_surge = avg_laggard_return >= 50
            
            return {
                "avg_laggard_return_6m": round(avg_laggard_return, 2),
                "laggard_count": len(laggard_returns),
                "laggards_surge_50pct": laggards_surge,
                "warning_signal": laggards_surge
            }
        except:
            return {"error": "calculation_failed"}
    
    def _analyze_pbr_levels(self, data_dict: Dict) -> Dict:
        """PBR 고평가 분석 (실제로는 P/E 또는 가격 수준으로 대체)"""
        try:
            # 실제 PBR 데이터가 없으므로 가격 상승률로 대체 분석
            high_valuation_count = 0
            total_count = 0
            
            for symbol, data in data_dict.items():
                if len(data) >= 126:  # 6개월 데이터
                    current_price = data['Close'].iloc[-1]
                    price_6m_ago = data['Close'].iloc[-126]
                    
                    # 52주 최고가 대비 현재가 위치
                    high_52w = data['High'].rolling(window=252).max().iloc[-1]
                    price_vs_high = current_price / high_52w
                    
                    # 높은 가격 수준 유지 (90% 이상에서 6개월)
                    if price_vs_high >= 0.9:
                        high_valuation_count += 1
                    
                    total_count += 1
            
            high_valuation_ratio = high_valuation_count / total_count if total_count > 0 else 0
            
            return {
                "high_valuation_count": high_valuation_count,
                "total_analyzed": total_count,
                "high_valuation_ratio": round(high_valuation_ratio, 2),
                "warning_signal": high_valuation_ratio >= 0.5  # 50% 이상이 고평가 상태
            }
        except:
            return {"error": "calculation_failed"}
    
    def _analyze_leverage_risk(self, data_dict: Dict) -> Dict:
        """레버리지 리스크 분석 (소형주 급등 위험)"""
        try:
            extreme_gains = 0
            total_count = 0
            
            for symbol, data in data_dict.items():
                if len(data) >= 252:  # 1년 데이터
                    current_price = data['Close'].iloc[-1]
                    price_1y_ago = data['Close'].iloc[-252]
                    return_1y = (current_price / price_1y_ago - 1) * 100
                    
                    # 1년간 1000% (10배) 이상 상승
                    if return_1y >= 1000:
                        extreme_gains += 1
                    
                    total_count += 1
            
            leverage_risk_ratio = extreme_gains / total_count if total_count > 0 else 0
            
            return {
                "extreme_gain_count": extreme_gains,
                "total_analyzed": total_count,
                "leverage_risk_ratio": round(leverage_risk_ratio, 2),
                "warning_signal": extreme_gains > 0  # 10배 이상 수익 종목 존재시
            }
        except:
            return {"error": "calculation_failed"}
    
    def _analyze_market_heat(self, data_dict: Dict) -> Dict:
        """시장 과열 지표 분석"""
        try:
            # 전체 종목의 평균 수익률 (3개월, 6개월)
            returns_3m = []
            returns_6m = []
            
            for symbol, data in data_dict.items():
                if len(data) >= 126:  # 6개월 데이터
                    current_price = data['Close'].iloc[-1]
                    
                    # 3개월 수익률
                    if len(data) >= 63:
                        price_3m_ago = data['Close'].iloc[-63]
                        return_3m = (current_price / price_3m_ago - 1) * 100
                        returns_3m.append(return_3m)
                    
                    # 6개월 수익률
                    price_6m_ago = data['Close'].iloc[-126]
                    return_6m = (current_price / price_6m_ago - 1) * 100
                    returns_6m.append(return_6m)
            
            avg_return_3m = np.mean(returns_3m) if returns_3m else 0
            avg_return_6m = np.mean(returns_6m) if returns_6m else 0
            
            # 과열 신호: 평균 수익률이 매우 높은 경우
            overheated_3m = avg_return_3m >= 30  # 3개월 30% 이상
            overheated_6m = avg_return_6m >= 50  # 6개월 50% 이상
            
            return {
                "avg_return_3m": round(avg_return_3m, 2),
                "avg_return_6m": round(avg_return_6m, 2),
                "overheated_3m": overheated_3m,
                "overheated_6m": overheated_6m,
                "warning_signal": overheated_3m or overheated_6m
            }
        except:
            return {"error": "calculation_failed"}
    
    def _calculate_leadership_score(self, criteria: Dict) -> Dict:
        """주도주 점수 계산"""
        score = 0
        max_score = 6
        
        try:
            # 1. 52주 신고가 근처 (1점)
            if criteria.get("52w_high", {}).get("is_near_high", False):
                score += 1
            
            # 2. 시장 대비 우수한 성과 (1점)
            if criteria.get("market_performance", {}).get("outperforms_market", False):
                score += 1
            
            # 3. 20주 이평선 위 거래 (1점)
            if criteria.get("moving_average", {}).get("above_20w_ma", False):
                score += 1
            
            # 4. 이평선 상승 추세 (1점)
            if criteria.get("moving_average", {}).get("ma20_trending_up", False):
                score += 1
            
            # 5. MACD 매도 신호 없음 (1점)
            macd = criteria.get("macd", {})
            if not macd.get("sell_preparation_needed", True):
                score += 1
            
            # 6. 적절한 변동성과 강도 (1점)
            volatility = criteria.get("volatility", {})
            if volatility.get("strength_ratio", 0) >= 1.2:  # 상승 강도가 하락 강도의 1.2배 이상
                score += 1
            
            return {
                "score": score,
                "max_score": max_score,
                "percentage": round((score / max_score) * 100, 1),
                "grade": self._get_grade(score, max_score)
            }
        except:
            return {"score": 0, "max_score": max_score, "percentage": 0, "grade": "F"}
    
    def _calculate_caution_score(self, signals: Dict) -> int:
        """조심 신호 점수 계산"""
        score = 0
        
        try:
            for signal_type, signal_data in signals.items():
                if isinstance(signal_data, dict) and signal_data.get("warning_signal", False):
                    score += 1
            
            return score
        except:
            return 0
    
    def _get_grade(self, score: int, max_score: int) -> str:
        """점수를 등급으로 변환"""
        percentage = (score / max_score) * 100
        
        if percentage >= 90:
            return "A+"
        elif percentage >= 80:
            return "A"
        elif percentage >= 70:
            return "B+"
        elif percentage >= 60:
            return "B"
        elif percentage >= 50:
            return "C"
        else:
            return "D"
    
    def generate_report(self, symbol: str, sector_symbols: List[str] = None) -> Dict:
        """종합 분석 리포트 생성"""
        report = {
            "symbol": symbol,
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "leadership_analysis": None,
            "caution_analysis": None,
            "recommendation": None
        }
        
        # 1. 주도주 분석
        leadership_result = self.analyze_leadership_criteria(symbol)
        report["leadership_analysis"] = leadership_result
        
        # 2. 조심 기준 분석 (섹터 정보가 있는 경우)
        if sector_symbols:
            caution_result = self.analyze_caution_criteria(sector_symbols)
            report["caution_analysis"] = caution_result
        
        # 3. 투자 추천 결정
        recommendation = self._generate_recommendation(leadership_result, report.get("caution_analysis"))
        report["recommendation"] = recommendation
        
        return report
    
    def _generate_recommendation(self, leadership: Dict, caution: Dict = None) -> Dict:
        """투자 추천 생성"""
        try:
            leadership_score = leadership.get("leadership_score", {}).get("score", 0)
            caution_score = caution.get("caution_score", 0) if caution else 0
            
            # 추천 로직
            if caution_score >= 5:
                recommendation = "매우 조심"
                reason = f"투자 조심 신호 {caution_score}개 발생"
            elif leadership_score >= 5:
                if caution_score >= 3:
                    recommendation = "조심스런 매수"
                    reason = f"주도주 특성 우수(점수: {leadership_score}/6)하나 조심 신호 {caution_score}개 존재"
                else:
                    recommendation = "적극 매수"
                    reason = f"주도주 특성 매우 우수(점수: {leadership_score}/6)"
            elif leadership_score >= 3:
                recommendation = "조건부 매수"
                reason = f"주도주 특성 보통(점수: {leadership_score}/6)"
            else:
                recommendation = "매수 보류"
                reason = f"주도주 특성 부족(점수: {leadership_score}/6)"
            
            return {
                "action": recommendation,
                "reason": reason,
                "leadership_score": leadership_score,
                "caution_score": caution_score,
                "confidence": self._calculate_confidence(leadership_score, caution_score)
            }
        except:
            return {
                "action": "분석 불가",
                "reason": "데이터 부족",
                "leadership_score": 0,
                "caution_score": 0,
                "confidence": 0
            }
    
    def _calculate_confidence(self, leadership_score: int, caution_score: int) -> int:
        """신뢰도 계산 (0-100)"""
        base_confidence = leadership_score * 15  # 최대 90점
        caution_penalty = caution_score * 10      # 조심 신호당 10점 감점
        
        confidence = max(0, min(100, base_confidence - caution_penalty))
        return confidence 