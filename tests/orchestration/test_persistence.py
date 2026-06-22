"""Tests for PersistenceProvider implementations — Package 10D."""

from __future__ import annotations

import pytest

from sfc.orchestration.master_state import MasterState, RunStatus
from sfc.orchestration.persistence import InMemoryPersistence, JSONLAuditPersistence


class TestInMemoryPersistence:
    def setup_method(self):
        self.p = InMemoryPersistence()

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        state = MasterState()
        await self.p.save(state)
        loaded = await self.p.load(state.run_id)
        assert loaded is not None
        assert loaded.run_id == state.run_id

    @pytest.mark.asyncio
    async def test_load_unknown_returns_none(self):
        result = await self.p.load("nonexistent-run-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_run_count_increases(self):
        assert self.p.run_count == 0
        await self.p.save(MasterState())
        assert self.p.run_count == 1
        await self.p.save(MasterState())
        assert self.p.run_count == 2

    @pytest.mark.asyncio
    async def test_save_twice_same_run_overwrites(self):
        state = MasterState()
        await self.p.save(state)
        state.status = RunStatus.RUNNING
        await self.p.save(state)
        loaded = await self.p.load(state.run_id)
        assert loaded.status == RunStatus.RUNNING
        assert self.p.run_count == 1

    @pytest.mark.asyncio
    async def test_delete_removes_run(self):
        state = MasterState()
        await self.p.save(state)
        await self.p.delete(state.run_id)
        loaded = await self.p.load(state.run_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_list_runs_returns_recent(self):
        for _ in range(3):
            await self.p.save(MasterState())
        runs = await self.p.list_runs(limit=10)
        assert len(runs) == 3

    @pytest.mark.asyncio
    async def test_list_runs_limit(self):
        for _ in range(5):
            await self.p.save(MasterState())
        runs = await self.p.list_runs(limit=2)
        assert len(runs) == 2

    @pytest.mark.asyncio
    async def test_loaded_state_has_correct_fields(self):
        state = MasterState(task_type="transfer_news", dry_run=False)
        await self.p.save(state)
        loaded = await self.p.load(state.run_id)
        assert loaded.task_type == "transfer_news"
        assert loaded.dry_run is False


class TestJSONLAuditPersistence:
    @pytest.mark.asyncio
    async def test_save_and_load(self, tmp_path):
        p = JSONLAuditPersistence(audit_dir=tmp_path)
        state = MasterState()
        await p.save(state)
        loaded = await p.load(state.run_id)
        assert loaded is not None
        assert loaded.run_id == state.run_id

    @pytest.mark.asyncio
    async def test_file_created_on_save(self, tmp_path):
        p = JSONLAuditPersistence(audit_dir=tmp_path)
        state = MasterState()
        await p.save(state)
        files = list(tmp_path.glob("*.jsonl"))
        assert len(files) == 1

    @pytest.mark.asyncio
    async def test_multiple_saves_appends_lines(self, tmp_path):
        p = JSONLAuditPersistence(audit_dir=tmp_path)
        state = MasterState()
        await p.save(state)
        state.status = RunStatus.RUNNING
        await p.save(state)
        content = (tmp_path / f"{state.run_id}.jsonl").read_text().strip().split("\n")
        assert len(content) == 2

    @pytest.mark.asyncio
    async def test_load_returns_last_snapshot(self, tmp_path):
        p = JSONLAuditPersistence(audit_dir=tmp_path)
        state = MasterState()
        await p.save(state)
        state.status = RunStatus.COMPLETED
        await p.save(state)
        loaded = await p.load(state.run_id)
        assert loaded.status == RunStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_delete_removes_file(self, tmp_path):
        p = JSONLAuditPersistence(audit_dir=tmp_path)
        state = MasterState()
        await p.save(state)
        await p.delete(state.run_id)
        assert not (tmp_path / f"{state.run_id}.jsonl").exists()

    @pytest.mark.asyncio
    async def test_load_unknown_returns_none(self, tmp_path):
        p = JSONLAuditPersistence(audit_dir=tmp_path)
        result = await p.load("unknown-id")
        assert result is None
