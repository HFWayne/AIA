# -*- coding: utf-8 -*-
"""
测试配置和 fixtures
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def mock_nav_data_simple():
    """简单数据：股价持续上涨"""
    dates = pd.date_range('2022-01-01', periods=12, freq='MS')  # 12个月
    nav = [10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5, 15.0, 15.5]
    return pd.DataFrame({'date': dates, 'nav': nav})


@pytest.fixture
def mock_nav_data_with_drop():
    """带下跌数据：涨到12后跌到9"""
    dates = pd.date_range('2022-01-01', periods=10, freq='MS')
    nav = [10.0, 10.5, 11.0, 12.0, 11.0, 10.5, 10.0, 9.5, 9.0, 8.5]
    return pd.DataFrame({'date': dates, 'nav': nav})


@pytest.fixture
def mock_nav_data_volatile():
    """波动数据：涨涨跌跌"""
    dates = pd.date_range('2022-01-01', periods=20, freq='MS')
    nav = [10.0, 11.0, 10.0, 12.0, 11.5, 13.0, 12.0, 14.0, 13.0, 12.5,
           13.5, 12.0, 11.0, 10.0, 9.0, 8.0, 9.0, 10.0, 11.0, 12.0]
    return pd.DataFrame({'date': dates, 'nav': nav})


@pytest.fixture
def mock_nav_data_continuous():
    """连续交易日数据：用于日定投测试"""
    dates = pd.date_range('2022-01-03', periods=30, freq='B')  # 工作日
    nav = np.linspace(10.0, 15.0, 30)  # 从10涨到15
    return pd.DataFrame({'date': dates, 'nav': nav})


@pytest.fixture
def mock_nav_data_stop_loss_scenario():
    """止损场景：持续下跌"""
    dates = pd.date_range('2022-01-01', periods=15, freq='MS')
    nav = [10.0, 9.5, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5, 6.0, 5.5, 5.0, 5.5, 6.0, 6.5, 7.0]
    return pd.DataFrame({'date': dates, 'nav': nav})


@pytest.fixture
def mock_nav_data_take_profit_scenario():
    """止盈场景：累计收益快速达到20%后回撤
    
    月定投场景下，累计收益率 = (当前持仓价值 - 总投入) / 总投入
    因为每月都在买入，累计成本不断增加，所以净值需要涨得更高才能让累计收益达到20%
    """
    dates = pd.date_range('2022-01-01', periods=20, freq='MS')
    # 股价持续上涨，后期回撤
    nav = [10.0, 11.0, 12.0, 13.0, 14.0,   # 前5个月持续上涨
           15.0, 16.0, 17.0, 18.0, 19.0,    # 继续涨到90%
           20.0, 19.5, 19.0, 18.5, 18.0,    # 从高点回撤10%
           17.5, 17.0, 16.5, 16.0, 15.5]    # 继续下跌
    return pd.DataFrame({'date': dates, 'nav': nav})


@pytest.fixture
def mock_nav_data_take_profit_fast():
    """止盈快速场景：净值翻倍，累计收益快速达到目标
    
    假设每月定投1000元：
    - 第1个月：1000/10=100份，投入1000
    - 第2个月：1000/20=50份，投入2000，持仓价值=(100+50)*20=3000，收益=(3000-2000)/2000=50%
    
    为了在月定投下达到20%累计收益，净值需要涨到投入成本的1.2倍左右
    """
    dates = pd.date_range('2022-01-01', periods=12, freq='MS')
    # 股价翻倍
    nav = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0,
           16.0, 17.0, 18.0, 19.0, 20.0, 19.0]  # 涨到20后回撤5%
    return pd.DataFrame({'date': dates, 'nav': nav})
