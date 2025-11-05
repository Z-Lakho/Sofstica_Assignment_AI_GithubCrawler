-- Create table if not exists
CREATE TABLE IF NOT EXISTS repositories (
    id SERIAL PRIMARY KEY,
    name_with_owner VARCHAR(255) UNIQUE NOT NULL,
    stargazer_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'  -- Flexible for future data like issues, PRs
);

-- Index for fast lookups/updates
CREATE INDEX IF NOT EXISTS idx_name_with_owner ON repositories(name_with_owner);