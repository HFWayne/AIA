# -*- coding: utf-8 -*-
"""
数据源诊断页面
"""

import streamlit as st
from data_source.diagnostic import DataSourceDiagnostic
from i18n import t


def render_diagnostic_page():
    """渲染数据源诊断页面"""
    st.markdown(f'<div class="section-header">📡 数据源诊断</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔄 重新诊断", type="primary", use_container_width=True):
            with st.spinner("正在诊断各数据源..."):
                diagnostic = DataSourceDiagnostic()
                result = diagnostic.run_all()
                st.session_state['diagnostic_result'] = result
    
    with col2:
        if st.button("💾 保存报告", use_container_width=True):
            with st.spinner("正在保存报告..."):
                diagnostic = DataSourceDiagnostic()
                files = diagnostic.save_report()
                st.success(f"报告已保存到 reports/ 目录")
    
    st.markdown("---")
    
    result = st.session_state.get('diagnostic_result')
    
    if result is None:
        with st.spinner("正在诊断各数据源..."):
            diagnostic = DataSourceDiagnostic()
            result = diagnostic.run_all()
            st.session_state['diagnostic_result'] = result
    
    if result:
        col_s1, col_s2, col_s3 = st.columns(3)
        
        with col_s1:
            status_icon = "✅" if result.overall_status == "healthy" else "❌"
            st.metric("总体状态", f"{status_icon} {result.overall_status.title()}")
        
        with col_s2:
            st.metric("可用数据源", f"{result.summary['available_sources']}/{result.summary['total_sources']}")
        
        with col_s3:
            recommended = result.summary.get('recommended_source', 'N/A')
            st.metric("推荐数据源", recommended or '无')
        
        st.markdown("---")
        
        for source in result.sources:
            with st.expander(f"{'✅' if source.connected else '❌'} {source.display_name} ({source.name})", expanded=True):
                col_l, col_r = st.columns([1, 1])
                
                with col_l:
                    st.markdown("**基本信息**")
                    st.write(f"- 连接状态: {'已连接' if source.connected else '连接失败'}")
                    if source.latency_ms:
                        st.write(f"- 响应延迟: {source.latency_ms:.0f}ms")
                    if source.error_message:
                        st.write(f"- 错误信息: `{source.error_message}`")
                
                with col_r:
                    if source.connected:
                        st.markdown("**支持的数据类型**")
                        for cap in source.capabilities:
                            st.write(f"- {cap}")
                
                if source.connected:
                    st.markdown("---")
                    col_t1, col_t2 = st.columns([1, 1])
                    
                    with col_t1:
                        st.markdown("**支持的品种**")
                        for stype in source.supported_types:
                            st.write(f"- {stype}")
                    
                    with col_t2:
                        st.markdown("**限制说明**")
                        for limit in source.limitations:
                            st.write(f"- {limit}")
        
        st.markdown("---")
        st.markdown("### 📋 推荐使用方案")
        
        st.info("""
        **自动切换模式（推荐）**: 系统默认使用 **akshare** 作为主数据源，当主数据源不可用时自动切换到 **tushare**。
        
        **回退链路**: """ + " → ".join(result.summary.get('fallback_chain', [])))
        
        with st.expander("📖 详细使用说明"):
            st.markdown("""
            **AkShare**
            - 完全免费开源
            - 数据来源于东方财富等
            - 建议作为主力数据源
            
            **Tushare**
            - 需要配置 `TU_SHARE_TOKEN` 环境变量
            - 免费版有 API 调用频率限制（每分钟 200 次）
            - 部分高级数据需要付费权限
            """)


if __name__ == "__main__":
    render_diagnostic_page()
