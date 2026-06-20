-- SFC Super Executive Media OS — PostgreSQL schema (Package 2+ persistence)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Episodic memory
CREATE TABLE IF NOT EXISTS episodes (
    episode_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id       TEXT NOT NULL,
    task_type    TEXT NOT NULL,
    event        TEXT NOT NULL,
    decision     TEXT NOT NULL,
    result       TEXT NOT NULL,
    lesson       TEXT NOT NULL,
    division     TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_episodes_run_id ON episodes(run_id);
CREATE INDEX IF NOT EXISTS idx_episodes_division ON episodes(division);

-- Global memory
CREATE TABLE IF NOT EXISTS global_memory (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    namespace  TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(namespace, key)
);
CREATE INDEX IF NOT EXISTS idx_global_memory_ns ON global_memory(namespace);

-- Knowledge graph entities
CREATE TABLE IF NOT EXISTS kg_entities (
    entity_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type TEXT NOT NULL,
    name        TEXT NOT NULL UNIQUE,
    attributes  JSONB NOT NULL DEFAULT '{}',
    aliases     TEXT[] NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Knowledge graph relationships
CREATE TABLE IF NOT EXISTS kg_relationships (
    relationship_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_type TEXT NOT NULL,
    source_entity_id  UUID REFERENCES kg_entities(entity_id),
    target_entity_id  UUID REFERENCES kg_entities(entity_id),
    attributes        JSONB NOT NULL DEFAULT '{}',
    confidence        FLOAT NOT NULL DEFAULT 100.0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_kg_rel_source ON kg_relationships(source_entity_id);

-- Content run log
CREATE TABLE IF NOT EXISTS content_runs (
    run_id           TEXT PRIMARY KEY,
    task_type        TEXT NOT NULL,
    pipeline_stage   TEXT NOT NULL,
    approved_count   INT NOT NULL DEFAULT 0,
    rejected_count   INT NOT NULL DEFAULT 0,
    estimated_reach  BIGINT NOT NULL DEFAULT 0,
    total_cost_usd   FLOAT NOT NULL DEFAULT 0.0,
    started_at       TIMESTAMPTZ NOT NULL,
    completed_at     TIMESTAMPTZ,
    state_snapshot   JSONB
);
