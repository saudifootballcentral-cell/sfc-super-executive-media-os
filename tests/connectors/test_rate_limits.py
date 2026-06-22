"""Rate limit and observability tests — Package 9A."""

from __future__ import annotations

import pytest

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.buffer.service import BufferService
from sfc.connectors.x.service import XService
from sfc.connectors.youtube.service import YouTubeService


class TestConnectorObservability:
    def test_initial_state_all_zeros(self):
        obs = ConnectorObservability(connector="test")
        assert obs.requests_made == 0
        assert obs.successful_requests == 0
        assert obs.failed_requests == 0
        assert obs.api_errors == 0
        assert obs.rate_limit_hits == 0
        assert obs.avg_latency_ms == 0.0

    def test_record_success_increments_counters(self):
        obs = ConnectorObservability(connector="test")
        obs.record_success(latency_ms=120.0)
        assert obs.requests_made == 1
        assert obs.successful_requests == 1
        assert obs.failed_requests == 0

    def test_record_failure_increments_counters(self):
        obs = ConnectorObservability(connector="test")
        obs.record_failure("connection_timeout")
        assert obs.requests_made == 1
        assert obs.failed_requests == 1
        assert obs.api_errors == 1
        assert obs.rate_limit_hits == 0

    def test_rate_limited_failure_increments_rate_limit_hits(self):
        obs = ConnectorObservability(connector="test")
        obs.record_failure("429 Too Many Requests", rate_limited=True)
        assert obs.rate_limit_hits == 1
        assert obs.api_errors == 1

    def test_non_rate_limited_failure_does_not_increment_rate_limit_hits(self):
        obs = ConnectorObservability(connector="test")
        obs.record_failure("500 Internal Server Error", rate_limited=False)
        assert obs.rate_limit_hits == 0
        assert obs.api_errors == 1

    def test_success_rate_all_success(self):
        obs = ConnectorObservability(connector="test")
        for _ in range(5):
            obs.record_success()
        assert obs.success_rate == 100.0

    def test_success_rate_all_failure(self):
        obs = ConnectorObservability(connector="test")
        for _ in range(5):
            obs.record_failure("error")
        assert obs.success_rate == 0.0

    def test_success_rate_mixed(self):
        obs = ConnectorObservability(connector="test")
        obs.record_success()
        obs.record_success()
        obs.record_success()
        obs.record_failure("error")
        assert abs(obs.success_rate - 75.0) < 0.1

    def test_avg_latency_single_request(self):
        obs = ConnectorObservability(connector="test")
        obs.record_success(latency_ms=250.0)
        assert obs.avg_latency_ms == 250.0

    def test_avg_latency_multiple_requests(self):
        obs = ConnectorObservability(connector="test")
        obs.record_success(latency_ms=100.0)
        obs.record_success(latency_ms=300.0)
        assert abs(obs.avg_latency_ms - 200.0) < 1.0

    def test_avg_latency_no_latency_param(self):
        obs = ConnectorObservability(connector="test")
        obs.record_success()
        assert obs.avg_latency_ms >= 0.0

    def test_to_dict_contains_all_fields(self):
        obs = ConnectorObservability(connector="youtube")
        obs.record_success(latency_ms=150.0)
        obs.record_failure("timeout", rate_limited=True)
        d = obs.to_dict()
        assert d["connector"] == "youtube"
        assert "requests_made" in d
        assert "successful_requests" in d
        assert "failed_requests" in d
        assert "api_errors" in d
        assert "rate_limit_hits" in d
        assert "avg_latency_ms" in d
        assert "success_rate" in d

    def test_cumulative_rate_limit_hits(self):
        obs = ConnectorObservability(connector="test")
        for _ in range(5):
            obs.record_failure("429", rate_limited=True)
        assert obs.rate_limit_hits == 5

    def test_multiple_connectors_independent(self):
        obs_yt = ConnectorObservability(connector="youtube")
        obs_x = ConnectorObservability(connector="x")
        obs_yt.record_failure("error", rate_limited=True)
        assert obs_x.rate_limit_hits == 0
        assert obs_yt.rate_limit_hits == 1


class TestYouTubeObservability:
    def test_observability_exposed_via_property(self):
        service = YouTubeService()
        assert service.observability is service._observability

    @pytest.mark.asyncio
    async def test_observability_tracks_upload(self):
        from sfc.connectors.youtube.models import VideoUploadRequest

        service = YouTubeService()
        before = service.observability.successful_requests
        await service.upload_video(VideoUploadRequest(title="Obs test"))
        assert service.observability.successful_requests > before

    def test_observability_connector_name(self):
        service = YouTubeService()
        assert service.observability.connector == "youtube"

    def test_observability_to_dict_connector_field(self):
        service = YouTubeService()
        d = service.observability.to_dict()
        assert d["connector"] == "youtube"

    def test_record_failure_propagates_to_report(self):
        service = YouTubeService()
        service._observability.record_failure("mock_error")
        assert service.observability.api_errors >= 1


class TestXObservability:
    def test_x_observability_connector_name(self):
        service = XService()
        assert service.observability.connector == "x"

    def test_x_observability_rate_limit_tracking(self):
        service = XService()
        service._observability.record_failure("429", rate_limited=True)
        assert service.observability.rate_limit_hits == 1

    def test_x_observability_failure_tracking(self):
        service = XService()
        service._observability.record_failure("server_error")
        assert service.observability.api_errors == 1
        assert service.observability.rate_limit_hits == 0

    def test_x_observability_success_tracking(self):
        service = XService()
        service._observability.record_success(latency_ms=90.0)
        assert service.observability.successful_requests == 1
        assert service.observability.avg_latency_ms == 90.0

    @pytest.mark.asyncio
    async def test_x_report_shows_api_errors(self):
        service = XService()
        service._observability.record_failure("mock_api_error")
        report = await service.generate_report()
        assert report.api_errors >= 1


class TestBufferObservability:
    def test_buffer_observability_connector_name(self):
        service = BufferService()
        assert service.observability.connector == "buffer"

    def test_buffer_rate_limit_tracking(self):
        service = BufferService()
        service._observability.record_failure("buffer_rate_limit", rate_limited=True)
        assert service.observability.rate_limit_hits == 1

    @pytest.mark.asyncio
    async def test_buffer_publish_increments_success(self):
        from sfc.connectors.buffer.models import BufferPlatform
        service = BufferService()
        before = service.observability.successful_requests
        await service.publish_to_platforms("Test", [BufferPlatform.INSTAGRAM])
        assert service.observability.successful_requests > before

    @pytest.mark.asyncio
    async def test_buffer_report_shows_rate_limit_hits(self):
        service = BufferService()
        service._observability.record_failure("429 rate limited", rate_limited=True)
        report = await service.generate_report()
        assert report.rate_limit_hits >= 1
