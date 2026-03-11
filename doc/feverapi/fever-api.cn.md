# API 公开测试版

## 信息

目前这是 [http://www.feedafever.com/api](http://www.feedafever.com/api) 的副本，但采用 Markdown 文件格式。

本文档末尾包含一些该 API 未记录的内容。

## 描述

Fever 1.14 引入了全新的 Fever API。该 API 处于公开测试阶段，目前支持基本的内容同步和消费功能。后续更新将支持添加、编辑和删除订阅源（feeds）和分组（groups）。该 API 的主要功能是在远程 Fever 安装中维护数据的本地缓存。

我正在向感兴趣的开发者征求反馈意见，因此测试版 API 可能会根据反馈进行扩展。当前的 API 功能不完整但运行稳定。现有功能可能会扩展，但不会被移除或修改。新功能可能会被添加。

我创建了一个简单的 [HTML 小部件](http://www.feedafever.com/gateway/public/api-widget.html.zip)，可用于查询 Fever API 并查看响应。

# 认证

闲言少叙，Fever API 端点 URL 如下所示：

`http://yourdomain.com/fever/?api`

所有请求必须通过 `POST` 方式提交 `api_key` 进行认证。`api_key` 的值应为 Fever 账户的电子邮件地址和密码用冒号连接后的 md5 校验和。以下是使用 PHP 原生 `md5()` 函数生成有效 `api_key` 值的示例：

```php
$email  = 'you@yourdomain.com';
$pass   = 'b3stp4s4wd3v4';
$api_key = md5($email.':'.$pass);
```

用户可以指定使用 `https` 连接到其 Fever 安装以获得更高的安全性，但您不应假设所有 Fever 安装都支持 `https`。

默认响应是一个包含两个成员的 JSON 对象：

* `api_version` 包含响应的 API 版本（正整数）
* `auth` 表示请求是否成功通过认证（布尔整数）

API 还可以通过将 `xml` 作为 `api` 参数的可选值传递来返回 XML，如下所示：

`http://yourdomain.com/fever/?api=xml`

顶层 XML 元素名为 `response`。

每个成功通过认证的请求的响应中 `auth` 将设置为 `1`，并至少包含一个额外成员：

* `last_refreshed_on_time` 包含最近一次刷新（而非*更新*）的订阅源的时间（Unix 时间戳/整数）

从 Fever API 读取数据时，您需要将参数添加到 API 端点 URL 的查询字符串中。如果您尝试 `POST` 这些参数（及其可选值），Fever 将无法识别该请求。

## 分组（Groups）

`http://yourdomain.com/fever/?api&groups`

带有 groups 参数的请求将返回两个额外成员：

* `groups` 包含 `group` 对象的数组
* `feeds_groups` 包含 `feeds_group` 对象的数组

`group` 对象具有以下成员：

* `id`（正整数）
* `title`（utf-8 字符串）

`feeds_group` 对象在"订阅源/分组关系"部分进行说明。

"Kindling"超级分组不包含在此响应中，它由所有 `is_spark` 等于 `0` 的订阅源组成。"Sparks"超级分组也不包含在此响应中，它由所有 `is_spark` 等于 `1` 的订阅源组成。

## 订阅源（Feeds）

`http://yourdomain.com/fever/?api&feeds`

带有 `feeds` 参数的请求将返回两个额外成员：

* `feeds` 包含 `feed` 对象的数组
* `feeds_groups` 包含 `feeds_group` 对象的数组

`feed` 对象具有以下成员：

* `id`（正整数）
* `favicon_id`（正整数）
* `title`（utf-8 字符串）
* `url`（utf-8 字符串）
* `site_url`（utf-8 字符串）
* `is_spark`（布尔整数）
* `last_updated_on_time`（Unix 时间戳/整数）

`feeds_group` 对象在"订阅源/分组关系"部分进行说明。

"所有条目（All Items）"超级订阅源不包含在此响应中，它由属于给定分组的所有订阅源的所有条目组成。对于"Kindling"超级分组和所有用户创建的分组，条目应限制为 `is_spark` 等于 `0` 的订阅源。对于"Sparks"超级分组，条目应限制为 `is_spark` 等于 `1` 的订阅源。

## 订阅源/分组关系（Feeds/Groups Relationships）

带有 `groups` 或 `feeds` 参数的请求将返回一个额外成员：

`feeds_group` 对象具有以下成员：

* `group_id`（正整数）
* `feed_ids`（字符串/逗号分隔的正整数列表）

## 网站图标（Favicons）

`http://yourdomain.com/fever/?api&favicons`

带有 `favicons` 参数的请求将返回一个额外成员：

* `favicons` 包含 `favicon` 对象的数组

`favicon` 对象具有以下成员：

* `id`（正整数）
* `data`（base64 编码的图像数据；带有图像类型前缀）

`data` 值示例：

`image/gif;base64,R0lGODlhAQABAIAAAObm5gAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==`

`favicon` 对象的 `data` 成员可与 `data:` 协议一起使用，将图像嵌入到 CSS 或 HTML 中。PHP/HTML 示例：

`echo '<img src="data:'.$favicon['data'].'">';`

## 条目（Items）

`http://yourdomain.com/fever/?api&items`

带有 `items` 参数的请求将返回两个额外成员：

* `items` 包含条目对象的数组
* `total_items` 包含数据库中存储的条目总数（API 版本 2 中添加）

`item` 对象具有以下成员：

* `id`（正整数）
* `feed_id`（正整数）
* `title`（utf-8 字符串）
* `author`（utf-8 字符串）
* `html`（utf-8 字符串）
* `url`（utf-8 字符串）
* `is_saved`（布尔整数）
* `is_read`（布尔整数）
* `created_on_time`（Unix 时间戳/整数）

大多数服务器没有为 PHP 分配足够的内存来一次性转储所有条目。三个可选参数控制响应中包含的条目。

使用 `since_id` 参数配合本地缓存条目的最高 id 来请求额外的 50 个条目。重复此过程直到响应中的 items 数组为空。

使用 `max_id` 参数配合本地缓存条目的最低 id（或初始为 `0`）来请求之前的 50 个条目。重复此过程直到响应中的 items 数组为空。（API 版本 2 中添加）

使用 `with_ids` 参数配合逗号分隔的条目 id 列表来请求（最多 50 个）特定条目。（API 版本 2 中添加）

## 热门链接（Hot Links）

`http://yourdomain.com/fever/?api&links`

带有 `links` 参数的请求将返回一个额外成员：

* `links` 包含 `link` 对象的数组

`link` 对象具有以下成员：

* `id`（正整数）
* `feed_id`（正整数）仅当 is_item 等于 1 时使用
* `item_id`（正整数）仅当 is_item 等于 1 时使用
* `temperature`（正浮点数）
* `is_item`（布尔整数）
* `is_local`（布尔整数）用于确定是否应显示源订阅源和网站图标
* `is_saved`（布尔整数）仅当 is_item 等于 1 时使用
* `title`（utf-8 字符串）
* `url`（utf-8 字符串）
* `item_ids`（字符串/逗号分隔的正整数列表）

请求热门链接时，您可以通过指定天数范围（range）和偏移量（offset）以及获取额外热门链接的页码（page）来控制范围和偏移。仅带有 `links` 参数的请求等同于：

`http://yourdomain.com/fever/?api&links&offset=0&range=7&page=1`

即从现在开始（`offset=0`）过去一周（`range=7`）的热门链接第一页（`page=1`）。

# 链接注意事项

Fever 实时计算热门链接的热度值。API 假设您拥有最新的条目、订阅源和网站图标的本地缓存，以便构建有意义的热门视图。由于热门链接是临时的，它们不应像条目、订阅源、分组和网站图标那样以关系型方式缓存。

由于 Fever 保存的是条目而非单独的链接，因此只有当 `is_item` 等于 `1` 时您才能"保存"热门链接。

`unread_item_ids` 和 `saved_item_ids` 参数可用于使您的本地缓存与远程 Fever 安装保持同步。

`http://yourdomain.com/fever/?api&unread_item_ids`

带有 `unread_item_ids` 参数的请求将返回一个额外成员：

* `unread_item_ids`（字符串/逗号分隔的正整数列表）

`http://yourdomain.com/fever/?api&saved_item_ids`

带有 `saved_item_ids` 参数的请求将返回一个额外成员：

* `saved_item_ids`（字符串/逗号分隔的正整数列表）

当将条目标记为已读、未读、已保存或未保存，以及将订阅源或分组标记为已读时，将酌情返回这些成员之一。

由于与条目相比，分组和订阅源的数量有限，因此应通过比较本地缓存的订阅源或分组 id 数组与其各自 API 请求返回的订阅源或分组 id 数组来进行同步。

# 写入（Write）

API 的公开测试版不提供添加、编辑或删除订阅源或分组的方法，但您可以将条目、订阅源和分组标记为已读，以及保存或取消保存条目。您还可以将最近阅读的条目取消标记为已读。向 Fever API 写入时，您需要将参数添加到提交给 API 端点 URL 的 POST 数据中。

在您的 POST 数据中添加 `unread_recently_read=1` 将把最近阅读的条目标记为未读。

您可以通过在 POST 数据中添加以下三个参数来更新单个条目：

* `mark=item`
* `as=?` 其中 `?` 替换为 `read`、`saved` 或 `unsaved`
* `id=?` 其中 `?` 替换为要修改的条目的 `id`

将订阅源或分组标记为已读的方法类似，但需要一个额外参数以防止将新的、未接收的条目标记为已读：

* `mark=?` 其中 `?` 替换为 `feed` 或 `group`
* `as=read`
* `id=?` 其中 `?` 替换为要修改的订阅源或分组的 id
* `before=?` 其中 `?` 替换为本地客户端最近一次 `items` API 请求的 Unix 时间戳

您可以通过在 POST 数据中添加以下四个参数将"Kindling"超级分组（以及"Sparks"超级分组）标记为已读：

* `mark=group`
* `as=read`
* `id=0`
* `before=?` 其中 `?` 替换为本地客户端上一次 `items` API 请求的 Unix 时间戳

同样，您可以通过在 POST 数据中添加以下四个参数仅将"Sparks"超级分组标记为已读：

* `mark=group`
* `as=read`
* `id=-1`
* `before=?` 其中 `?` 替换为本地客户端上一次 `items` API 请求的 Unix 时间戳

# 非官方/未记录的 API

这是代表 iPad 上 Mr.Reader App 将使用的一些功能的扩展，这些功能未作为常规 API 记录，但允许使用，因为 Fever API 端点与网页请求相同。

## 登录（login）

`http://yourdomain.com/fever/?action=login&username=[username]&password=[password]`

带有 `action=login` 参数的请求将返回一个 cookie `fever_auth`。这应等于 API 密钥。这是通常由 Fever 网页的登录对话框创建的调用。

* `username` - 您的登录用户名
* `password` - 您为 API 设置的密码

作为返回，一个名为 `fever_auth` 的 cookie 将被设置，值为 API 密钥。

---

## 测试文件：`test_fever_api.py`

包含 __FeverAPI__ 客户端类和 __20 个测试用例__，覆盖所有 API 端点：

__读取 API (Read APIs)__:

- `test_auth()` - 基础认证 (JSON/XML) ✓
- `get_groups()` - 获取分组 ✓ (2 个分组)
- `get_feeds()` - 获取订阅源 ✓ (118 个订阅源)
- `get_favicons()` - 获取图标 ✓ (0 个图标)
- `get_items()` - 获取条目 ✓ (54974 总条目，每次 50 个)
- `get_links()` - 获取热门链接 - 服务器返回 500 错误 (不支持)
- `get_unread_item_ids()` - 未读条目 ID ✓
- `get_saved_item_ids()` - 已保存条目 ID ✓ (大量已保存条目)

__写入 API (Write APIs)__ - 默认跳过:

- `mark_item_as_read()` - 标记条目为已读
- `mark_item_as_saved()` - 标记条目为已保存
- `mark_item_as_unsaved()` - 取消保存
- `mark_feed_as_read()` - 标记订阅源为已读
- `mark_group_as_read()` - 标记分组为已读 (含 Kindling/Sparks 超级分组)
- `unread_recently_read()` - 将最近已读标记为未读

__非官方 API__:

- `login()` - 网页登录 (跳过)

##
