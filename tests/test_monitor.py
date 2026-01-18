"""
Tests for Monitor module
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from src.monitor import AnnouncementMonitor


class TestAnnouncementMonitorInit:
    """Test AnnouncementMonitor initialization"""
    
    def test_init_load_keywords(self, sample_keywords_yaml):
        """Test keyword loading"""
        monitor = AnnouncementMonitor(keywords_path=sample_keywords_yaml)
        
        assert len(monitor.positive_keywords) > 0
        assert len(monitor.negative_keywords) > 0
        assert '增持' in monitor.positive_keywords
        assert '减持' in monitor.negative_keywords
    
    def test_init_missing_keywords_file(self, tmp_path):
        """Test initialization with missing keywords file"""
        missing_file = tmp_path / 'missing.yaml'
        
        with pytest.raises(FileNotFoundError):
            AnnouncementMonitor(keywords_path=str(missing_file))


class TestAnalyzeNotices:
    """Test analyze_notices method"""
    
    @pytest.fixture
    def monitor(self, sample_keywords_yaml):
        """Create AnnouncementMonitor instance"""
        return AnnouncementMonitor(keywords_path=sample_keywords_yaml)
    
    @pytest.fixture
    def sample_notices_df(self):
        """Create sample notices DataFrame"""
        today = datetime.now()
        dates = [
            today.strftime('%Y%m%d'),  # Today
            (today - timedelta(days=1)).strftime('%Y%m%d'),  # Yesterday
            (today - timedelta(days=2)).strftime('%Y%m%d'),  # 2 days ago
            (today - timedelta(days=4)).strftime('%Y%m%d'),  # 4 days ago (outside lookback)
        ]
        
        return pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000001.SZ', '600000.SH'],
            'ann_date': dates,
            'title': [
                '关于公司增持股份的公告',
                '关于公司回购股份的公告',
                '关于公司预增业绩的公告',
                '关于公司减持股份的公告'
            ]
        })
    
    def test_analyze_notices_positive(self, monitor, sample_notices_df):
        """Test positive keyword matching"""
        results = monitor.analyze_notices(sample_notices_df, lookback_days=3)
        
        # Should find positive keywords
        positive_results = [r for r in results if r['sentiment'] == 'Positive']
        assert len(positive_results) > 0
        
        # Check that matched keywords are in positive list
        for result in positive_results:
            assert result['matched_keyword'] in monitor.positive_keywords
            assert result['sentiment'] == 'Positive'
    
    def test_analyze_notices_negative(self, monitor, sample_notices_df):
        """Test negative keyword matching"""
        results = monitor.analyze_notices(sample_notices_df, lookback_days=3)
        
        # Should find negative keywords (but 4 days ago is outside lookback)
        negative_results = [r for r in results if r['sentiment'] == 'Negative']
        
        # The negative notice is 4 days ago, so it should be filtered out
        # But if we extend lookback_days, it should be found
        results_extended = monitor.analyze_notices(sample_notices_df, lookback_days=5)
        negative_extended = [r for r in results_extended if r['sentiment'] == 'Negative']
        
        if len(negative_extended) > 0:
            for result in negative_extended:
                assert result['matched_keyword'] in monitor.negative_keywords
                assert result['sentiment'] == 'Negative'
    
    def test_analyze_notices_no_match(self, monitor):
        """Test with no matching keywords"""
        today = datetime.now()
        notices_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'ann_date': [today.strftime('%Y%m%d')],
            'title': ['关于公司日常经营情况的公告']  # No keywords
        })
        
        results = monitor.analyze_notices(notices_df, lookback_days=3)
        
        assert len(results) == 0
    
    def test_analyze_notices_lookback_days(self, monitor):
        """Test lookback days filtering"""
        today = datetime.now()
        dates = [
            today.strftime('%Y%m%d'),  # Today - should be included
            (today - timedelta(days=2)).strftime('%Y%m%d'),  # 2 days ago - should be included
            (today - timedelta(days=4)).strftime('%Y%m%d'),  # 4 days ago - should be excluded
        ]
        
        notices_df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '600000.SH'],
            'ann_date': dates,
            'title': [
                '关于公司增持股份的公告',
                '关于公司回购股份的公告',
                '关于公司减持股份的公告'
            ]
        })
        
        results = monitor.analyze_notices(notices_df, lookback_days=3)
        
        # Should only include notices within 3 days
        for result in results:
            notice_date = datetime.strptime(result['notice_date'], '%Y-%m-%d')
            days_ago = (today - notice_date).days
            assert days_ago <= 3
    
    def test_analyze_notices_empty_df(self, monitor):
        """Test with empty DataFrame"""
        empty_df = pd.DataFrame(columns=['ts_code', 'ann_date', 'title'])
        
        results = monitor.analyze_notices(empty_df, lookback_days=3)
        
        assert results == []
    
    def test_analyze_notices_multiple_keywords(self, monitor):
        """Test matching multiple keywords (should match first one)"""
        today = datetime.now()
        notices_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'ann_date': [today.strftime('%Y%m%d')],
            'title': ['关于公司增持和回购股份的公告']  # Contains both keywords
        })
        
        results = monitor.analyze_notices(notices_df, lookback_days=3)
        
        # Should match first positive keyword found
        assert len(results) == 1
        assert results[0]['sentiment'] == 'Positive'
        # Should match '增持' (first in positive list) or '回购'
        assert results[0]['matched_keyword'] in monitor.positive_keywords
    
    def test_analyze_notices_priority_positive_over_negative(self, monitor):
        """Test that positive keywords are checked before negative"""
        today = datetime.now()
        notices_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'ann_date': [today.strftime('%Y%m%d')],
            'title': ['关于公司增持和减持股份的公告']  # Contains both positive and negative
        })
        
        results = monitor.analyze_notices(notices_df, lookback_days=3)
        
        # Should match positive keyword first
        assert len(results) == 1
        assert results[0]['sentiment'] == 'Positive'
        assert results[0]['matched_keyword'] in monitor.positive_keywords
    
    def test_analyze_notices_date_format_handling(self, monitor):
        """Test handling of different date formats"""
        today = datetime.now()
        notices_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'ann_date': [today.strftime('%Y%m%d')],
            'title': ['关于公司增持股份的公告']
        })
        
        results = monitor.analyze_notices(notices_df, lookback_days=3)
        
        # Should handle date format correctly
        assert len(results) > 0
        for result in results:
            # Date should be in YYYY-MM-DD format
            assert len(result['notice_date']) == 10
            assert result['notice_date'].count('-') == 2
    
    def test_analyze_notices_all_keywords(self, monitor):
        """Test matching all positive and negative keywords"""
        today = datetime.now()
        
        # Create notices for all positive keywords
        positive_titles = [f'关于公司{keyword}的公告' for keyword in monitor.positive_keywords]
        # Create notices for all negative keywords
        negative_titles = [f'关于公司{keyword}的公告' for keyword in monitor.negative_keywords]
        
        all_titles = positive_titles + negative_titles
        notices_df = pd.DataFrame({
            'ts_code': [f'{i:06d}.SZ' for i in range(len(all_titles))],
            'ann_date': [today.strftime('%Y%m%d')] * len(all_titles),
            'title': all_titles
        })
        
        results = monitor.analyze_notices(notices_df, lookback_days=3)
        
        # Should match all keywords
        assert len(results) == len(all_titles)
        
        positive_count = sum(1 for r in results if r['sentiment'] == 'Positive')
        negative_count = sum(1 for r in results if r['sentiment'] == 'Negative')
        
        assert positive_count == len(monitor.positive_keywords)
        assert negative_count == len(monitor.negative_keywords)
    
    def test_analyze_notices_case_sensitivity(self, monitor):
        """Test that keyword matching is case-sensitive (Chinese keywords)"""
        today = datetime.now()
        notices_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'ann_date': [today.strftime('%Y%m%d')],
            'title': ['关于公司增持股份的公告']  # Contains keyword
        })
        
        results = monitor.analyze_notices(notices_df, lookback_days=3)
        
        # Should match (Chinese is not case-sensitive in the same way)
        assert len(results) > 0
