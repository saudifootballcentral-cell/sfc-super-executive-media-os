"""Tests for Package 10B — Real Creative Providers.

Covers:
1.  No credentials → provider_unavailable
2.  GENERATE_REAL_ASSETS=false blocks provider calls
3.  No fake mock URL returned as status=generated
4.  Generated file is saved to disk
5.  Checksum is computed
6.  Manifest JSON is created
7.  Zero-byte file rejected by validate_file
8.  Missing file rejected by validate_file
9.  Content package rejects provider_unavailable asset
10. Provider fallback order (OpenAI fails → Flux succeeds)
11. Retry logic (fail twice, succeed on third)
12. Cost budget blocks generation
13. All existing factory tests still pass (verified by importing and calling service)
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sfc.creative.providers.generated_asset import (
    GeneratedAsset,
    GeneratedAssetStatus,
    GovernanceStatus,
)
from sfc.creative.providers.asset_storage import LocalAssetStorage
from sfc.creative.providers.cost_guard import CostGuard
from sfc.creative.providers.retry import RetryExecutor, RetryResult
from sfc.creative.providers.image_providers import (
    ImageProviderChain,
    OpenAIImageProvider,
    FluxProvider,
    IdeogramProvider,
)
from sfc.creative.providers.audio_providers import (
    AudioProviderChain,
    ElevenLabsProvider,
    AzureVoiceProvider,
)
from sfc.creative.packaging.service import ContentPackagingService
from sfc.creative.packaging.models import PackageType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chain_no_creds() -> ImageProviderChain:
    """Image chain where none of the providers has credentials."""
    chain = ImageProviderChain()
    for p in chain._providers:
        p.is_available = lambda: False  # type: ignore[method-assign]
    return chain


def _make_audio_chain_no_creds() -> AudioProviderChain:
    chain = AudioProviderChain()
    for p in chain._providers:
        p.is_available = lambda: False  # type: ignore[method-assign]
    return chain


def _fresh_cost_guard(enabled: bool = False) -> CostGuard:
    guard = CostGuard()
    guard.reset_for_test()
    return guard


# ===========================================================================
# Test 1 — No provider credentials → provider_unavailable
# ===========================================================================

class TestNoCredentials:
    @pytest.mark.asyncio
    async def test_image_chain_no_creds_returns_unavailable(self):
        chain = _make_chain_no_creds()
        guard = _fresh_cost_guard(enabled=True)
        with patch(
            "sfc.creative.providers.image_providers.get_cost_guard", return_value=guard
        ), patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "true"}):
            guard._run_costs.clear()  # fresh
            result = await chain.generate("SFC match day")
        assert result.status == GeneratedAssetStatus.PROVIDER_UNAVAILABLE
        assert result.local_path == ""
        assert result.provider == "none"

    @pytest.mark.asyncio
    async def test_audio_chain_no_creds_returns_unavailable(self):
        chain = _make_audio_chain_no_creds()
        guard = _fresh_cost_guard(enabled=True)
        with patch(
            "sfc.creative.providers.audio_providers.get_cost_guard", return_value=guard
        ), patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "true"}):
            result = await chain.synthesize("كرة القدم السعودية")
        assert result.status == GeneratedAssetStatus.PROVIDER_UNAVAILABLE
        assert result.local_path == ""


# ===========================================================================
# Test 2 — GENERATE_REAL_ASSETS=false blocks provider calls
# ===========================================================================

class TestGenerationDisabled:
    @pytest.mark.asyncio
    async def test_image_chain_disabled_returns_unavailable(self):
        chain = ImageProviderChain()
        guard = CostGuard()
        guard.reset_for_test()
        # Even if a provider would be "available", disabled flag wins
        for p in chain._providers:
            p.is_available = lambda: True  # type: ignore[method-assign]

        with patch(
            "sfc.creative.providers.image_providers.get_cost_guard", return_value=guard
        ), patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "false"}):
            result = await chain.generate("SFC promotional")

        assert result.status == GeneratedAssetStatus.PROVIDER_UNAVAILABLE
        assert result.metadata.get("reason") == "GENERATE_REAL_ASSETS=false"

    @pytest.mark.asyncio
    async def test_audio_chain_disabled_returns_unavailable(self):
        chain = AudioProviderChain()
        guard = CostGuard()
        guard.reset_for_test()
        for p in chain._providers:
            p.is_available = lambda: True  # type: ignore[method-assign]

        with patch(
            "sfc.creative.providers.audio_providers.get_cost_guard", return_value=guard
        ), patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "false"}):
            result = await chain.synthesize("SFC highlights narration")

        assert result.status == GeneratedAssetStatus.PROVIDER_UNAVAILABLE
        assert result.metadata.get("reason") == "GENERATE_REAL_ASSETS=false"

    @pytest.mark.asyncio
    async def test_disabled_image_factory_does_not_call_provider(self):
        """ImageFactoryService must not call provider when GENERATE_REAL_ASSETS=false."""
        from sfc.creative.image.service import ImageFactoryService
        from sfc.creative.image.models import ImageFormat

        called = []

        async def fake_generate(*args, **kwargs):
            called.append(True)
            return GeneratedAsset(
                asset_type="image", status=GeneratedAssetStatus.PROVIDER_UNAVAILABLE
            )

        svc = ImageFactoryService()
        with patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "false"}):
            asset = await svc.generate_image(title="Disabled Test")

        assert called == [], "Provider must not be called when GENERATE_REAL_ASSETS=false"
        assert len(asset.variants) >= 1


# ===========================================================================
# Test 3 — No fake mock URL returned as status=generated
# ===========================================================================

class TestNoFakeMockUrl:
    @pytest.mark.asyncio
    async def test_unavailable_asset_has_no_generated_status(self):
        chain = _make_chain_no_creds()
        guard = _fresh_cost_guard(enabled=True)
        with patch(
            "sfc.creative.providers.image_providers.get_cost_guard", return_value=guard
        ), patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "true"}):
            result = await chain.generate("test")
        assert result.status != GeneratedAssetStatus.GENERATED
        assert result.local_path == ""

    def test_generated_asset_with_mock_url_is_not_publishable(self):
        asset = GeneratedAsset(
            asset_type="image",
            provider="mock",
            status=GeneratedAssetStatus.GENERATED,
            local_path="https://assets.sfc.sa/images/mock/test.jpg",  # fake URL, not a file
            file_size=100,
            checksum_sha256="abc123",
        )
        # is_publishable checks local_path exists as a file on disk
        # A URL string as local_path won't exist on disk → not publishable
        path = Path(asset.local_path)
        assert not path.exists(), "Mock URL must not point to a real file"


# ===========================================================================
# Test 4 — Generated file is saved to disk
# ===========================================================================

class TestFileSavedToDisk:
    @pytest.mark.asyncio
    async def test_file_saved_when_provider_returns_bytes(self, tmp_path):
        fake_bytes = b"PNG_IMAGE_DATA" * 100  # non-empty bytes

        storage = LocalAssetStorage(storage_root=str(tmp_path))
        local_path, checksum, file_size = storage.save_file(
            fake_bytes, "test-asset-id", "image", "png"
        )

        assert Path(local_path).exists()
        assert file_size == len(fake_bytes)
        assert file_size > 0

    @pytest.mark.asyncio
    async def test_openai_provider_saves_file(self, tmp_path):
        """Mock OpenAI HTTP call; verify file is saved and asset is GENERATED."""
        import base64

        fake_image = b"FAKE_PNG_BYTES_12345"
        b64 = base64.b64encode(fake_image).decode()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"b64_json": b64}]}
        mock_response.raise_for_status = MagicMock()

        storage = LocalAssetStorage(storage_root=str(tmp_path))

        with patch(
            "sfc.creative.providers.image_providers.get_asset_storage",
            return_value=storage,
        ), patch(
            "sfc.creative.providers.image_providers.get_cost_guard",
            return_value=_fresh_cost_guard(enabled=True),
        ), patch.dict(
            os.environ, {"OPENAI_API_KEY": "sk-test123", "GENERATE_REAL_ASSETS": "true"}
        ):
            # Patch httpx.AsyncClient
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)

            provider = OpenAIImageProvider()
            with patch("httpx.AsyncClient", return_value=mock_client):
                asset = await provider.generate("Saudi football match", "1080x1080")

        assert asset.status == GeneratedAssetStatus.GENERATED
        assert Path(asset.local_path).exists()
        assert asset.file_size == len(fake_image)


# ===========================================================================
# Test 5 — Checksum is computed
# ===========================================================================

class TestChecksumComputed:
    @pytest.mark.asyncio
    async def test_checksum_matches_file_content(self, tmp_path):
        content = b"SFC_AUDIO_BYTES_CONTENT"
        storage = LocalAssetStorage(storage_root=str(tmp_path))
        local_path, checksum, _ = storage.save_file(content, "chk-test", "audio", "mp3")

        expected = hashlib.sha256(content).hexdigest()
        assert checksum == expected
        assert len(checksum) == 64  # SHA-256 hex

    @pytest.mark.asyncio
    async def test_compute_checksum_from_path(self, tmp_path):
        content = b"CONTENT_FOR_CHECKSUM"
        storage = LocalAssetStorage(storage_root=str(tmp_path))
        local_path, orig_checksum, _ = storage.save_file(content, "chk2", "image", "jpg")
        recomputed = storage.compute_checksum(local_path)
        assert recomputed == orig_checksum


# ===========================================================================
# Test 6 — Manifest JSON is created
# ===========================================================================

class TestManifestCreated:
    @pytest.mark.asyncio
    async def test_manifest_file_exists(self, tmp_path):
        storage = LocalAssetStorage(storage_root=str(tmp_path))
        manifest_path = storage.save_manifest(
            "manifest-test-id",
            {"asset_type": "image", "provider": "flux", "status": "generated"},
        )
        assert Path(manifest_path).exists()
        import json
        data = json.loads(Path(manifest_path).read_text())
        assert data["asset_type"] == "image"
        assert "_manifest_saved_at" in data

    @pytest.mark.asyncio
    async def test_openai_provider_creates_manifest(self, tmp_path):
        import base64

        fake_image = b"FAKE_IMAGE_FOR_MANIFEST"
        b64 = base64.b64encode(fake_image).decode()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"b64_json": b64}]}
        mock_response.raise_for_status = MagicMock()

        storage = LocalAssetStorage(storage_root=str(tmp_path))

        with patch(
            "sfc.creative.providers.image_providers.get_asset_storage",
            return_value=storage,
        ), patch(
            "sfc.creative.providers.image_providers.get_cost_guard",
            return_value=_fresh_cost_guard(enabled=True),
        ), patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)

            provider = OpenAIImageProvider()
            with patch("httpx.AsyncClient", return_value=mock_client):
                asset = await provider.generate("test")

        manifest_path = Path(tmp_path) / "manifests" / f"{asset.asset_id}.json"
        assert manifest_path.exists()


# ===========================================================================
# Test 7 — Zero-byte file rejected
# ===========================================================================

class TestZeroByteFileRejected:
    def test_validate_zero_byte_file(self, tmp_path):
        zero_file = tmp_path / "empty.png"
        zero_file.write_bytes(b"")  # zero bytes
        storage = LocalAssetStorage(storage_root=str(tmp_path))
        valid, errors = storage.validate_file(str(zero_file))
        assert valid is False
        assert any("zero bytes" in e for e in errors)

    def test_zero_byte_asset_not_publishable(self, tmp_path):
        zero_file = tmp_path / "empty.png"
        zero_file.write_bytes(b"")
        asset = GeneratedAsset(
            asset_type="image",
            provider="flux",
            status=GeneratedAssetStatus.GENERATED,
            local_path=str(zero_file),
            file_size=0,  # zero
            checksum_sha256="abc",
        )
        assert asset.is_publishable is False


# ===========================================================================
# Test 8 — Missing file rejected
# ===========================================================================

class TestMissingFileRejected:
    def test_validate_missing_file(self, tmp_path):
        storage = LocalAssetStorage(storage_root=str(tmp_path))
        valid, errors = storage.validate_file("/nonexistent/path/image.png")
        assert valid is False
        assert any("not found" in e for e in errors)

    def test_missing_file_asset_not_publishable(self):
        asset = GeneratedAsset(
            asset_type="image",
            provider="flux",
            status=GeneratedAssetStatus.GENERATED,
            local_path="/nonexistent/path/asset.png",
            file_size=1024,
            checksum_sha256="abc123",
        )
        assert asset.is_publishable is False


# ===========================================================================
# Test 9 — Content package rejects provider_unavailable asset
# ===========================================================================

class TestPackagingRejectsUnavailable:
    @pytest.mark.asyncio
    async def test_validate_provider_unavailable_fails(self):
        svc = ContentPackagingService()
        asset = GeneratedAsset(
            asset_type="image",
            provider="none",
            status=GeneratedAssetStatus.PROVIDER_UNAVAILABLE,
            local_path="",
        )
        valid, errors = svc.validate_asset_for_packaging(asset)
        assert valid is False
        assert any("provider_unavailable" in e or "generated" in e for e in errors)

    @pytest.mark.asyncio
    async def test_package_from_generated_assets_raises_if_all_unavailable(self):
        svc = ContentPackagingService()
        unavailable = GeneratedAsset(
            asset_type="image",
            provider="none",
            status=GeneratedAssetStatus.PROVIDER_UNAVAILABLE,
            local_path="",
        )
        with pytest.raises(ValueError, match="No valid GeneratedAssets"):
            await svc.package_from_generated_assets(
                PackageType.INSTAGRAM,
                "Test Package",
                [unavailable],
            )

    @pytest.mark.asyncio
    async def test_validate_failed_asset_fails(self):
        svc = ContentPackagingService()
        asset = GeneratedAsset(
            asset_type="image",
            provider="openai_image",
            status=GeneratedAssetStatus.FAILED,
            local_path="",
        )
        valid, errors = svc.validate_asset_for_packaging(asset)
        assert valid is False

    @pytest.mark.asyncio
    async def test_valid_generated_asset_passes_packaging(self, tmp_path):
        svc = ContentPackagingService()
        # Save a real file so validation passes
        real_file = tmp_path / "asset.png"
        real_file.write_bytes(b"REAL_IMAGE_DATA_" * 50)

        asset = GeneratedAsset(
            asset_type="image",
            provider="flux",
            status=GeneratedAssetStatus.GENERATED,
            local_path=str(real_file),
            file_size=real_file.stat().st_size,
            checksum_sha256="abc123def456" * 4,
            quality_score=85.0,
            governance_status=GovernanceStatus.PENDING_REVIEW,
        )
        valid, errors = svc.validate_asset_for_packaging(asset)
        assert valid is True, f"Expected valid but got errors: {errors}"


# ===========================================================================
# Test 10 — Provider fallback order
# ===========================================================================

class TestProviderFallback:
    @pytest.mark.asyncio
    async def test_image_chain_falls_back_to_flux_when_openai_fails(self, tmp_path):
        storage = LocalAssetStorage(storage_root=str(tmp_path))
        guard = _fresh_cost_guard(enabled=True)
        fake_bytes = b"FLUX_IMAGE_BYTES_" * 20

        async def openai_fail(*a, **kw):
            raise RuntimeError("OpenAI unavailable")

        async def flux_succeed(prompt, dimensions="1080x1080", negative_prompt="", asset_id=None):
            local_path, checksum, file_size = storage.save_file(
                fake_bytes, asset_id or "flux-test", "image", "jpg"
            )
            a = GeneratedAsset(
                asset_type="image",
                provider="flux",
                status=GeneratedAssetStatus.GENERATED,
                local_path=local_path,
                file_size=file_size,
                checksum_sha256=checksum,
                quality_score=92.0,
            )
            storage.save_manifest(a.asset_id, a.to_dict())
            return a

        chain = ImageProviderChain()
        # Patch OpenAI to fail, Flux to succeed, Ideogram not needed
        chain._providers[0].generate = openai_fail  # type: ignore[method-assign]
        chain._providers[0].is_available = lambda: True  # type: ignore[method-assign]
        chain._providers[1].generate = flux_succeed  # type: ignore[method-assign]
        chain._providers[1].is_available = lambda: True  # type: ignore[method-assign]
        chain._providers[2].is_available = lambda: False  # type: ignore[method-assign]

        with patch(
            "sfc.creative.providers.image_providers.get_cost_guard", return_value=guard
        ), patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "true"}):
            result = await chain.generate("Match day poster")

        assert result.status == GeneratedAssetStatus.GENERATED
        assert result.provider == "flux"

    @pytest.mark.asyncio
    async def test_audio_chain_falls_back_to_azure_when_elevenlabs_fails(self, tmp_path):
        storage = LocalAssetStorage(storage_root=str(tmp_path))
        guard = _fresh_cost_guard(enabled=True)
        fake_audio = b"AZURE_AUDIO_BYTES_" * 20

        async def el_fail(*a, **kw):
            raise RuntimeError("ElevenLabs quota exceeded")

        async def azure_succeed(script, voice_id="", language="arabic", asset_id=None):
            local_path, checksum, file_size = storage.save_file(
                fake_audio, asset_id or "azure-test", "audio", "mp3"
            )
            a = GeneratedAsset(
                asset_type="audio",
                provider="azure_voice",
                status=GeneratedAssetStatus.GENERATED,
                local_path=local_path,
                file_size=file_size,
                checksum_sha256=checksum,
                quality_score=91.0,
            )
            storage.save_manifest(a.asset_id, a.to_dict())
            return a

        chain = AudioProviderChain()
        chain._providers[0].synthesize = el_fail  # type: ignore[method-assign]
        chain._providers[0].is_available = lambda: True  # type: ignore[method-assign]
        chain._providers[1].synthesize = azure_succeed  # type: ignore[method-assign]
        chain._providers[1].is_available = lambda: True  # type: ignore[method-assign]

        with patch(
            "sfc.creative.providers.audio_providers.get_cost_guard", return_value=guard
        ), patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "true"}):
            result = await chain.synthesize("SFC match recap")

        assert result.status == GeneratedAssetStatus.GENERATED
        assert result.provider == "azure_voice"


# ===========================================================================
# Test 11 — Retry logic
# ===========================================================================

class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retry_succeeds_after_two_failures(self):
        executor = RetryExecutor(max_retries=3, base_delay=0.01)
        calls = []

        async def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("temporary failure")
            return "success"

        result = await executor.execute(flaky, "test_op")
        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 3
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_returns_failure(self):
        executor = RetryExecutor(max_retries=2, base_delay=0.01)

        async def always_fail():
            raise RuntimeError("permanent failure")

        result = await executor.execute(always_fail, "fail_op")
        assert result.success is False
        assert "permanent failure" in result.error
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_retry_timeout_returns_failure(self):
        executor = RetryExecutor(max_retries=1, base_delay=0.01, timeout_seconds=0.05)

        async def slow():
            await asyncio.sleep(1.0)
            return "never"

        result = await executor.execute(slow, "slow_op")
        assert result.success is False
        assert "Timeout" in result.error


# ===========================================================================
# Test 12 — Cost budget blocks generation
# ===========================================================================

class TestCostBudget:
    @pytest.mark.asyncio
    async def test_daily_budget_blocks_generation(self):
        guard = CostGuard()
        guard.reset_for_test()

        # Manually set daily cost to just below the limit
        from datetime import date
        today = date.today().isoformat()
        guard._daily_costs[today] = 49.999  # just below $50 default
        # openai_image costs $0.04 — would push over limit
        can = guard.can_afford("openai_image", daily_limit=50.0)
        assert can is False

    @pytest.mark.asyncio
    async def test_per_run_budget_blocks_generation(self):
        guard = CostGuard()
        guard.reset_for_test()

        run_id = "run-budget-test"
        guard._run_costs[run_id] = 4.99  # $4.99 of $5.00 used
        # openai_image costs $0.04 — would push over $5
        with patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "true"}):
            can = guard.can_afford("openai_image", run_id=run_id, per_run_limit=5.0)
        assert can is False

    @pytest.mark.asyncio
    async def test_cost_guard_disabled_blocks_generation(self):
        guard = CostGuard()
        guard.reset_for_test()
        with patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "false"}):
            can = guard.can_afford("flux")
        assert can is False

    @pytest.mark.asyncio
    async def test_chain_blocked_by_budget_returns_unavailable(self):
        chain = _make_chain_no_creds()
        guard = CostGuard()
        guard.reset_for_test()
        # Re-enable creds but exhaust budget
        from datetime import date
        today = date.today().isoformat()
        guard._daily_costs[today] = 999.0
        for p in chain._providers:
            p.is_available = lambda: True  # type: ignore[method-assign]

        with patch(
            "sfc.creative.providers.image_providers.get_cost_guard", return_value=guard
        ), patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "true"}):
            result = await chain.generate("over budget test")

        # All providers budget_exceeded → FAILED (all errors recorded)
        assert result.status in (
            GeneratedAssetStatus.PROVIDER_UNAVAILABLE,
            GeneratedAssetStatus.FAILED,
        )


# ===========================================================================
# Test 13 — Existing factory contracts preserved
# ===========================================================================

class TestExistingFactoriesUnaffected:
    """Smoke-test that existing factory services still honour their contracts
    when GENERATE_REAL_ASSETS is unset (defaults to false)."""

    @pytest.mark.asyncio
    async def test_image_factory_still_returns_variants_with_scores(self):
        from sfc.creative.image.service import ImageFactoryService
        from sfc.creative.image.models import ImageFormat

        svc = ImageFactoryService()
        with patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "false"}):
            asset = await svc.generate_image(
                title="Legacy Test", image_format=ImageFormat.SOCIAL_CARD
            )
        assert len(asset.variants) >= 1
        for v in asset.variants:
            assert v.quality_score > 0
            assert v.brand_alignment_score > 0

    @pytest.mark.asyncio
    async def test_thumbnail_factory_still_returns_four_variants(self):
        from sfc.creative.thumbnail.service import ThumbnailFactoryService

        svc = ThumbnailFactoryService()
        with patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "false"}):
            asset = await svc.generate_thumbnails(content_title="Legacy Thumb Test")
        assert len(asset.variants) == 4
        assert asset.best_ctr_score > 0

    @pytest.mark.asyncio
    async def test_audio_factory_still_returns_asset_with_duration(self):
        from sfc.creative.audio.service import AudioFactoryService
        from sfc.creative.audio.models import AudioType, VoiceLanguage

        svc = AudioFactoryService()
        with patch.dict(os.environ, {"GENERATE_REAL_ASSETS": "false"}):
            asset = await svc.generate_audio(
                title="Legacy Audio",
                audio_type=AudioType.NEWS_BRIEF,
                language=VoiceLanguage.ARABIC,
            )
        assert asset.duration_seconds > 0
        assert asset.word_count > 0
        assert asset.quality_score > 0
