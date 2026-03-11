这个 `fever_api.php` 实现的是 **Tiny Tiny RSS 的 Fever API 兼容接口**。
它的设计特点：

* **只有一个入口接口**：`/fever_api.php`
* 通过 **POST/GET 参数决定返回内容**
* 返回 **JSON 或 XML**
* 使用 **api_key 认证**
* 所有请求都是 **同一个 endpoint**

核心模式：

```
/fever_api.php?api_key=APIKEY&<operation>=1
```

或 POST。

---

# 一、API入口

```
/fever_api.php
```

常用参数：

| 参数              | 说明           |
| --------------- | ------------ |
| api_key         | API 密钥       |
| api=xml         | 返回XML，否则JSON |
| groups          | 获取分类         |
| feeds           | 获取订阅源        |
| items           | 获取文章         |
| links           | 获取热门文章       |
| favicons        | 获取favicon    |
| unread_item_ids | 获取未读文章ID     |
| saved_item_ids  | 获取收藏文章ID     |
| mark            | 修改文章状态       |
| as              | 状态类型         |
| id              | 对象ID         |

---

# 二、认证接口

Fever API没有独立认证接口。

认证方式：

```
api_key = md5(email:password)
```

示例：

```
md5("user@example.com:password")
```

请求示例

```
https://example.com/fever_api.php?api_key=ABCDEF123456
```

返回

```json
{
  "api_version": 3,
  "auth": 1,
  "last_refreshed_on_time": "1700000000"
}
```

字段说明：

| 字段                     | 含义         |
| ---------------------- | ---------- |
| api_version            | API版本      |
| auth                   | 1=认证成功     |
| last_refreshed_on_time | feed最后更新时间 |

---

# 三、获取分类 (groups)

## 请求

```
GET /fever_api.php?api_key=APIKEY&groups
```

示例

```
https://example.com/fever_api.php?api_key=123456&groups
```

---

## 返回

```json
{
  "api_version": 3,
  "auth": 1,
  "groups": [
    {
      "id": 1,
      "title": "Technology"
    },
    {
      "id": 2,
      "title": "News"
    }
  ],
  "feeds_groups": [
    {
      "group_id": 1,
      "feed_ids": "5,7"
    }
  ]
}
```

字段解释

| 字段    | 含义   |
| ----- | ---- |
| id    | 分类ID |
| title | 分类名称 |

feeds_groups：

| 字段       | 含义         |
| -------- | ---------- |
| group_id | 分类ID       |
| feed_ids | 该分类包含的feed |

---

# 四、获取Feed列表

## 请求

```
GET /fever_api.php?api_key=APIKEY&feeds
```

示例

```
https://example.com/fever_api.php?api_key=123&feeds
```

---

## 返回

```json
{
  "feeds": [
    {
      "id": 5,
      "favicon_id": 5,
      "title": "Hacker News",
      "url": "https://news.ycombinator.com/rss",
      "site_url": "https://news.ycombinator.com",
      "is_spark": 0,
      "last_updated_on_time": 1700000000
    }
  ]
}
```

字段说明

| 字段                   | 含义         |
| -------------------- | ---------- |
| id                   | feed ID    |
| favicon_id           | favicon ID |
| title                | feed名称     |
| url                  | RSS地址      |
| site_url             | 网站地址       |
| is_spark             | 是否热点源      |
| last_updated_on_time | 最后更新时间     |

---

# 五、获取Favicon

## 请求

```
GET /fever_api.php?api_key=APIKEY&favicons
```

示例

```
https://example.com/fever_api.php?api_key=123&favicons
```

---

## 返回

```json
{
  "favicons": [
    {
      "id": 5,
      "data": "image/gif;base64,R0lGOD..."
    }
  ]
}
```

字段

| 字段   | 含义             |
| ---- | -------------- |
| id   | feed ID        |
| data | base64 favicon |

---

# 六、获取文章 items

## 请求

```
GET /fever_api.php?api_key=APIKEY&items
```

---

## 可选参数

| 参数        | 说明      |
| --------- | ------- |
| feed_ids  | 指定feed  |
| group_ids | 指定分类    |
| since_id  | 获取某ID之后 |
| max_id    | 获取某ID之前 |
| with_ids  | 指定ID    |
| limit     | 限制数量    |

示例

```
https://example.com/fever_api.php?api_key=123&items&since_id=100
```

---

## 返回

```json
{
  "total_items": 500,
  "items": [
    {
      "id": 101,
      "feed_id": 5,
      "title": "New CPU released",
      "author": "John",
      "html": "<p>content</p>",
      "url": "https://site/article",
      "is_saved": 0,
      "is_read": 0,
      "created_on_time": 1700000000
    }
  ]
}
```

字段

| 字段              | 含义         |
| --------------- | ---------- |
| id              | article ID |
| feed_id         | feed       |
| title           | 标题         |
| author          | 作者         |
| html            | 文章内容       |
| url             | 原文         |
| is_saved        | 是否收藏       |
| is_read         | 是否已读       |
| created_on_time | 发布时间       |

---

# 七、获取热门文章 links

## 请求

```
GET /fever_api.php?api_key=APIKEY&links
```

---

示例

```
https://example.com/fever_api.php?api_key=123&links
```

---

返回

```json
{
  "links": [
    {
      "id": 101,
      "feed_id": 5,
      "item_id": 101,
      "temperature": 5,
      "is_item": 1,
      "is_local": 1,
      "is_saved": 0,
      "title": "AI breakthrough",
      "url": "https://example.com",
      "item_ids": ""
    }
  ]
}
```

字段

| 字段          | 含义         |
| ----------- | ---------- |
| id          | link ID    |
| feed_id     | 来源         |
| item_id     | article ID |
| temperature | 热度(score)  |
| is_saved    | 收藏         |
| url         | 链接         |

---

# 八、获取未读文章ID

## 请求

```
GET /fever_api.php?api_key=APIKEY&unread_item_ids
```

---

返回

```json
{
  "unread_item_ids": "101,102,103"
}
```

---

# 九、获取收藏文章ID

## 请求

```
GET /fever_api.php?api_key=APIKEY&saved_item_ids
```

---

返回

```json
{
  "saved_item_ids": "101,110"
}
```

---

# 十、标记文章状态

统一接口：

```
mark=<object>&as=<state>&id=<id>
```

---

## 标记已读

请求

```
GET /fever_api.php?api_key=APIKEY&mark=item&as=read&id=100
```

---

## 标记未读

```
GET /fever_api.php?api_key=APIKEY&mark=item&as=unread&id=100
```

---

## 收藏文章

```
GET /fever_api.php?api_key=APIKEY&mark=item&as=saved&id=100
```

---

## 取消收藏

```
GET /fever_api.php?api_key=APIKEY&mark=item&as=unsaved&id=100
```

---

返回

```json
{
  "api_version":3,
  "auth":1,
  "unread_item_ids":"101,102"
}
```

---

# 十一、标记feed已读

## 请求

```
GET /fever_api.php?api_key=APIKEY&mark=feed&as=read&id=5
```

---

# 十二、标记分类已读

```
GET /fever_api.php?api_key=APIKEY&mark=group&as=read&id=2
```

---

# 十三、参数汇总

| 参数              | 含义                |
| --------------- | ----------------- |
| groups          | 获取分类              |
| feeds           | 获取feeds           |
| favicons        | 获取图标              |
| items           | 获取文章              |
| links           | 热门                |
| unread_item_ids | 未读                |
| saved_item_ids  | 收藏                |
| mark            | 修改状态              |
| as              | read/unread/saved |
| id              | 目标ID              |

---

# 十四、典型客户端调用流程

Fever客户端一般顺序：

1️⃣ 验证API

```
/fever_api.php?api_key=KEY
```

2️⃣ 获取feeds

```
/fever_api.php?api_key=KEY&feeds
```

3️⃣ 获取groups

```
/fever_api.php?api_key=KEY&groups
```

4️⃣ 获取items

```
/fever_api.php?api_key=KEY&items&since_id=xxx
```

5️⃣ 获取未读

```
/fever_api.php?api_key=KEY&unread_item_ids
```

6️⃣ 标记已读

```
/fever_api.php?api_key=KEY&mark=item&as=read&id=100
```
