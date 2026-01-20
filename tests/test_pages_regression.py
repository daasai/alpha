"""
Pages Module Regression Tests
验证pages模块导入和app.py路由
"""

import pytest
from pathlib import Path


class TestPagesImport:
    """测试pages模块导入"""
    
    def test_pages_module_import(self):
        """测试pages模块可以正确导入"""
        from pages import render_hunter_page, render_backtest_page, render_truth_page
        
        assert callable(render_hunter_page)
        assert callable(render_backtest_page)
        assert callable(render_truth_page)
    
    def test_pages_init_imports(self):
        """测试pages/__init__.py导出"""
        from pages import render_hunter_page, render_backtest_page, render_truth_page
        
        # 验证函数存在且可调用
        assert hasattr(render_hunter_page, '__call__')
        assert hasattr(render_backtest_page, '__call__')
        assert hasattr(render_truth_page, '__call__')
    
    def test_pages_module_structure(self):
        """测试pages模块文件结构"""
        pages_dir = Path('pages')
        assert pages_dir.exists()
        assert (pages_dir / '__init__.py').exists()
        assert (pages_dir / 'hunter_page.py').exists()
        assert (pages_dir / 'backtest_page.py').exists()
        assert (pages_dir / 'truth_page.py').exists()


class TestAppRouting:
    """测试app.py路由逻辑"""
    
    def test_app_imports_pages(self):
        """测试app.py从pages导入"""
        app_path = Path('app.py')
        if app_path.exists():
            with open(app_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 验证从pages导入
                assert 'from pages import' in content or 'import pages' in content
                assert 'render_hunter_page' in content
                assert 'render_backtest_page' in content
                assert 'render_truth_page' in content
    
    def test_app_routing_logic(self):
        """测试app.py路由逻辑"""
        app_path = Path('app.py')
        if app_path.exists():
            with open(app_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 验证路由调用
                assert 'render_hunter_page()' in content
                assert 'render_backtest_page()' in content
                assert 'render_truth_page()' in content
    
    def test_app_has_three_tabs(self):
        """测试app.py包含三个标签"""
        app_path = Path('app.py')
        if app_path.exists():
            with open(app_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 验证三个标签
                assert '机会挖掘' in content or 'Hunter' in content
                assert '时光机' in content or 'Backtest' in content
                assert '复盘验证' in content or 'Truth' in content
    
    def test_app_simplified_structure(self):
        """测试app.py已简化（不再包含大量业务逻辑）"""
        app_path = Path('app.py')
        if app_path.exists():
            with open(app_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # app.py应该大幅简化（从773行减少到约125行）
                # 这里只验证行数在合理范围内（不超过200行）
                assert len(lines) < 200, f"app.py应该已简化，当前有{len(lines)}行"


class TestPageFunctions:
    """测试页面函数"""
    
    def test_hunter_page_function_signature(self):
        """测试hunter_page函数签名"""
        from pages.hunter_page import render_hunter_page
        import inspect
        
        sig = inspect.signature(render_hunter_page)
        # 应该没有必需参数（或只有可选参数）
        assert len(sig.parameters) == 0 or all(
            p.default != inspect.Parameter.empty 
            for p in sig.parameters.values()
        )
    
    def test_backtest_page_function_signature(self):
        """测试backtest_page函数签名"""
        from pages.backtest_page import render_backtest_page
        import inspect
        
        sig = inspect.signature(render_backtest_page)
        assert len(sig.parameters) == 0 or all(
            p.default != inspect.Parameter.empty 
            for p in sig.parameters.values()
        )
    
    def test_truth_page_function_signature(self):
        """测试truth_page函数签名"""
        from pages.truth_page import render_truth_page
        import inspect
        
        sig = inspect.signature(render_truth_page)
        assert len(sig.parameters) == 0 or all(
            p.default != inspect.Parameter.empty 
            for p in sig.parameters.values()
        )
    
    def test_pages_use_services(self):
        """测试pages使用Service层"""
        # 验证hunter_page使用HunterService
        hunter_page_path = Path('pages/hunter_page.py')
        if hunter_page_path.exists():
            with open(hunter_page_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'HunterService' in content or 'from src.services' in content
        
        # 验证backtest_page使用BacktestService
        backtest_page_path = Path('pages/backtest_page.py')
        if backtest_page_path.exists():
            with open(backtest_page_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'BacktestService' in content or 'from src.services' in content
        
        # 验证truth_page使用TruthService
        truth_page_path = Path('pages/truth_page.py')
        if truth_page_path.exists():
            with open(truth_page_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'TruthService' in content or 'from src.services' in content
