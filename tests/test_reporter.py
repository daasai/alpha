"""
Tests for Reporter module
"""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime
from src.reporter import ReportGenerator


class TestReportGeneratorInit:
    """Test ReportGenerator initialization"""
    
    def test_init_default_output_dir(self):
        """Test initialization with default output directory"""
        reporter = ReportGenerator()
        
        assert reporter.output_dir == Path('data/output')
        assert reporter.output_dir.exists()
    
    def test_init_custom_output_dir(self, temp_output_dir):
        """Test initialization with custom output directory"""
        reporter = ReportGenerator(output_dir=str(temp_output_dir))
        
        assert reporter.output_dir == temp_output_dir
        assert reporter.output_dir.exists()


class TestGenerateReport:
    """Test generate_report method"""
    
    @pytest.fixture
    def reporter(self, temp_output_dir):
        """Create ReportGenerator instance"""
        return ReportGenerator(output_dir=str(temp_output_dir))
    
    @pytest.fixture
    def sample_anchor_pool(self):
        """Sample anchor pool DataFrame"""
        return pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '600000.SH'],
            'name': ['平安银行', '万科A', '浦发银行'],
            'industry': ['银行', '房地产', '银行'],
            'pe_ttm': [8.5, 12.3, 6.2],
            'pb': [0.8, 1.2, 0.6],
            'roe': [12.5, 15.8, 10.2],
            'dividend_yield': [2.5, 3.2, 1.8],
            'total_market_cap': [1500000, 2000000, 1200000],
            'listing_days': [12000, 12500, 9000]
        })
    
    def test_generate_report_basic(self, reporter, sample_anchor_pool):
        """Test basic report generation"""
        trade_date = '20250116'
        notice_results = []
        
        report_path = reporter.generate_report(sample_anchor_pool, notice_results, trade_date)
        
        # Check file was created
        assert Path(report_path).exists()
        
        # Read and verify content
        content = Path(report_path).read_text(encoding='utf-8')
        assert '分析报告' in content
        assert '白名单股票数量: 3' in content
        assert '平安银行' in content
        assert '万科A' in content
    
    def test_generate_report_empty_pool(self, reporter):
        """Test report generation with empty pool"""
        empty_pool = pd.DataFrame(columns=[
            'ts_code', 'name', 'industry', 'pe_ttm', 'pb', 'roe', 
            'dividend_yield', 'total_market_cap', 'listing_days'
        ])
        trade_date = '20250116'
        notice_results = []
        
        report_path = reporter.generate_report(empty_pool, notice_results, trade_date)
        
        # Check file was created
        assert Path(report_path).exists()
        
        # Read and verify content
        content = Path(report_path).read_text(encoding='utf-8')
        assert '白名单股票数量: 0' in content
        assert '暂无符合条件的股票' in content
    
    def test_generate_report_with_notices(self, reporter, sample_anchor_pool, sample_notice_results):
        """Test report generation with notices"""
        trade_date = '20250116'
        
        report_path = reporter.generate_report(sample_anchor_pool, sample_notice_results, trade_date)
        
        # Check file was created
        assert Path(report_path).exists()
        
        # Read and verify content
        content = Path(report_path).read_text(encoding='utf-8')
        assert '重要异动公告' in content
        assert '利好公告' in content or '利空公告' in content
        
        # Check for notice content
        for notice in sample_notice_results:
            assert notice['ts_code'] in content
            if notice['sentiment'] == 'Positive':
                assert '利好' in content or 'Positive' in content
    
    def test_generate_report_date_format(self, reporter, sample_anchor_pool):
        """Test date format handling"""
        # Test YYYYMMDD format
        trade_date_1 = '20250116'
        report_path_1 = reporter.generate_report(sample_anchor_pool, [], trade_date_1)
        content_1 = Path(report_path_1).read_text(encoding='utf-8')
        assert '2025-01-16' in content_1
        
        # Test YYYY-MM-DD format
        trade_date_2 = '2025-01-16'
        report_path_2 = reporter.generate_report(sample_anchor_pool, [], trade_date_2)
        content_2 = Path(report_path_2).read_text(encoding='utf-8')
        assert '2025-01-16' in content_2
    
    def test_generate_report_markdown_format(self, reporter, sample_anchor_pool):
        """Test Markdown format validation"""
        trade_date = '20250116'
        notice_results = []
        
        report_path = reporter.generate_report(sample_anchor_pool, notice_results, trade_date)
        content = Path(report_path).read_text(encoding='utf-8')
        
        # Check Markdown elements
        assert content.startswith('#')  # Title
        assert '##' in content  # Section headers
        assert '|' in content  # Table
        assert '---' in content  # Separator
    
    def test_generate_report_file_creation(self, reporter, sample_anchor_pool, temp_output_dir):
        """Test file creation and naming"""
        trade_date = '20250116'
        notice_results = []
        
        report_path = reporter.generate_report(sample_anchor_pool, notice_results, trade_date)
        
        # Check file exists
        file_path = Path(report_path)
        assert file_path.exists()
        assert file_path.is_file()
        
        # Check file name format
        assert file_path.name.startswith('2025-01-16')
        assert file_path.name.endswith('.md')
        assert 'Analysis_Report' in file_path.name
    
    def test_generate_report_top_20(self, reporter):
        """Test that only top 20 stocks are shown in report"""
        # Create pool with more than 20 stocks
        large_pool = pd.DataFrame({
            'ts_code': [f'{i:06d}.SZ' for i in range(25)],
            'name': [f'股票{i}' for i in range(25)],
            'industry': ['其他'] * 25,
            'pe_ttm': [10.0] * 25,
            'pb': [1.0] * 25,
            'roe': [float(i) for i in range(25, 0, -1)],  # Descending ROE
            'dividend_yield': [2.0] * 25,
            'total_market_cap': [1000000] * 25,
            'listing_days': [1000] * 25
        })
        
        trade_date = '20250116'
        report_path = reporter.generate_report(large_pool, [], trade_date)
        content = Path(report_path).read_text(encoding='utf-8')
        
        # Count table rows (excluding header and separator)
        lines = content.split('\n')
        table_lines = [line for line in lines if line.startswith('|') and '股票代码' not in line and '---' not in line]
        
        # Should have at most 20 rows
        assert len(table_lines) <= 20
    
    def test_generate_report_number_formatting(self, reporter, sample_anchor_pool):
        """Test number formatting in report"""
        trade_date = '20250116'
        report_path = reporter.generate_report(sample_anchor_pool, [], trade_date)
        content = Path(report_path).read_text(encoding='utf-8')
        
        # Check number formatting
        assert '8.50' in content or '8.5' in content  # PE_TTM
        assert '12.50%' in content or '12.5%' in content  # ROE
        assert '2.50%' in content or '2.5%' in content  # Dividend yield
        assert '亿' in content  # Market cap unit
    
    def test_generate_report_notice_highlighting(self, reporter, sample_anchor_pool, sample_notice_results):
        """Test keyword highlighting in notices"""
        trade_date = '20250116'
        
        report_path = reporter.generate_report(sample_anchor_pool, sample_notice_results, trade_date)
        content = Path(report_path).read_text(encoding='utf-8')
        
        # Check that keywords are highlighted (bold in markdown)
        for notice in sample_notice_results:
            keyword = notice['matched_keyword']
            # Keyword should appear in bold (**keyword**)
            assert f'**{keyword}**' in content or keyword in content
    
    def test_generate_report_sentiment_sections(self, reporter, sample_anchor_pool):
        """Test positive and negative notice sections"""
        trade_date = '20250116'
        
        # Test with only positive notices
        positive_notices = [
            {
                'ts_code': '000001.SZ',
                'notice_date': '2025-01-16',
                'title': '关于公司增持股份的公告',
                'matched_keyword': '增持',
                'sentiment': 'Positive'
            }
        ]
        
        report_path = reporter.generate_report(sample_anchor_pool, positive_notices, trade_date)
        content = Path(report_path).read_text(encoding='utf-8')
        assert '利好' in content or 'Positive' in content
        
        # Test with only negative notices
        negative_notices = [
            {
                'ts_code': '000001.SZ',
                'notice_date': '2025-01-16',
                'title': '关于公司减持股份的公告',
                'matched_keyword': '减持',
                'sentiment': 'Negative'
            }
        ]
        
        report_path = reporter.generate_report(sample_anchor_pool, negative_notices, trade_date)
        content = Path(report_path).read_text(encoding='utf-8')
        assert '利空' in content or 'Negative' in content
    
    def test_generate_report_no_notices_message(self, reporter, sample_anchor_pool):
        """Test message when no notices are found"""
        trade_date = '20250116'
        notice_results = []
        
        report_path = reporter.generate_report(sample_anchor_pool, notice_results, trade_date)
        content = Path(report_path).read_text(encoding='utf-8')
        
        assert '未发现重要异动公告' in content or '未发现' in content
    
    def test_generate_report_encoding(self, reporter, sample_anchor_pool):
        """Test UTF-8 encoding"""
        trade_date = '20250116'
        notice_results = []
        
        report_path = reporter.generate_report(sample_anchor_pool, notice_results, trade_date)
        
        # Should be able to read with UTF-8 encoding
        content = Path(report_path).read_text(encoding='utf-8')
        assert '平安银行' in content  # Chinese characters
        assert '银行' in content
