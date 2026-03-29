# -*- coding: utf-8 -*-
"""
国际化 (i18n) 模块

支持中文和英文两种语言
"""

import streamlit as st
from typing import Optional

_translations = {}
_current_locale = "zh_CN"


def init_i18n():
    """初始化翻译"""
    global _translations
    
    from i18n.locales import zh_CN, en_US
    
    _translations = {
        "zh_CN": zh_CN,
        "en_US": en_US,
    }


def get_locale() -> str:
    """获取当前语言环境"""
    if "locale" not in st.session_state:
        st.session_state["locale"] = "zh_CN"
    return st.session_state["locale"]


def set_locale(locale: str):
    """设置语言环境"""
    global _current_locale
    if locale in ["zh_CN", "en_US"]:
        st.session_state["locale"] = locale
        _current_locale = locale


def t(key: str) -> str:
    """翻译函数
    
    Usage:
        from i18n import t
        st.title(t("app_title"))
    """
    locale = get_locale()
    
    if not _translations:
        init_i18n()
    
    if locale in _translations:
        return _translations[locale].get(key, key)
    
    return key


def get_language_name(locale: str) -> str:
    """获取语言显示名称"""
    names = {
        "zh_CN": "中文",
        "en_US": "English"
    }
    return names.get(locale, locale)


def render_language_selector():
    """渲染语言选择器（右上角下拉框）"""
    current = get_locale()
    
    locale_options = ["zh_CN", "en_US"]
    locale_labels = {
        "zh_CN": "🇨🇳 中文",
        "en_US": "🇺🇸 English"
    }
    
    selected = st.selectbox(
        "🌐",
        options=locale_options,
        index=locale_options.index(current),
        format_func=lambda x: locale_labels[x],
        key="language_selector",
        label_visibility="collapsed"
    )
    
    if selected != current:
        set_locale(selected)
        st.rerun()
    
    st.markdown("""
    <style>
    [data-testid="stSelectbox"] {
        position: fixed;
        top: 4px;
        right: 70px;
        z-index: 999;
        width: 120px;
    }
    [data-testid="stSelectbox"] > div {
        background: white;
    }
    </style>
    """, unsafe_allow_html=True)


def gettext(key: str) -> str:
    """gettext 兼容函数"""
    return t(key)


_ = gettext

init_i18n()
