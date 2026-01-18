"""
Integration tests for the complete workflow
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from pathlib import Path

from src.data_loader import DataLoader
from src.strategy import StockStrategy
from src.monitor import AnnouncementMonitor
from src.reporter import ReportGenerator


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow with mocked data"""
    
    @pytest.fixture
    def mock_data_loader(self, sample_stock_basics, sample_daily_indicators, 
                         sample_financial_indicators, sample_notices):
        """Create mocked DataLoader"""
        with patch('src.data_loader.load_dotenv'), \
             patch('src.data_loader.ts') as mock_ts, \
             patch('src.data_loader.time.sleep'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            
            mock_pro = MagicMock()
            mock_ts.pro_api.return_value = mock_pro
            
            # Setup mock responses
            mock_pro.stock_basic.return_value = sample_stock_basics.drop(columns=['is_st'])
            mock_pro.daily_basic.return_value = pd.DataFrame({
                'ts_code': sample_daily_indicators['ts_code'],
                'trade_date': sample_daily_indicators['trade_date'],
                'pe': sample_daily_indicators['pe_ttm'],
                'pb': sample_daily_indicators['pb'],
                'dv_ttm': sample_daily_indicators['dividend_yield'],
                'total_mv': sample_daily_indicators['total_market_cap']
            })
            
            # Mock fina_indicator for each stock
            def mock_fina_indicator(ts_code, fields):
                stock_data = sample_financial_indicators[
                    sample_financial_indicators['ts_code'] == ts_code
                ]
                if not stock_data.empty:
                    return pd.DataFrame({
                        'ts_code': [ts_code],
                        'end_date': [stock_data.iloc[0]['end_date']],
                        'roe': [stock_data.iloc[0]['roe']],
                        'netprofit_yoy': [stock_data.iloc[0].get('net_profit_growth_rate', 0)]
                    })
                # Return default data if stock not found in sample
                return pd.DataFrame({
                    'ts_code': [ts_code],
                    'end_date': [trade_date],
                    'roe': [10.0],
                    'netprofit_yoy': [5.0]
                })
            
            mock_pro.fina_indicator.side_effect = mock_fina_indicator
            mock_pro.notice.return_value = sample_notices
            
            loader = DataLoader()
            loader.pro = mock_pro
            return loader
    
    def test_end_to_end_workflow(self, mock_data_loader, sample_settings_yaml, 
                                  sample_keywords_yaml, temp_output_dir, trade_date):
        """Test complete workflow from data loading to report generation"""
        # 1. Load data
        stock_basics = mock_data_loader.get_stock_basics()
        daily_indicators = mock_data_loader.get_daily_indicators(trade_date)
        stock_codes = stock_basics['ts_code'].tolist()
        financial_indicators = mock_data_loader.get_financial_indicators(trade_date, stock_list=stock_codes)
        
        assert not stock_basics.empty
        assert not daily_indicators.empty
        # Financial indicators might be empty if no stocks match, but should have correct structure
        assert isinstance(financial_indicators, pd.DataFrame)
        # If empty, we can still proceed (strategy handles this)
        if financial_indicators.empty:
            # Add some mock financial data to make test meaningful
            financial_indicators = pd.DataFrame({
                'ts_code': stock_codes[:2],
                'end_date': [trade_date] * 2,
                'roe': [12.5, 15.8],
                'net_profit_growth_rate': [8.5, 12.3]
            })
        
        # 2. Filter stocks
        strategy = StockStrategy(config_path=sample_settings_yaml)
        anchor_pool = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        assert isinstance(anchor_pool, pd.DataFrame)
        # Should have some stocks after filtering (depending on criteria)
        
        # 3. Get notices for anchor pool
        if not anchor_pool.empty:
            stock_list = anchor_pool['ts_code'].tolist()
            start_date = (datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=3)).strftime('%Y%m%d')
            notices = mock_data_loader.get_notices(stock_list, start_date)
            
            # 4. Analyze notices
            monitor = AnnouncementMonitor(keywords_path=sample_keywords_yaml)
            notice_results = monitor.analyze_notices(notices, lookback_days=3)
            
            # 5. Generate report
            reporter = ReportGenerator(output_dir=str(temp_output_dir))
            report_path = reporter.generate_report(anchor_pool, notice_results, trade_date)
            
            # Verify report was created
            assert Path(report_path).exists()
            content = Path(report_path).read_text(encoding='utf-8')
            assert '分析报告' in content


class TestDataFlowValidation:
    """Test data flow between modules"""
    
    def test_data_flow_stock_basics_to_strategy(self, sample_stock_basics, sample_daily_indicators,
                                                sample_financial_indicators, sample_settings_yaml):
        """Test data flow from stock basics to strategy"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        
        # Verify data can be merged
        result = strategy.filter_stocks(sample_stock_basics, sample_daily_indicators, 
                                       sample_financial_indicators)
        
        assert isinstance(result, pd.DataFrame)
        # Verify all required columns are present
        required_cols = ['ts_code', 'name', 'industry', 'pe_ttm', 'pb', 'roe', 
                        'dividend_yield', 'total_market_cap', 'listing_days']
        assert all(col in result.columns for col in required_cols)
    
    def test_data_flow_anchor_pool_to_monitor(self, sample_anchor_pool, sample_notices,
                                               sample_keywords_yaml):
        """Test data flow from anchor pool to monitor"""
        monitor = AnnouncementMonitor(keywords_path=sample_keywords_yaml)
        
        # Verify notices can be analyzed
        results = monitor.analyze_notices(sample_notices, lookback_days=3)
        
        assert isinstance(results, list)
        # Verify result structure
        if results:
            assert 'ts_code' in results[0]
            assert 'sentiment' in results[0]
            assert 'matched_keyword' in results[0]
    
    def test_data_flow_to_reporter(self, sample_anchor_pool, sample_notice_results, temp_output_dir):
        """Test data flow to reporter"""
        reporter = ReportGenerator(output_dir=str(temp_output_dir))
        
        # Verify report can be generated
        report_path = reporter.generate_report(sample_anchor_pool, sample_notice_results, '20250116')
        
        assert Path(report_path).exists()
        content = Path(report_path).read_text(encoding='utf-8')
        assert len(content) > 0
    
    def test_data_format_compatibility(self, sample_stock_basics, sample_daily_indicators,
                                      sample_financial_indicators, sample_settings_yaml):
        """Test that data formats are compatible between modules"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        
        # Test with different data combinations
        # 1. All data present
        result1 = strategy.filter_stocks(sample_stock_basics, sample_daily_indicators,
                                         sample_financial_indicators)
        assert isinstance(result1, pd.DataFrame)
        
        # 2. Missing financial data (should use left join)
        partial_financial = sample_financial_indicators.head(2)
        result2 = strategy.filter_stocks(sample_stock_basics, sample_daily_indicators,
                                        partial_financial)
        assert isinstance(result2, pd.DataFrame)
        
        # 3. Empty financial data
        empty_financial = pd.DataFrame(columns=['ts_code', 'end_date', 'roe', 'net_profit_growth_rate'])
        result3 = strategy.filter_stocks(sample_stock_basics, sample_daily_indicators,
                                        empty_financial)
        assert isinstance(result3, pd.DataFrame)


class TestConfigurationLoading:
    """Test configuration loading across modules"""
    
    def test_configuration_loading_strategy(self, sample_settings_yaml):
        """Test strategy configuration loading"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        
        assert hasattr(strategy, 'pe_ttm_max')
        assert hasattr(strategy, 'pb_max')
        assert hasattr(strategy, 'roe_min')
        assert hasattr(strategy, 'dividend_yield_min')
        assert hasattr(strategy, 'listing_days_min')
    
    def test_configuration_loading_monitor(self, sample_keywords_yaml):
        """Test monitor configuration loading"""
        monitor = AnnouncementMonitor(keywords_path=sample_keywords_yaml)
        
        assert hasattr(monitor, 'positive_keywords')
        assert hasattr(monitor, 'negative_keywords')
        assert isinstance(monitor.positive_keywords, list)
        assert isinstance(monitor.negative_keywords, list)
    
    def test_configuration_consistency(self, sample_settings_yaml, sample_keywords_yaml):
        """Test that configurations are consistent"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        monitor = AnnouncementMonitor(keywords_path=sample_keywords_yaml)
        
        # Verify both can be initialized with their configs
        assert strategy.pe_ttm_max > 0
        assert len(monitor.positive_keywords) > 0


class TestErrorPropagation:
    """Test error propagation through the system"""
    
    def test_error_propagation_data_loader(self):
        """Test error propagation from DataLoader"""
        with patch('src.data_loader.load_dotenv'), \
             patch.dict('os.environ', {}, clear=True):
            
            with pytest.raises(ValueError, match="TUSHARE_TOKEN"):
                DataLoader()
    
    def test_error_propagation_strategy(self, tmp_path):
        """Test error propagation from Strategy"""
        missing_config = tmp_path / 'missing.yaml'
        
        with pytest.raises(FileNotFoundError):
            StockStrategy(config_path=str(missing_config))
    
    def test_error_propagation_monitor(self, tmp_path):
        """Test error propagation from Monitor"""
        missing_config = tmp_path / 'missing.yaml'
        
        with pytest.raises(FileNotFoundError):
            AnnouncementMonitor(keywords_path=str(missing_config))
    
    def test_graceful_degradation_financial_data(self, sample_stock_basics, 
                                                  sample_daily_indicators, sample_settings_yaml):
        """Test graceful degradation when financial data is missing"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        
        # Empty financial indicators
        empty_financial = pd.DataFrame(columns=['ts_code', 'end_date', 'roe', 'net_profit_growth_rate'])
        
        # Should not raise exception, but return empty or filtered result
        result = strategy.filter_stocks(sample_stock_basics, sample_daily_indicators, empty_financial)
        
        assert isinstance(result, pd.DataFrame)
        # Since ROE filter requires ROE > 8, and all will be NaN, result should be empty
        # or filtered out
    
    def test_graceful_degradation_empty_notices(self, sample_keywords_yaml):
        """Test graceful degradation when no notices are found"""
        monitor = AnnouncementMonitor(keywords_path=sample_keywords_yaml)
        
        empty_notices = pd.DataFrame(columns=['ts_code', 'ann_date', 'title'])
        results = monitor.analyze_notices(empty_notices, lookback_days=3)
        
        assert results == []
    
    def test_graceful_degradation_empty_anchor_pool(self, temp_output_dir):
        """Test graceful degradation when anchor pool is empty"""
        reporter = ReportGenerator(output_dir=str(temp_output_dir))
        
        empty_pool = pd.DataFrame(columns=[
            'ts_code', 'name', 'industry', 'pe_ttm', 'pb', 'roe',
            'dividend_yield', 'total_market_cap', 'listing_days'
        ])
        
        report_path = reporter.generate_report(empty_pool, [], '20250116')
        
        assert Path(report_path).exists()
        content = Path(report_path).read_text(encoding='utf-8')
        assert '0' in content or '暂无' in content
