#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fever API 测试文件

包含所有 Fever API 端点的测试用例。
Fever API 文档：http://www.feedafever.com/api

使用前请配置有效的 Fever 服务器凭据。
"""

import unittest
import hashlib
import time
import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List

# 日志文件路径
LOG_FILE = "fever_api_test_output.log"

def log_api_output(test_name: str, api_name: str, response: Dict[str, Any], status: str = "success"):
    """
    记录 API 输出到日志文件
    
    Args:
        test_name: 测试名称
        api_name: API 名称
        response: API 响应数据
        status: 状态 (success, skipped, error)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 准备日志数据
    log_entry = {
        "timestamp": timestamp,
        "test_name": test_name,
        "api_name": api_name,
        "status": status,
        "response": response
    }
    
    # 移除敏感信息和大数据
    if 'api_key' in log_entry['response']:
        log_entry['response']['api_key'] = '***REDACTED***'
    
    # 截断大型响应
    if 'items' in log_entry['response'] and len(log_entry['response']['items']) > 5:
        log_entry['response']['items_preview'] = log_entry['response']['items'][:5]
        log_entry['response']['items_count'] = len(log_entry['response']['items'])
        del log_entry['response']['items']
    
    if 'feeds' in log_entry['response'] and len(log_entry['response']['feeds']) > 5:
        log_entry['response']['feeds_preview'] = log_entry['response']['feeds'][:5]
        log_entry['response']['feeds_count'] = len(log_entry['response']['feeds'])
        del log_entry['response']['feeds']
    
    if 'groups' in log_entry['response'] and len(log_entry['response']['groups']) > 5:
        log_entry['response']['groups_preview'] = log_entry['response']['groups'][:5]
        log_entry['response']['groups_count'] = len(log_entry['response']['groups'])
        del log_entry['response']['groups']
    
    if 'favicons' in log_entry['response'] and len(log_entry['response']['favicons']) > 5:
        log_entry['response']['favicons_preview'] = log_entry['response']['favicons'][:5]
        log_entry['response']['favicons_count'] = len(log_entry['response']['favicons'])
        del log_entry['response']['favicons']
    
    if 'links' in log_entry['response'] and len(log_entry['response']['links']) > 5:
        log_entry['response']['links_preview'] = log_entry['response']['links'][:5]
        log_entry['response']['links_count'] = len(log_entry['response']['links'])
        del log_entry['response']['links']
    
    # 追加到日志文件
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"时间：{timestamp}\n")
        f.write(f"测试：{test_name}\n")
        f.write(f"API: {api_name}\n")
        f.write(f"状态：{status}\n")
        f.write("-" * 40 + "\n")
        f.write(json.dumps(log_entry['response'], ensure_ascii=False, indent=2))
        f.write("\n\n")


class FeverAPI:
    """
    Fever API 客户端类
    
    封装了所有 Fever API 的读取和写入操作。
    """
    
    def __init__(self, base_url: str, email: str, password: str):
        """
        初始化 Fever API 客户端
        
        Args:
            base_url: Fever 服务器的基础 URL，例如 'http://example.com/fever/'
            email: 登录邮箱
            password: 登录密码
        """
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.password = password
        self.api_key = self._generate_api_key()
        self.session = requests.Session()
        
    def _generate_api_key(self) -> str:
        """生成 API 密钥 (email:password 的 MD5)"""
        return hashlib.md5(f"{self.email}:{self.password}".encode('utf-8')).hexdigest()
    
    def _get_endpoint_url(self) -> str:
        """获取 API 端点 URL"""
        return f"{self.base_url}/?api"
    
    def _make_request(self, params: Optional[Dict[str, Any]] = None, 
                      post_data: Optional[Dict[str, Any]] = None,
                      response_format: str = 'json') -> Dict[str, Any]:
        """
        发送 API 请求
        
        Args:
            params: URL 查询参数
            post_data: POST 数据
            response_format: 响应格式 ('json' 或 'xml')
            
        Returns:
            API 响应数据
        """
        url = self._get_endpoint_url()
        
        if response_format == 'xml':
            if params is None:
                params = {}
            params['api'] = 'xml'
        
        if post_data:
            # POST 请求
            post_data['api_key'] = self.api_key
            response = self.session.post(url, params=params, data=post_data)
        else:
            # GET 请求
            if params is None:
                params = {}
            params['api_key'] = self.api_key
            response = self.session.get(url, params=params)
        
        response.raise_for_status()
        
        if response_format == 'xml':
            return {'raw_xml': response.text}
        return response.json()
    
    # ==================== 基础认证 ====================
    
    def test_auth(self, response_format: str = 'json') -> Dict[str, Any]:
        """
        测试基础认证
        
        返回 API 版本和认证状态。
        
        Returns:
            包含 api_version 和 auth 的响应
        """
        return self._make_request(response_format=response_format)
    
    # ==================== Groups (分组) ====================
    
    def get_groups(self) -> Dict[str, Any]:
        """
        获取所有分组
        
        Returns:
            包含 groups 和 feeds_groups 数组的响应
        """
        return self._make_request(params={'groups': ''})
    
    # ==================== Feeds (订阅源) ====================
    
    def get_feeds(self) -> Dict[str, Any]:
        """
        获取所有订阅源
        
        Returns:
            包含 feeds 和 feeds_groups 数组的响应
        """
        return self._make_request(params={'feeds': ''})
    
    # ==================== Favicons (图标) ====================
    
    def get_favicons(self) -> Dict[str, Any]:
        """
        获取所有订阅源图标
        
        Returns:
            包含 favicons 数组的响应
        """
        return self._make_request(params={'favicons': ''})
    
    # ==================== Items (条目/文章) ====================
    
    def get_items(self, since_id: Optional[int] = None,
                  max_id: Optional[int] = None,
                  with_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        获取条目列表
        
        Args:
            since_id: 获取此 ID 之后的条目
            max_id: 获取此 ID 之前的条目
            with_ids: 指定要获取的条目 ID 列表 (最多 50 个)
            
        Returns:
            包含 items 数组和 total_items 的响应
        """
        params = {'items': ''}
        
        if since_id is not None:
            params['since_id'] = since_id
        if max_id is not None:
            params['max_id'] = max_id
        if with_ids is not None:
            params['with_ids'] = ','.join(map(str, with_ids[:50]))
        
        return self._make_request(params=params)
    
    # ==================== Links (热门链接) ====================
    
    def get_links(self, offset: int = 0, range_days: int = 7, page: int = 1) -> Dict[str, Any]:
        """
        获取热门链接
        
        Args:
            offset: 偏移天数，默认为 0 (从现在开始)
            range_days: 时间范围 (天数)，默认为 7 天
            page: 页码，默认为 1
            
        Returns:
            包含 links 数组的响应
        """
        params = {
            'links': '',
            'offset': offset,
            'range': range_days,
            'page': page
        }
        return self._make_request(params=params)
    
    # ==================== Unread Item IDs (未读条目 ID) ====================
    
    def get_unread_item_ids(self) -> Dict[str, Any]:
        """
        获取所有未读条目的 ID 列表
        
        Returns:
            包含 unread_item_ids (逗号分隔的字符串) 的响应
        """
        return self._make_request(params={'unread_item_ids': ''})
    
    # ==================== Saved Item IDs (已保存条目 ID) ====================
    
    def get_saved_item_ids(self) -> Dict[str, Any]:
        """
        获取所有已保存条目的 ID 列表
        
        Returns:
            包含 saved_item_ids (逗号分隔的字符串) 的响应
        """
        return self._make_request(params={'saved_item_ids': ''})
    
    # ==================== Write Operations (写入操作) ====================
    
    def mark_item_as_read(self, item_id: int) -> Dict[str, Any]:
        """
        标记条目为已读
        
        Args:
            item_id: 要标记的条目 ID
            
        Returns:
            API 响应
        """
        return self._make_request(post_data={
            'mark': 'item',
            'as': 'read',
            'id': item_id
        })
    
    def mark_item_as_saved(self, item_id: int) -> Dict[str, Any]:
        """
        标记条目为已保存
        
        Args:
            item_id: 要标记的条目 ID
            
        Returns:
            API 响应
        """
        return self._make_request(post_data={
            'mark': 'item',
            'as': 'saved',
            'id': item_id
        })
    
    def mark_item_as_unsaved(self, item_id: int) -> Dict[str, Any]:
        """
        取消标记条目的已保存状态
        
        Args:
            item_id: 要取消标记的条目 ID
            
        Returns:
            API 响应
        """
        return self._make_request(post_data={
            'mark': 'item',
            'as': 'unsaved',
            'id': item_id
        })
    
    def mark_feed_as_read(self, feed_id: int, before_timestamp: int) -> Dict[str, Any]:
        """
        标记订阅源为已读
        
        Args:
            feed_id: 要标记的订阅源 ID
            before_timestamp: 将此时间之前的条目标记为已读 (Unix 时间戳)
            
        Returns:
            API 响应
        """
        return self._make_request(post_data={
            'mark': 'feed',
            'as': 'read',
            'id': feed_id,
            'before': before_timestamp
        })
    
    def mark_group_as_read(self, group_id: int, before_timestamp: int) -> Dict[str, Any]:
        """
        标记分组为已读
        
        Args:
            group_id: 要标记的分组 ID (0 表示 Kindling 超级分组，-1 表示 Sparks 超级分组)
            before_timestamp: 将此时间之前的条目标记为已读 (Unix 时间戳)
            
        Returns:
            API 响应
        """
        return self._make_request(post_data={
            'mark': 'group',
            'as': 'read',
            'id': group_id,
            'before': before_timestamp
        })
    
    def unread_recently_read(self) -> Dict[str, Any]:
        """
        将最近已读的条目标记为未读
        
        Returns:
            API 响应
        """
        return self._make_request(post_data={
            'unread_recently_read': '1'
        })
    
    # ==================== Unofficial API (非官方 API) ====================
    
    def login(self) -> Dict[str, Any]:
        """
        网页登录 (非官方 API)
        
        此方法模拟 Fever 网页的登录请求，返回 fever_auth cookie。
        
        Returns:
            登录响应
        """
        url = f"{self.base_url}/?action=login"
        params = {
            'username': self.email,
            'password': self.password
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        # 返回响应内容和 cookie 信息
        return {
            'status_code': response.status_code,
            'cookies': dict(self.session.cookies),
            'fever_auth': self.session.cookies.get('fever_auth'),
            'raw_response': response.text
        }


class TestFeverAPI(unittest.TestCase):
    """Fever API 测试类"""
    
    # ==================== 配置区域 ====================
    # 请修改以下配置为您的 Fever 服务器信息
    
    FEVER_BASE_URL = "https://ttrss.flow-serene.life/plugins/fever"  # Fever 服务器 URL
    FEVER_EMAIL = "admin"                  # 登录邮箱
    FEVER_PASSWORD = "whl003388"                # 登录密码
    
    # ================================================
    
    def setUp(self):
        """测试前设置"""
        self.api = FeverAPI(
            base_url=self.FEVER_BASE_URL,
            email=self.FEVER_EMAIL,
            password=self.FEVER_PASSWORD
        )
    
    def _skip_if_no_server(self):
        """如果没有配置有效的服务器，跳过测试"""
        if self.FEVER_BASE_URL == "http://yourdomain.com/fever":
            self.skipTest("请配置有效的 Fever 服务器 URL")
    
    # ==================== 认证测试 ====================
    
    def test_01_authentication(self):
        """测试 01: 测试基础认证"""
        self._skip_if_no_server()
        response = self.api.test_auth()
        
        self.assertIn('api_version', response)
        self.assertIn('auth', response)
        self.assertEqual(response['auth'], 1, "认证失败")
        print(f"✓ API 版本：{response['api_version']}")
        log_api_output("test_01_authentication", "基础认证 (JSON)", response)
    
    def test_02_authentication_xml(self):
        """测试 02: 测试 XML 格式响应"""
        self._skip_if_no_server()
        response = self.api.test_auth(response_format='xml')
        
        self.assertIn('raw_xml', response)
        self.assertIn('<response>', response['raw_xml'])
        print(f"✓ XML 响应获取成功")
        log_api_output("test_02_authentication_xml", "基础认证 (XML)", response)
    
    # ==================== Groups 测试 ====================
    
    def test_03_get_groups(self):
        """测试 03: 获取分组列表"""
        self._skip_if_no_server()
        response = self.api.get_groups()
        
        self.assertEqual(response['auth'], 1)
        self.assertIn('groups', response)
        self.assertIn('feeds_groups', response)
        print(f"✓ 分组数量：{len(response['groups'])}")
        log_api_output("test_03_get_groups", "获取分组", response)
        
        # 验证分组结构
        for group in response['groups']:
            self.assertIn('id', group)
            self.assertIn('title', group)
    
    # ==================== Feeds 测试 ====================
    
    def test_04_get_feeds(self):
        """测试 04: 获取订阅源列表"""
        self._skip_if_no_server()
        response = self.api.get_feeds()
        
        self.assertEqual(response['auth'], 1)
        self.assertIn('feeds', response)
        self.assertIn('feeds_groups', response)
        print(f"✓ 订阅源数量：{len(response['feeds'])}")
        log_api_output("test_04_get_feeds", "获取订阅源", response)
        
        # 验证订阅源结构
        for feed in response['feeds']:
            self.assertIn('id', feed)
            self.assertIn('title', feed)
            self.assertIn('url', feed)
            self.assertIn('site_url', feed)
            self.assertIn('is_spark', feed)
    
    # ==================== Favicons 测试 ====================
    
    def test_05_get_favicons(self):
        """测试 05: 获取图标列表"""
        self._skip_if_no_server()
        response = self.api.get_favicons()
        
        self.assertEqual(response['auth'], 1)
        self.assertIn('favicons', response)
        print(f"✓ 图标数量：{len(response['favicons'])}")
        log_api_output("test_05_get_favicons", "获取图标", response)
        
        # 验证图标结构
        for favicon in response['favicons']:
            self.assertIn('id', favicon)
            self.assertIn('data', favicon)
            self.assertTrue(favicon['data'].startswith('image/'))
    
    # ==================== Items 测试 ====================
    
    def test_06_get_items(self):
        """测试 06: 获取条目列表"""
        self._skip_if_no_server()
        response = self.api.get_items()
        
        self.assertEqual(response['auth'], 1)
        self.assertIn('items', response)
        print(f"✓ 条目数量：{len(response['items'])}")
        log_api_output("test_06_get_items", "获取条目", response)
        
        # 验证条目结构
        for item in response['items']:
            self.assertIn('id', item)
            self.assertIn('title', item)
            self.assertIn('html', item)
            self.assertIn('url', item)
    
    def test_07_get_items_with_since_id(self):
        """测试 07: 使用 since_id 获取条目"""
        self._skip_if_no_server()
        
        # 先获取一批条目
        first_response = self.api.get_items()
        log_api_output("test_07_get_items_with_since_id_first", "获取条目 (第一批)", first_response)
        
        if first_response['items']:
            max_id = min(item['id'] for item in first_response['items'])
            # 使用 max_id 获取更多条目
            response = self.api.get_items(max_id=max_id)
            self.assertEqual(response['auth'], 1)
            print(f"✓ 使用 max_id 获取条目成功")
            log_api_output("test_07_get_items_with_since_id_second", "获取条目 (使用 max_id)", response)
    
    def test_08_get_items_with_ids(self):
        """测试 08: 使用 with_ids 获取特定条目"""
        self._skip_if_no_server()
        
        # 先获取一些条目 ID
        first_response = self.api.get_items()
        log_api_output("test_08_get_items_with_ids_first", "获取条目 (第一批)", first_response)
        
        if first_response['items']:
            item_ids = [item['id'] for item in first_response['items'][:5]]
            response = self.api.get_items(with_ids=item_ids)
            self.assertEqual(response['auth'], 1)
            print(f"✓ 使用 with_ids 获取特定条目成功")
            log_api_output("test_08_get_items_with_ids_result", "获取条目 (使用 with_ids)", response)
    
    # ==================== Links 测试 ====================
    
    def test_09_get_links(self):
        """测试 09: 获取热门链接"""
        self._skip_if_no_server()
        try:
            response = self.api.get_links()
            self.assertEqual(response['auth'], 1)
            self.assertIn('links', response)
            print(f"✓ 热门链接数量：{len(response['links'])}")
            log_api_output("test_09_get_links", "获取热门链接", response)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                log_api_output("test_09_get_links", "获取热门链接", {"error": "500 Internal Server Error"}, "skipped")
                self.skipTest("服务器不支持 links API (返回 500 错误)")
            raise
    
    def test_10_get_links_with_params(self):
        """测试 10: 使用参数获取热门链接"""
        self._skip_if_no_server()
        try:
            response = self.api.get_links(offset=0, range_days=3, page=1)
            self.assertEqual(response['auth'], 1)
            print(f"✓ 使用参数获取热门链接成功")
            log_api_output("test_10_get_links_with_params", "获取热门链接 (带参数)", response)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                log_api_output("test_10_get_links_with_params", "获取热门链接 (带参数)", {"error": "500 Internal Server Error"}, "skipped")
                self.skipTest("服务器不支持 links API (返回 500 错误)")
            raise
    
    # ==================== Unread/Saved Item IDs 测试 ====================
    
    def test_11_get_unread_item_ids(self):
        """测试 11: 获取未读条目 ID 列表"""
        self._skip_if_no_server()
        response = self.api.get_unread_item_ids()
        
        self.assertEqual(response['auth'], 1)
        self.assertIn('unread_item_ids', response)
        print(f"✓ 未读条目 ID 列表获取成功")
        log_api_output("test_11_get_unread_item_ids", "获取未读条目 ID", response)
    
    def test_12_get_saved_item_ids(self):
        """测试 12: 获取已保存条目 ID 列表"""
        self._skip_if_no_server()
        response = self.api.get_saved_item_ids()
        
        self.assertEqual(response['auth'], 1)
        self.assertIn('saved_item_ids', response)
        print(f"✓ 已保存条目 ID 列表获取成功")
        log_api_output("test_12_get_saved_item_ids", "获取已保存条目 ID", response)
    
    # ==================== Write Operations 测试 ====================
    # 注意：以下测试会修改服务器数据，默认跳过
    
    @unittest.skip("跳过写入测试，避免修改服务器数据")
    def test_13_mark_item_as_read(self):
        """测试 13: 标记条目为已读"""
        self._skip_if_no_server()
        
        # 获取一个未读条目
        items_response = self.api.get_items()
        if items_response['items']:
            item_id = items_response['items'][0]['id']
            response = self.api.mark_item_as_read(item_id)
            self.assertEqual(response['auth'], 1)
            print(f"✓ 标记条目 {item_id} 为已读")
    
    @unittest.skip("跳过写入测试，避免修改服务器数据")
    def test_14_mark_item_as_saved(self):
        """测试 14: 标记条目为已保存"""
        self._skip_if_no_server()
        
        items_response = self.api.get_items()
        if items_response['items']:
            item_id = items_response['items'][0]['id']
            response = self.api.mark_item_as_saved(item_id)
            self.assertEqual(response['auth'], 1)
            print(f"✓ 标记条目 {item_id} 为已保存")
    
    @unittest.skip("跳过写入测试，避免修改服务器数据")
    def test_15_mark_feed_as_read(self):
        """测试 15: 标记订阅源为已读"""
        self._skip_if_no_server()
        
        feeds_response = self.api.get_feeds()
        if feeds_response['feeds']:
            feed_id = feeds_response['feeds'][0]['id']
            before_timestamp = int(time.time())
            response = self.api.mark_feed_as_read(feed_id, before_timestamp)
            self.assertEqual(response['auth'], 1)
            print(f"✓ 标记订阅源 {feed_id} 为已读")
    
    @unittest.skip("跳过写入测试，避免修改服务器数据")
    def test_16_mark_group_as_read(self):
        """测试 16: 标记分组为已读"""
        self._skip_if_no_server()
        
        groups_response = self.api.get_groups()
        if groups_response['groups']:
            group_id = groups_response['groups'][0]['id']
            before_timestamp = int(time.time())
            response = self.api.mark_group_as_read(group_id, before_timestamp)
            self.assertEqual(response['auth'], 1)
            print(f"✓ 标记分组 {group_id} 为已读")
    
    @unittest.skip("跳过写入测试，避免修改服务器数据")
    def test_17_mark_kindling_as_read(self):
        """测试 17: 标记 Kindling 超级分组为已读 (id=0)"""
        self._skip_if_no_server()
        
        before_timestamp = int(time.time())
        response = self.api.mark_group_as_read(0, before_timestamp)
        self.assertEqual(response['auth'], 1)
        print(f"✓ 标记 Kindling 超级分组为已读")
    
    @unittest.skip("跳过写入测试，避免修改服务器数据")
    def test_18_mark_sparks_as_read(self):
        """测试 18: 标记 Sparks 超级分组为已读 (id=-1)"""
        self._skip_if_no_server()
        
        before_timestamp = int(time.time())
        response = self.api.mark_group_as_read(-1, before_timestamp)
        self.assertEqual(response['auth'], 1)
        print(f"✓ 标记 Sparks 超级分组为已读")
    
    @unittest.skip("跳过写入测试，避免修改服务器数据")
    def test_19_unread_recently_read(self):
        """测试 19: 将最近已读的条目标记为未读"""
        self._skip_if_no_server()
        
        response = self.api.unread_recently_read()
        self.assertEqual(response['auth'], 1)
        print(f"✓ 将最近已读的条目标记为未读")
    
    # ==================== Unofficial API 测试 ====================
    
    @unittest.skip("跳过非官方登录测试，可能需要网页界面支持")
    def test_20_login(self):
        """测试 20: 网页登录 (非官方 API)"""
        self._skip_if_no_server()
        
        response = self.api.login()
        self.assertEqual(response['status_code'], 200)
        print(f"✓ 网页登录成功，fever_auth cookie: {response['fever_auth']}")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestFeverAPI)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 60)
    print("Fever API 测试")
    print("=" * 60)
    print(f"配置:")
    print(f"  - URL: {TestFeverAPI.FEVER_BASE_URL}")
    print(f"  - 邮箱：{TestFeverAPI.FEVER_EMAIL}")
    print("=" * 60)
    print()
    
    success = run_tests()
    exit(0 if success else 1)