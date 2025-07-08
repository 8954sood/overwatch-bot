-- 유저의 기본 정보를 저장하는 테이블
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,           -- Discord 유저 ID
    display_name TEXT NOT NULL,            -- 서버에서 사용하는 닉네임
    balance INTEGER NOT NULL DEFAULT 0,     -- 재화 (정수형으로 저장)
    birthday TEXT                          -- 생일 (YYYY-MM-DD)
);

-- 상점에 등록된 상품 정보를 저장하는 테이블
CREATE TABLE IF NOT EXISTS shop_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 상품 고유 ID
    item_type TEXT NOT NULL,               -- 'ROLE' 또는 'ITEM'
    name TEXT NOT NULL UNIQUE,             -- 상품 이름 (역할 이름 또는 아이템 이름)
    emoji TEXT,                            -- 상품 이모지
    price INTEGER NOT NULL,                -- 가격
    description TEXT,                      -- 상품 설명
    role_id INTEGER,                       -- 상품이 역할일 경우 Discord 역할 ID
    duration_days INTEGER                  -- 역할 기간 (0은 영구)
);

-- 유저가 보유한 아이템 목록
CREATE TABLE IF NOT EXISTS user_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    shop_item_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (shop_item_id) REFERENCES shop_items(id) ON DELETE CASCADE
);

-- 유저가 보유한 기간제 역할 목록
CREATE TABLE IF NOT EXISTS temporary_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,              -- 만료 시간 (ISO 8601 형식)
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 유저의 일일 활동량 기록
CREATE TABLE IF NOT EXISTS daily_activity (
    user_id INTEGER NOT NULL,
    activity_date TEXT NOT NULL,           -- 'YYYY-MM-DD' 형식
    message_count INTEGER NOT NULL DEFAULT 0,
    voice_seconds INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, activity_date),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 처벌 내역을 기록하는 테이블
CREATE TABLE IF NOT EXISTS moderation_logs (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 사건 ID
    user_id INTEGER NOT NULL,                  -- 대상 유저 ID
    moderator_id INTEGER NOT NULL,             -- 관리자 ID
    action TEXT NOT NULL,                      -- 처벌 종류 ('WARN', 'BAN')
    reason TEXT,                               -- 사유
    count INTEGER,                             -- 경고 횟수 (경고 처벌 시)
    created_at TEXT NOT NULL,                  -- 처벌 시간 (ISO 8601)
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (moderator_id) REFERENCES users(user_id) ON DELETE CASCADE
);