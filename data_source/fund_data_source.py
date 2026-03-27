import tushare as ts
import akshare as ak
import baostock as bs
import pandas as pd
from typing import Optional, List
import logging
import time

from data_source.config import DATA_SOURCE, TU_SHARE_TOKEN, REQUEST_DELAY, MAX_RETRIES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FundDataSource:
    """统一的数据源接口，支持多数据源切换"""
    
    def __init__(self, preferred_source: Optional[str] = None):
        self.current_source = preferred_source or DATA_SOURCE
        self.request_delay = REQUEST_DELAY
        self.max_retries = MAX_RETRIES
        self._init_tushare()
    
    def _apply_delay(self):
        """请求延时，防止触发频率限制"""
        if self.request_delay > 0:
            time.sleep(self.request_delay)
    
    def _init_tushare(self):
        """初始化tushare"""
        try:
            ts.set_token(TU_SHARE_TOKEN)
            self.pro = ts.pro_api()
            logger.info("Tushare initialized successfully")
        except Exception as e:
            logger.warning(f"Tushare init failed: {e}")
            self.pro = None
    
    def get_fund_nav(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取基金净值数据
        :param fund_code: 基金代码，如 510300 (沪深300ETF), 511880 (黄金ETF)
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD
        :return: DataFrame with columns: date, nav, name
        """
        data = None
        
        sources = self._get_source_priority()
        
        for source in sources:
            try:
                if source == "tushare":
                    data = self._get_fund_from_tushare(fund_code, start_date, end_date)
                elif source == "akshare":
                    data = self._get_fund_from_akshare(fund_code, start_date, end_date)
                elif source == "baostock":
                    data = self._get_fund_from_baostock(fund_code, start_date, end_date)
                
                if data is not None and not data.empty:
                    logger.info(f"Successfully got data from {source}: {len(data)} records")
                    data['source'] = source
                    return data
            except Exception as e:
                logger.warning(f"{source} failed for {fund_code}: {e}")
                continue
        
        return None
    
    def _get_source_priority(self) -> List[str]:
        """获取数据源优先级"""
        if self.current_source == "auto":
            return ["tushare", "akshare", "baostock"]
        return [self.current_source]
    
    def _get_fund_from_tushare(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从tushare获取基金/ETF数据"""
        if self.pro is None:
            return None
        
        for retry in range(self.max_retries):
            try:
                self._apply_delay()
                df = self.pro.fund_nav(ts_code=f"{fund_code}.OF", start_date=start_date, end_date=end_date)
                if df is not None and not df.empty:
                    df = df.rename(columns={
                        'nav_date': 'date',
                        'nav': 'nav',
                        'accum_nav': 'accum_nav',
                        'fund_name': 'name'
                    })
                    df = df[['date', 'nav', 'accum_nav', 'name']].sort_values('date')
                    return df
            except Exception as e:
                logger.warning(f"Tushare fund_nav error (retry {retry+1}): {e}")
                if retry < self.max_retries - 1:
                    time.sleep(1)
        
        for retry in range(self.max_retries):
            for exchange in ['SH', 'SZ']:
                try:
                    self._apply_delay()
                    logger.info(f"Trying tushare daily {fund_code}.{exchange}")
                    df = self.pro.daily(ts_code=f"{fund_code}.{exchange}", start_date=start_date, end_date=end_date, adj='hfq')
                    
                    if df is not None and not df.empty:
                        df = df.rename(columns={
                            'trade_date': 'date',
                            'close': 'nav'
                        })
                        df = df[['date', 'open', 'high', 'low', 'nav']].sort_values('date')
                        df['accum_nav'] = df['nav']
                        return df
                except Exception as e:
                    logger.warning(f"Tushare daily error (retry {retry+1}): {e}")
                    if retry < self.max_retries - 1:
                        time.sleep(1)
        
        return None
    
    def _get_fund_from_akshare(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从akshare获取基金数据（使用新浪接口）"""
        funcs_to_try = [
            ('stock_zh_a_hist_sina', {'symbol': fund_code}),
            ('fund_etf_hist_sina', {'symbol': fund_code}),
            ('fund_etf_hist_em', {'symbol': fund_code}),
        ]
        
        for retry in range(self.max_retries):
            for func_name, kwargs in funcs_to_try:
                try:
                    self._apply_delay()
                    logger.info(f"Trying ak.{func_name}({fund_code}) retry {retry+1}")
                    func = getattr(ak, func_name, None)
                    if func is None:
                        continue
                    
                    df = func(**kwargs)
                    
                    if df is not None and not df.empty:
                        logger.info(f"Got data from {func_name}")
                        
                        for date_col in ['day', '日期', 'date']:
                            if date_col in df.columns:
                                df['day'] = pd.to_datetime(df[date_col])
                                break
                        
                        for price_col in ['close', '收盘', 'close_x', '单位净值']:
                            if price_col in df.columns:
                                df['price'] = df[price_col]
                                break
                        
                        start_dt = pd.to_datetime(start_date)
                        end_dt = pd.to_datetime(end_date)
                        df = df[(df['day'] >= start_dt) & (df['day'] <= end_dt)]
                        
                        result = pd.DataFrame()
                        result['date'] = df['day'].dt.strftime('%Y%m%d')
                        result['nav'] = df['price']
                        result['accum_nav'] = df['price']
                        
                        logger.info(f"Got {len(result)} rows")
                        return result.sort_values('date')
                except Exception as e:
                    logger.warning(f"ak.{func_name} error: {e}")
            if retry < self.max_retries - 1:
                time.sleep(1)
        return None
    
    def _get_fund_from_baostock(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从baostock获取基金数据"""
        try:
            bs.login()
            if '-' in start_date:
                start_str = start_date
                end_str = end_date
            else:
                start_str = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
                end_str = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
            
            code_formats = [f"of.{fund_code}", f"sh.{fund_code}", f"sz.{fund_code}"]
            
            for retry in range(self.max_retries):
                for code in code_formats:
                    try:
                        self._apply_delay()
                        logger.info(f"Trying Baostock with {code}")
                        rs = bs.query_history_k_data_plus(
                            code,
                            "date,open,high,low,close",
                            start_date=start_str,
                            end_date=end_str,
                            frequency="d",
                            adjustflag="2"
                        )
                        
                        logger.info(f"Baostock result: error_code={rs.error_code}")
                        
                        if rs.error_code == '0':
                            data_list = []
                            while rs.error_code == '0' and rs.next():
                                data_list.append(rs.get_row_data())
                            
                            if data_list:
                                df = pd.DataFrame(data_list, columns=rs.fields)
                                logger.info(f"Got {len(df)} rows from Baostock")
                                df = df.rename(columns={'close': 'nav'})
                                df['accum_nav'] = df['nav']
                                bs.logout()
                                return df[['date', 'nav', 'accum_nav']]
                        else:
                            logger.warning(f"Baostock query failed: {rs.error_msg}")
                    except Exception as e:
                        logger.warning(f"Baostock error for {code}: {e}")
                        if retry < self.max_retries - 1:
                            time.sleep(1)
            
            bs.logout()
        except Exception as e:
            logger.warning(f"Baostock fund error: {e}")
        return None
    
    def set_source(self, source: str):
        """设置数据源"""
        self.current_source = source
        logger.info(f"Data source changed to: {source}")

    def get_stock_info(self, stock_code: str) -> Optional[dict]:
        """
        获取股票/ETF基本信息
        :param stock_code: 股票代码，如 600036, 510300
        :return: dict with name, type, market, etc.
        """
        stock_info = None
        
        if self.pro:
            stock_info = self._get_stock_info_tushare(stock_code)
        
        if stock_info is None:
            stock_info = self._get_stock_info_akshare(stock_code)
        
        return stock_info
    
    def _get_stock_info_tushare(self, stock_code: str) -> Optional[dict]:
        """从tushare获取股票信息"""
        if self.pro is None:
            return None
        
        self._apply_delay()
        
        exchange = "SH" if stock_code.startswith(("5", "6", "9")) else "SZ"
        ts_code = f"{stock_code}.{exchange}"
        
        try:
            df = self.pro.stock_basic(ts_code=ts_code, list_status='L')
            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    'code': stock_code,
                    'name': row.get('name', stock_code),
                    'market': 'SH' if exchange == 'SH' else 'SZ',
                    'industry': row.get('industry', ''),
                    'list_date': row.get('list_date', ''),
                }
        except Exception as e:
            logger.warning(f"Tushare stock_basic error: {e}")
        
        try:
            df = self.pro.fund_basic(market='E', ts_code=ts_code)
            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    'code': stock_code,
                    'name': row.get('name', stock_code),
                    'type': 'ETF',
                    'market': 'SH' if exchange == 'SH' else 'SZ',
                    'management': row.get('management', ''),
                }
        except Exception as e:
            logger.warning(f"Tushare fund_basic error: {e}")
        
        try:
            df = self.pro.daily(ts_code=ts_code, start_date='20240101', end_date='20240110')
            if df is not None and not df.empty:
                name_map = {
                    '600036': '招商银行', '601318': '中国平安', '000858': '五粮液',
                    '600519': '贵州茅台', '601888': '中国中免', '300750': '宁德时代',
                    '000001': '上证指数', '399001': '深证成指', '399006': '创业板指',
                    '000300': '沪深300', '000905': '中证500', '000016': '上证50',
                    '510300': '沪深300ETF', '510500': '中证500ETF', '159915': '创业板ETF',
                    '510050': '上证50ETF', '510880': '红利ETF', '512880': '证券ETF',
                    '512760': '芯片ETF', '512660': '军工ETF', '512010': '医药ETF',
                    '515050': '5GETF', '512890': '红利低波ETF', '515100': '红利增强ETF',
                }
                return {
                    'code': stock_code,
                    'name': name_map.get(stock_code, stock_code),
                    'market': 'SH' if exchange == 'SH' else 'SZ',
                    'verified': True,
                }
        except Exception as e:
            logger.warning(f"Tushare daily verify error: {e}")
        
        return None
    
    def _get_stock_info_akshare(self, stock_code: str) -> Optional[dict]:
        """从akshare获取股票信息"""
        try:
            self._apply_delay()
            
            info = ak.stock_individual_info_em(symbol=stock_code)
            if info is not None and not info.empty:
                info_dict = dict(zip(info['item'], info['value']))
                return {
                    'code': stock_code,
                    'name': info_dict.get('股票简称', stock_code),
                    'market': 'SH' if stock_code.startswith(('5', '6', '9')) else 'SZ',
                    'industry': info_dict.get('行业', ''),
                    'verified': True,
                }
        except Exception as e:
            logger.warning(f"AkShare stock_info error: {e}")
        
        name_map = {
            '600036': '招商银行', '601318': '中国平安', '000858': '五粮液',
            '600519': '贵州茅台', '601888': '中国中免', '300750': '宁德时代',
            '510300': '沪深300ETF', '510500': '中证500ETF', '159915': '创业板ETF',
            '510050': '上证50ETF', '510880': '红利ETF', '512880': '证券ETF',
            '512760': '芯片ETF', '512660': '军工ETF', '512010': '医药ETF',
            '515050': '5GETF', '512890': '红利低波ETF', '515100': '红利增强ETF',
        }
        
        if stock_code in name_map:
            return {
                'code': stock_code,
                'name': name_map[stock_code],
                'verified': True,
            }
        
        return None
    
    def verify_stock(self, stock_code: str) -> tuple[bool, Optional[str]]:
        """
        验证股票代码是否有效
        :return: (is_valid, stock_name)
        """
        info = self.get_stock_info(stock_code)
        if info:
            return True, info.get('name', stock_code)
        return False, None


# 常用基金代码示例
FUND_CODES = {
    # 指数基金
    '沪深300ETF': '510300',
    '上证50ETF': '510050',
    '创业板ETF': '159915',
    '中证500ETF': '510500',
    '科创50ETF': '588000',
    # 债券基金
    '纯债基金': '161039',
    '中债ETF': '511010',
    # 黄金ETF
    '黄金ETF': '518880',
    '易方达黄金ETF': '159934',
}


def get_fund_data(fund_code: str, start_date: str, end_date: str, source: str = None) -> Optional[pd.DataFrame]:
    """便捷函数：获取基金数据"""
    ds = FundDataSource(preferred_source=source)
    return ds.get_fund_nav(fund_code, start_date, end_date)


if __name__ == "__main__":
    ds = FundDataSource(DATA_SOURCE)
    df = ds.get_fund_nav("510300", "20240101", "20240630")
    print(df)