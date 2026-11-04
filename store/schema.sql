-- 企业关系图谱最小内核 schema (SQLite)
-- 迁移原则: 只加表加列, 不改语义; 结构化"记忆"沉淀即本库, 飞轮的数据侧

CREATE TABLE IF NOT EXISTS entity (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT NOT NULL CHECK (kind IN ('company','person')),
    name         TEXT NOT NULL,               -- 标准名(工商全称优先)
    name_norm    TEXT NOT NULL,               -- 归一化名: 去空格/全半角/去地区后缀
    uscc         TEXT,                        -- 统一社会信用代码(企业强键)
    aliases      TEXT NOT NULL DEFAULT '[]',  -- JSON数组: 简称/英文名/历史名称
    external_ids TEXT NOT NULL DEFAULT '{}',  -- JSON: {"qcc":"UniqueId"} 对齐硬键
    meta         TEXT NOT NULL DEFAULT '{}',  -- JSON: 法人/注册资本/状态等
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_uscc ON entity(uscc) WHERE uscc IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_entity_name_norm ON entity(name_norm);

-- 关系表: 属性图最小实现 (MVP 2层穿透用 networkx 内存遍历)
CREATE TABLE IF NOT EXISTS edge (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id       INTEGER NOT NULL REFERENCES entity(id),
    to_id         INTEGER NOT NULL REFERENCES entity(id),
    relation      TEXT NOT NULL,   -- shareholder|legal_rep|director|executive|invest|...
    ratio         REAL,            -- 持股比例
    source        TEXT NOT NULL,   -- 'qcc:shareholder' | 'qcc:invest' | 'web' | 'manual'
    evidence      TEXT,            -- 出处描述/URL
    raw_ref       INTEGER REFERENCES qcc_response(id),
    first_seen    TEXT NOT NULL DEFAULT (datetime('now')),
    last_verified TEXT NOT NULL DEFAULT (datetime('now')),  -- TTL新鲜度判断用
    UNIQUE(from_id, to_id, relation, source)
);
CREATE INDEX IF NOT EXISTS idx_edge_from ON edge(from_id);
CREATE INDEX IF NOT EXISTS idx_edge_to   ON edge(to_id);

-- qcc原始响应缓存: 省钱第二道闸 + 可重放重建图库
CREATE TABLE IF NOT EXISTS qcc_response (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    api        TEXT NOT NULL,              -- 'company_shareholder' 等
    req_hash   TEXT NOT NULL UNIQUE,       -- sha256(api + 归一化参数)
    request    TEXT NOT NULL,              -- JSON: 请求参数
    response   TEXT NOT NULL,              -- JSON: 原始返回(证据不可丢)
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    ttl_hours  INTEGER NOT NULL DEFAULT 720  -- 工商类30天, 动态类可调24
);

CREATE TABLE IF NOT EXISTS session (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT 'default',
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    title      TEXT
);

CREATE TABLE IF NOT EXISTS message (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES session(id),
    role       TEXT NOT NULL,              -- user|assistant|tool
    content    TEXT NOT NULL,
    tool_calls TEXT,                       -- JSON
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_message_session ON message(session_id);

-- 成本审计表: 飞轮效果的度量 (命中率 = 1 - qcc_calls/queries)
CREATE TABLE IF NOT EXISTS query_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT REFERENCES session(id),
    question      TEXT NOT NULL,
    entities_hit  TEXT NOT NULL DEFAULT '[]',  -- JSON: 命中的entity id
    qcc_calls     INTEGER NOT NULL DEFAULT 0,  -- 本次付费调用次数
    cache_hit     INTEGER NOT NULL DEFAULT 0,  -- 1=完全未调qcc
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
