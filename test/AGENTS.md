# Test Module Knowledge Base

## Overview

测试架构：使用 Vitest 测试框架，采用分离的测试目录结构。当前测试覆盖 CLI 命令和 Feed 生成服务。

## Structure

```
test/
├── cli/
│   └── group-edit.test.ts     # 组编辑命令测试
└── services/
    └── feed/
        └── PodcastFeedGenerator.test.ts  # Feed 生成器测试
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 添加 CLI 测试 | `test/cli/` 目录 | 测试 CLI 命令逻辑 |
| 添加服务测试 | `test/services/` 目录 | 测试服务层逻辑 |
| 查看测试配置 | `package.json` (vitest 配置) | Vitest 配置 |

## 测试框架

**Vitest** - 下一代测试框架，支持：
- ESM 原生支持
- 快速监听模式
- 内置覆盖率
- Vitest UI

**配置** (`package.json`):
```json
{
  "scripts": {
    "test": "vitest",
    "test:coverage": "vitest --coverage"
  },
  "devDependencies": {
    "vitest": "^2.1.8"
  }
}
```

## 测试模式

### CLI 命令测试
测试 CLI 命令的业务逻辑：

**文件**: `test/cli/group-edit.test.ts`

**模式**:
```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { editGroup } from '../../src/cli/commands/groups';

describe('editGroup', () => {
  beforeEach(() => {
    // 设置测试数据库
  });
  
  afterEach(() => {
    // 清理测试数据
  });
  
  it('should edit group name', () => {
    const result = editGroup('grp-123', { name: 'New Name' });
    expect(result).toBe(true);
  });
});
```

### 服务测试
测试服务层功能：

**文件**: `test/services/feed/PodcastFeedGenerator.test.ts`

**模式**:
```typescript
import { describe, test, expect, afterAll } from 'vitest';
import { PodcastFeedGenerator } from '../../../src/services/feed/PodcastFeedGenerator';

describe('PodcastFeedGenerator', () => {
  afterAll(() => {
    // 清理生成的测试文件
  });
  
  test('should generate valid RSS feed', () => {
    const generator = new PodcastFeedGenerator();
    const xml = generator.generateFeed(items, config);
    
    expect(xml).toContain('<rss');
    expect(xml).toContain('</rss>');
  });
});
```

## 代码约定

### 测试文件命名
- `*.test.ts` - 测试文件后缀
- 与源文件路径对应：`src/services/feed/X.ts` → `test/services/feed/X.test.ts`

### 测试数据库
使用独立的测试数据库：
```typescript
const TEST_DB_PATH = './data/test-rss2pod.db';

beforeEach(() => {
  const dbManager = new DatabaseManager(TEST_DB_PATH);
  dbManager.initialize();
});

afterEach(() => {
  // 清理测试数据库
  if (existsSync(TEST_DB_PATH)) {
    unlinkSync(TEST_DB_PATH);
  }
});
```

### 测试分组
使用 `describe` 分组相关测试：
```typescript
describe('GroupManagement', () => {
  describe('createGroup', () => {
    it('should create group with valid config', () => { /* ... */ });
    it('should fail with invalid trigger type', () => { /* ... */ });
  });
  
  describe('editGroup', () => {
    it('should update group name', () => { /* ... */ });
    it('should update trigger config', () => { /* ... */ });
  });
});
```

## 反模式

- ❌ 不要使用 `console.log` - 使用测试断言
- ❌ 不要跳过清理 - `afterEach` 清理测试数据
- ❌ 不要依赖测试顺序 - 每个测试独立
- ❌ 不要测试实现细节 - 测试公共 API 行为
- ❌ 不要忘记断言 - 每个测试必须有 `expect()`

## 独特风格

### 测试数据清理
每个测试后清理测试数据库：
```typescript
afterEach(() => {
  if (existsSync(TEST_DB_PATH)) {
    unlinkSync(TEST_DB_PATH);
  }
});
```

### ESM 测试
Vitest 原生支持 ESM：
```typescript
import { describe, it, expect } from 'vitest';
import { someFunction } from '../../src/module.js';  // .js 扩展名必需
```

## 运行测试

```bash
# 运行所有测试
npm run test

# 运行特定测试文件
npx vitest test/cli/group-edit.test.ts

# 监听模式（开发）
npm run test -- --watch

# 生成覆盖率报告
npm run test -- --coverage

# 使用 UI 查看测试结果
npx vitest --ui
```

## 添加新测试步骤

1. 在 `test/` 目录创建对应子目录
2. 创建 `*.test.ts` 文件
3. 导入 Vitest 函数：`describe, it, expect` 等
4. 编写测试用例
5. 添加 `beforeEach` 和 `afterEach` 钩子
6. 运行测试验证

## 测试示例

### CLI 命令测试
```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createGroup } from '../../src/cli/commands/groups';
import { DatabaseManager } from '../../src/infrastructure/database/DatabaseManager';
import { GroupRepository } from '../../src/repositories/GroupRepository';

describe('createGroup', () => {
  const TEST_DB_PATH = './data/test-rss2pod.db';
  let dbManager: DatabaseManager;
  let groupRepo: GroupRepository;
  
  beforeEach(() => {
    dbManager = new DatabaseManager(TEST_DB_PATH);
    dbManager.initialize();
    const db = dbManager.getDb();
    groupRepo = new GroupRepository(db);
  });
  
  afterEach(() => {
    dbManager.close();
    if (existsSync(TEST_DB_PATH)) {
      unlinkSync(TEST_DB_PATH);
    }
  });
  
  it('should create group with valid config', () => {
    const name = 'Test Group';
    const sourceIds = ['1', '2'];
    const triggerType = 'count';
    const triggerConfig = { threshold: 10 };
    
    const result = createGroup(name, sourceIds, triggerType, triggerConfig);
    
    expect(result.id).toMatch(/grp-\d+/);
    expect(result.name).toBe(name);
    expect(result.sourceIds).toEqual(sourceIds);
  });
});
```

### 服务测试
```typescript
import { describe, test, expect, afterAll } from 'vitest';
import { PodcastFeedGenerator } from '../../../src/services/feed/PodcastFeedGenerator';
import type { FeedItem, FeedConfig } from '../../../src/services/feed';

describe('PodcastFeedGenerator', () => {
  const TEST_FEED_PATH = './data/media/feeds/test.xml';
  
  afterAll(() => {
    // 清理测试文件
    if (existsSync(TEST_FEED_PATH)) {
      unlinkSync(TEST_FEED_PATH);
    }
  });
  
  test('should generate valid RSS feed', () => {
    const generator = new PodcastFeedGenerator();
    
    const items: FeedItem[] = [
      {
        title: 'Test Episode',
        description: 'Test description',
        enclosure: {
          url: 'http://example.com/audio.mp3',
          length: 123456,
          type: 'audio/mpeg',
        },
        pubDate: 'Mon, 01 Jan 2024 00:00:00 GMT',
        guid: 'test-episode-1',
      },
    ];
    
    const config: FeedConfig = {
      groupId: 'test',
      title: 'Test Podcast',
      description: 'Test description',
      siteUrl: 'http://localhost:3000',
    };
    
    const xml = generator.generateFeed(items, config);
    
    expect(xml).toContain('<rss');
    expect(xml).toContain('</rss>');
    expect(xml).toContain('Test Episode');
  });
});
```

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `src/` | 测试源文件中的代码 |
| `infrastructure/database/` | 测试数据库使用独立的 test-rss2pod.db |
| `repositories/` | 测试 Repository 的 CRUD 操作 |

## 调试测试

```bash
# 运行测试并显示详细输出
npm run test -- --reporter=verbose

# 运行匹配的测试
npm run test -- --grep "editGroup"

# 运行失败测试
npm run test -- --bail

# 生成 HTML 报告
npm run test -- --coverage --reporter=html
```
