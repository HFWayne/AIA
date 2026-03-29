# -*- coding: utf-8 -*-
"""
i18n 模块测试
"""

import pytest
import os
import sys

sys_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, sys_path)


class TestI18n:
    """i18n 模块测试"""

    def test_import_i18n(self):
        """测试导入 i18n 模块"""
        from i18n import t, set_locale, get_locale, get_language_name
        assert callable(t)
        assert callable(set_locale)
        assert callable(get_locale)
        assert callable(get_language_name)

    def test_translation_chinese(self):
        """测试中文翻译"""
        from i18n import t, set_locale
        
        set_locale("zh_CN")
        assert t("app_title") == "股票定投回测工具"
        assert t("tab_single_backtest") == "📊 单股票回测"

    def test_translation_english(self):
        """测试英文翻译"""
        from i18n import t, set_locale
        
        set_locale("en_US")
        assert t("app_title") == "Stock DCA Backtesting Tool"
        assert t("tab_single_backtest") == "📊 Single Stock"

    def test_language_names(self):
        """测试语言名称"""
        from i18n import get_language_name
        
        assert get_language_name("zh_CN") == "中文"
        assert get_language_name("en_US") == "English"
        assert get_language_name("unknown") == "unknown"

    def test_get_locale(self):
        """测试获取当前语言"""
        from i18n import get_locale, set_locale
        
        set_locale("zh_CN")
        assert get_locale() == "zh_CN"
        
        set_locale("en_US")
        assert get_locale() == "en_US"

    def test_missing_key_returns_key(self):
        """测试缺失的 key 返回原值"""
        from i18n import t, set_locale
        
        set_locale("zh_CN")
        result = t("nonexistent_key_12345")
        assert result == "nonexistent_key_12345"

    def test_chinese_locale_complete(self):
        """测试中文语言包完整性"""
        from i18n.locales.zh_CN import zh_CN
        
        required_keys = [
            "app_title",
            "tab_single_backtest",
            "sidebar_title",
            "metric_total_invested",
            "success_backtest_complete"
        ]
        
        for key in required_keys:
            assert key in zh_CN, f"Missing key: {key}"

    def test_english_locale_complete(self):
        """测试英文语言包完整性"""
        from i18n.locales.en_US import en_US
        
        required_keys = [
            "app_title",
            "tab_single_backtest",
            "sidebar_title",
            "metric_total_invested",
            "success_backtest_complete"
        ]
        
        for key in required_keys:
            assert key in en_US, f"Missing key: {key}"

    def test_locale_key_count(self):
        """测试语言包 key 数量"""
        from i18n.locales.zh_CN import zh_CN
        from i18n.locales.en_US import en_US
        
        zh_count = len(zh_CN)
        en_count = len(en_US)
        
        assert zh_count >= 50, f"Chinese locale should have at least 50 keys, got {zh_count}"
        assert en_count >= 50, f"English locale should have at least 50 keys, got {en_count}"
        assert zh_count == en_count, "Both locales should have the same number of keys"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
