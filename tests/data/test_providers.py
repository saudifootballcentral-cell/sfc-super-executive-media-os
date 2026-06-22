"""Provider tests — Package 10A (fixture fallback paths)."""

from __future__ import annotations

import pytest

from sfc.data.providers.x_provider import XDataProvider
from sfc.data.providers.youtube_provider import YouTubeDataProvider
from sfc.data.providers.google_trends_provider import GoogleTrendsProvider
from sfc.data.providers.rss_provider import RSSProvider
from sfc.data.providers.csv_json_provider import CSVJSONProvider


class TestXDataProvider:
    def setup_method(self):
        self.provider = XDataProvider()

    def test_data_source_is_mock_fixture_without_credentials(self):
        assert self.provider.data_source == "mock_fixture"

    def test_is_available_false_without_credentials(self):
        assert self.provider.is_available() is False

    @pytest.mark.asyncio
    async def test_fetch_returns_list(self):
        results = await self.provider.fetch("#AlHilal")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_fetch_fixture_returns_trend_data(self):
        results = await self.provider.fetch("AlHilal")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_fetch_fixture_has_tweet_volume(self):
        results = await self.provider.fetch("SPL")
        assert all("tweet_volume" in r for r in results)

    @pytest.mark.asyncio
    async def test_fetch_unknown_query_returns_default(self):
        results = await self.provider.fetch("zzz_unknown_topic_999")
        assert len(results) > 0


class TestYouTubeDataProvider:
    def setup_method(self):
        self.provider = YouTubeDataProvider()

    def test_data_source_is_mock_fixture_without_credentials(self):
        assert self.provider.data_source == "mock_fixture"

    def test_is_available_false_without_api_key(self):
        assert self.provider.is_available() is False

    @pytest.mark.asyncio
    async def test_fetch_channel_returns_list(self):
        results = await self.provider.fetch("channel")
        assert isinstance(results, list)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_fetch_channel_has_subscriber_count(self):
        results = await self.provider.fetch("channel")
        assert "subscriber_count" in results[0]

    @pytest.mark.asyncio
    async def test_fetch_short_returns_short_data(self):
        results = await self.provider.fetch("youtube short")
        assert len(results) == 1
        assert int(results[0].get("views", 0)) > 0

    @pytest.mark.asyncio
    async def test_fetch_default_returns_data(self):
        results = await self.provider.fetch("some video")
        assert len(results) == 1


class TestGoogleTrendsProvider:
    def setup_method(self):
        self.provider = GoogleTrendsProvider()

    def test_data_source_mock_without_env(self):
        assert self.provider.data_source == "mock_fixture"

    def test_is_available_false_without_env(self):
        assert self.provider.is_available() is False

    @pytest.mark.asyncio
    async def test_fetch_returns_list(self):
        results = await self.provider.fetch("Al Hilal Champions League run")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_fetch_fixture_has_score(self):
        results = await self.provider.fetch("Al Hilal Champions League run")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_fetch_unknown_falls_back_gracefully(self):
        results = await self.provider.fetch("completely unknown entity xyz")
        assert isinstance(results, list)


class TestRSSProvider:
    def setup_method(self):
        self.provider = RSSProvider()

    def test_data_source_mock_without_env(self):
        assert self.provider.data_source == "mock_fixture"

    def test_is_available_false_without_env(self):
        assert self.provider.is_available() is False

    @pytest.mark.asyncio
    async def test_fetch_returns_list(self):
        results = await self.provider.fetch("Al Hilal")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_fetch_has_headline(self):
        results = await self.provider.fetch("Al Hilal")
        assert all("headline" in r for r in results)

    @pytest.mark.asyncio
    async def test_fetch_unknown_returns_default_items(self):
        results = await self.provider.fetch("zzz_unknown_topic")
        assert len(results) > 0


class TestCSVJSONProvider:
    def setup_method(self):
        self.provider = CSVJSONProvider()

    def test_data_source_is_csv_import(self):
        assert self.provider.data_source == "csv_import"

    @pytest.mark.asyncio
    async def test_fetch_empty_imports_dir_returns_empty(self, tmp_path):
        provider = CSVJSONProvider(imports_dir=tmp_path)
        results = await provider.fetch("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_json_file(self, tmp_path):
        import json
        data = [{"term": "Al Hilal", "tweet_volume": 125000}]
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data))
        provider = CSVJSONProvider(imports_dir=tmp_path)
        results = await provider.fetch("Al Hilal")
        assert len(results) == 1
        assert results[0]["term"] == "Al Hilal"

    @pytest.mark.asyncio
    async def test_fetch_csv_file(self, tmp_path):
        csv_content = "term,tweet_volume\nAlHilal,120000\nAlNassr,95000\n"
        p = tmp_path / "test.csv"
        p.write_text(csv_content)
        provider = CSVJSONProvider(imports_dir=tmp_path)
        results = await provider.fetch("AlHilal")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_fetch_with_explicit_file_path(self, tmp_path):
        import json
        data = [{"term": "SPL", "tweet_volume": 80000}]
        p = tmp_path / "explicit.json"
        p.write_text(json.dumps(data))
        provider = CSVJSONProvider(imports_dir=tmp_path)
        results = await provider.fetch("SPL", file_path=str(p))
        assert len(results) == 1
