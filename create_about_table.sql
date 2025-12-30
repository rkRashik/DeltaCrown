-- UP-PHASE15: Create ProfileAboutItem table
CREATE TABLE IF NOT EXISTS user_profile_profileaboutitem (
    id SERIAL PRIMARY KEY,
    user_profile_id INTEGER NOT NULL REFERENCES user_profile_userprofile(id) ON DELETE CASCADE,
    item_type VARCHAR(20) NOT NULL,
    visibility VARCHAR(20) NOT NULL DEFAULT 'public',
    source_model VARCHAR(100),
    source_id INTEGER,
    display_text VARCHAR(200) NOT NULL,
    icon_emoji VARCHAR(10),
    order_index INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_up_about_profile_active 
    ON user_profile_profileaboutitem(user_profile_id, is_active, order_index);

CREATE INDEX IF NOT EXISTS idx_up_about_profile_type 
    ON user_profile_profileaboutitem(user_profile_id, item_type);
