"""
Tests for DataLoader module
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch, call
import os
from src.data_loader import DataLoader


class TestDataLoaderInit:
    """Test DataLoader initialization"""
    
    @patch('src.data_loader.load_dotenv')
    @patch('src.data_loader.ts')
    @patch.dict(os.environ, {'TUSHARE_TOKEN': 'test_token_12345'})
    def test_init_with_valid_token(self, mock_ts, mock_load_dotenv):
        """Test initialization with valid token"""
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        
        loader = DataLoader()
        
        mock_load_dotenv.assert_called_once()
        mock_ts.set_token.assert_called_once_with('test_token_12345')
        mock_ts.pro_api.assert_called_once()
        assert loader.pro == mock_pro
    
    @patch('src.data_loader.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_token(self, mock_load_dotenv):
        """Test initialization without token raises error"""
        with pytest.raises(ValueError, match="TUSHARE_TOKEN not found"):
            DataLoader()


class TestGetStockBasics:
    """Test get_stock_basics method"""
    
    @pytest.fixture
    def loader(self, mock_tushare_pro):
        """Create DataLoader with mocked Tushare Pro"""
        with patch('src.data_loader.load_dotenv'), \
             patch('src.data_loader.ts') as mock_ts, \
             patch.dict(os.environ, {'TUSHARE_TOKEN': 'test_token'}):
            mock_ts.pro_api.return_value = mock_tushare_pro
            return DataLoader()
    
    def test_get_stock_basics(self, loader, mock_tushare_pro, sample_stock_basics):
        """Test getting stock basics"""
        # Mock API response (without is_st column, it will be added)
        mock_response = sample_stock_basics.drop(columns=['is_st']).copy()
        mock_tushare_pro.stock_basic.return_value = mock_response
        
        result = loader.get_stock_basics()
        
        mock_tushare_pro.stock_basic.assert_called_once_with(
            exchange='',
            list_status='L',
            fields='ts_code,symbol,name,area,industry,list_date,is_hs'
        )
        assert isinstance(result, pd.DataFrame)
        assert 'is_st' in result.columns
        assert len(result) == len(mock_response)
    
    def test_get_stock_basics_st_detection(self, loader, mock_tushare_pro):
        """Test ST stock detection"""
        mock_response = pd.DataFrame({
            'ts_code': ['000001.SZ', 'ST0001.SZ', '*ST001.SZ'],
            'name': ['平安银行', 'ST测试', '*ST测试'],
            'symbol': ['000001', '000001', '000001'],
            'area': ['深圳'] * 3,
            'industry': ['银行'] * 3,
            'list_date': ['19910403'] * 3,
            'is_hs': ['N'] * 3
        })
        mock_tushare_pro.stock_basic.return_value = mock_response
        
        result = loader.get_stock_basics()
        
        # Check ST detection
        assert result.loc[result['ts_code'] == '000001.SZ', 'is_st'].iloc[0] == False
        assert result.loc[result['ts_code'] == 'ST0001.SZ', 'is_st'].iloc[0] == True
        assert result.loc[result['ts_code'] == '*ST001.SZ', 'is_st'].iloc[0] == True
    
    def test_get_stock_basics_api_error(self, loader, mock_tushare_pro):
        """Test API error handling"""
        mock_tushare_pro.stock_basic.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            loader.get_stock_basics()


class TestGetDailyIndicators:
    """Test get_daily_indicators method"""
    
    @pytest.fixture
    def loader(self, mock_tushare_pro):
        """Create DataLoader with mocked Tushare Pro"""
        with patch('src.data_loader.load_dotenv'), \
             patch('src.data_loader.ts') as mock_ts, \
             patch.dict(os.environ, {'TUSHARE_TOKEN': 'test_token'}):
            mock_ts.pro_api.return_value = mock_tushare_pro
            return DataLoader()
    
    def test_get_daily_indicators(self, loader, mock_tushare_pro, sample_daily_indicators, trade_date):
        """Test getting daily indicators"""
        # Mock API response with original column names
        mock_response = pd.DataFrame({
            'ts_code': sample_daily_indicators['ts_code'],
            'trade_date': sample_daily_indicators['trade_date'],
            'pe': sample_daily_indicators['pe_ttm'],
            'pb': sample_daily_indicators['pb'],
            'dv_ttm': sample_daily_indicators['dividend_yield'],
            'total_mv': sample_daily_indicators['total_market_cap']
        })
        mock_tushare_pro.daily_basic.return_value = mock_response
        
        result = loader.get_daily_indicators(trade_date)
        
        mock_tushare_pro.daily_basic.assert_called_once_with(
            trade_date=trade_date,
            fields='ts_code,trade_date,pe,pb,dv_ttm,total_mv'
        )
        assert isinstance(result, pd.DataFrame)
        assert 'pe_ttm' in result.columns
        assert 'pb' in result.columns
        assert 'dividend_yield' in result.columns
        assert 'total_market_cap' in result.columns
        assert len(result) == len(mock_response)
    
    def test_get_daily_indicators_invalid_date(self, loader, mock_tushare_pro):
        """Test handling invalid date"""
        mock_tushare_pro.daily_basic.side_effect = Exception("Invalid date")
        
        with pytest.raises(Exception):
            loader.get_daily_indicators('20250101')


class TestGetFinancialIndicators:
    """Test get_financial_indicators method"""
    
    @pytest.fixture
    def loader(self, mock_tushare_pro):
        """Create DataLoader with mocked Tushare Pro"""
        with patch('src.data_loader.load_dotenv'), \
             patch('src.data_loader.ts') as mock_ts, \
             patch('src.data_loader.time.sleep'), \
             patch.dict(os.environ, {'TUSHARE_TOKEN': 'test_token'}):
            mock_ts.pro_api.return_value = mock_tushare_pro
            return DataLoader()
    
    def test_get_financial_indicators_with_stock_list(self, loader, mock_tushare_pro, 
                                                       sample_financial_indicators, trade_date):
        """Test getting financial indicators with stock list"""
        stock_list = ['000001.SZ', '000002.SZ']
        
        # Mock API responses for each stock
        mock_responses = []
        for ts_code in stock_list:
            mock_df = pd.DataFrame({
                'ts_code': [ts_code],
                'end_date': [trade_date],
                'roe': [12.5],
                'netprofit_yoy': [8.5]
            })
            mock_responses.append(mock_df)
        
        mock_tushare_pro.fina_indicator.side_effect = mock_responses
        
        result = loader.get_financial_indicators(trade_date, stock_list=stock_list)
        
        # Verify API was called for each stock
        assert mock_tushare_pro.fina_indicator.call_count == len(stock_list)
        assert isinstance(result, pd.DataFrame)
        assert 'ts_code' in result.columns
        assert 'roe' in result.columns
        assert 'net_profit_growth_rate' in result.columns
    
    def test_get_financial_indicators_batch(self, loader, mock_tushare_pro, trade_date):
        """Test batch processing of financial indicators"""
        stock_list = [f'{i:06d}.SZ' for i in range(150)]  # 150 stocks
        
        # Mock API responses
        def mock_fina_indicator(ts_code, fields):
            return pd.DataFrame({
                'ts_code': [ts_code],
                'end_date': [trade_date],
                'roe': [10.0],
                'netprofit_yoy': [5.0]
            })
        
        mock_tushare_pro.fina_indicator.side_effect = mock_fina_indicator
        
        result = loader.get_financial_indicators(trade_date, stock_list=stock_list)
        
        # Verify all stocks were processed
        assert mock_tushare_pro.fina_indicator.call_count == len(stock_list)
        assert len(result) == len(stock_list)
    
    def test_get_financial_indicators_without_stock_list(self, loader, mock_tushare_pro, 
                                                          sample_stock_basics, trade_date):
        """Test getting financial indicators without stock list (should fetch stock list first)"""
        # Mock get_stock_basics
        mock_stock_basics = sample_stock_basics.drop(columns=['is_st'])
        mock_tushare_pro.stock_basic.return_value = mock_stock_basics
        
        # Mock fina_indicator responses
        def mock_fina_indicator(ts_code, fields):
            return pd.DataFrame({
                'ts_code': [ts_code],
                'end_date': [trade_date],
                'roe': [10.0],
                'netprofit_yoy': [5.0]
            })
        
        mock_tushare_pro.fina_indicator.side_effect = mock_fina_indicator
        
        result = loader.get_financial_indicators(trade_date, stock_list=None)
        
        # Verify stock_basic was called first
        mock_tushare_pro.stock_basic.assert_called()
        assert isinstance(result, pd.DataFrame)
    
    def test_get_financial_indicators_api_error(self, loader, mock_tushare_pro, trade_date):
        """Test handling API errors in financial indicators"""
        stock_list = ['000001.SZ']
        mock_tushare_pro.fina_indicator.side_effect = Exception("API Error")
        
        # Should return empty DataFrame instead of raising exception
        result = loader.get_financial_indicators(trade_date, stock_list=stock_list)
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert list(result.columns) == ['ts_code', 'end_date', 'roe', 'net_profit_growth_rate']
    
    def test_get_financial_indicators_date_filtering(self, loader, mock_tushare_pro, trade_date):
        """Test date filtering in financial indicators"""
        stock_list = ['000001.SZ']
        
        # Create dates: one within range, one outside
        from datetime import datetime, timedelta
        trade_dt = datetime.strptime(trade_date, '%Y%m%d')
        within_range = trade_dt.strftime('%Y%m%d')
        outside_range = (trade_dt - timedelta(days=400)).strftime('%Y%m%d')
        
        mock_response = pd.DataFrame({
            'ts_code': ['000001.SZ', '000001.SZ'],
            'end_date': [within_range, outside_range],
            'roe': [12.5, 10.0],
            'netprofit_yoy': [8.5, 5.0]
        })
        mock_tushare_pro.fina_indicator.return_value = mock_response
        
        result = loader.get_financial_indicators(trade_date, stock_list=stock_list)
        
        # Should only include data within date range
        assert len(result) == 1
        assert result.iloc[0]['end_date'] == within_range


class TestGetNotices:
    """Test get_notices method"""
    
    @pytest.fixture
    def loader(self, mock_tushare_pro):
        """Create DataLoader with mocked Tushare Pro"""
        with patch('src.data_loader.load_dotenv'), \
             patch('src.data_loader.ts') as mock_ts, \
             patch('src.data_loader.time.sleep'), \
             patch('src.data_loader.datetime') as mock_datetime, \
             patch.dict(os.environ, {'TUSHARE_TOKEN': 'test_token'}):
            from datetime import datetime
            mock_datetime.now.return_value.strftime.return_value = '20250116'
            mock_ts.pro_api.return_value = mock_tushare_pro
            return DataLoader()
    
    def test_get_notices(self, loader, mock_tushare_pro, sample_notices):
        """Test getting notices"""
        stock_list = ['000001.SZ', '000002.SZ']
        start_date = '20250113'
        
        # Mock API responses
        mock_responses = []
        for ts_code in stock_list:
            mock_df = sample_notices[sample_notices['ts_code'] == ts_code].copy()
            if not mock_df.empty:
                mock_responses.append(mock_df)
        
        mock_tushare_pro.notice.side_effect = mock_responses
        
        result = loader.get_notices(stock_list, start_date)
        
        assert isinstance(result, pd.DataFrame)
        assert 'ts_code' in result.columns
        assert 'ann_date' in result.columns
        assert 'title' in result.columns
    
    def test_get_notices_empty_list(self, loader, mock_tushare_pro):
        """Test getting notices with empty stock list"""
        result = loader.get_notices([], '20250113')
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert list(result.columns) == ['ts_code', 'ann_date', 'title']
    
    def test_get_notices_api_error(self, loader, mock_tushare_pro):
        """Test handling API errors in notices"""
        stock_list = ['000001.SZ']
        mock_tushare_pro.notice.side_effect = Exception("API Error")
        
        # Should continue processing other stocks
        result = loader.get_notices(stock_list, '20250113')
        
        assert isinstance(result, pd.DataFrame)
        # Result might be empty if all requests fail
        assert 'ts_code' in result.columns


class TestAPIErrorHandling:
    """Test general API error handling"""
    
    @pytest.fixture
    def loader(self, mock_tushare_pro):
        """Create DataLoader with mocked Tushare Pro"""
        with patch('src.data_loader.load_dotenv'), \
             patch('src.data_loader.ts') as mock_ts, \
             patch.dict(os.environ, {'TUSHARE_TOKEN': 'test_token'}):
            mock_ts.pro_api.return_value = mock_tushare_pro
            return DataLoader()
    
    def test_api_error_propagation(self, loader, mock_tushare_pro):
        """Test that API errors are properly propagated"""
        mock_tushare_pro.stock_basic.side_effect = Exception("Network Error")
        
        with pytest.raises(Exception):
            loader.get_stock_basics()
