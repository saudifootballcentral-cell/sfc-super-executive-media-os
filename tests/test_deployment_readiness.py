"""Deployment readiness tests — verify Railway Docker setup is complete."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).parents[1]


class TestDockerfile:
    def test_root_dockerfile_exists(self) -> None:
        assert (ROOT / "Dockerfile").exists(), "Dockerfile missing at repo root — Railway will not auto-detect it"

    def test_dockerfile_installs_ffmpeg(self) -> None:
        content = (ROOT / "Dockerfile").read_text()
        assert "ffmpeg" in content, "ffmpeg not installed in Dockerfile — Video Intelligence live mode requires it"

    def test_dockerfile_safe_defaults(self) -> None:
        content = (ROOT / "Dockerfile").read_text()
        assert "LIVE_PUBLISHING_ENABLED=false" in content, "LIVE_PUBLISHING_ENABLED must default to false"
        assert "VIDEO_PROCESSING_ENABLED=false" in content, "VIDEO_PROCESSING_ENABLED must default to false"
        assert "GENERATE_REAL_ASSETS=false" in content, "GENERATE_REAL_ASSETS must default to false"

    def test_dockerfile_non_root_user(self) -> None:
        content = (ROOT / "Dockerfile").read_text()
        assert "USER sfc" in content, "Dockerfile must switch to non-root user before CMD"

    def test_dockerfile_creates_artifact_dirs(self) -> None:
        content = (ROOT / "Dockerfile").read_text()
        assert "artifacts/creative" in content
        assert "artifacts/video_intelligence" in content
        assert "artifacts/analytics_sync" in content

    def test_dockerfile_has_healthcheck(self) -> None:
        content = (ROOT / "Dockerfile").read_text()
        assert "HEALTHCHECK" in content, "Dockerfile missing HEALTHCHECK directive"
        assert "healthcheck.py" in content, "HEALTHCHECK should call scripts/healthcheck.py"


class TestRailwayConfig:
    def test_railway_toml_exists(self) -> None:
        assert (ROOT / "railway.toml").exists(), "railway.toml missing — Railway won't know which Dockerfile to use"

    def test_railway_toml_specifies_dockerfile(self) -> None:
        content = (ROOT / "railway.toml").read_text()
        assert "dockerfile" in content.lower(), "railway.toml must specify dockerfile builder"
        assert "Dockerfile" in content, "railway.toml must reference root Dockerfile"

    def test_railway_toml_has_start_command(self) -> None:
        content = (ROOT / "railway.toml").read_text()
        assert "startCommand" in content, "railway.toml must define startCommand"


class TestHealthCheck:
    def test_healthcheck_script_exists(self) -> None:
        assert (ROOT / "scripts" / "healthcheck.py").exists(), "scripts/healthcheck.py missing"

    def test_healthcheck_checks_ffmpeg(self) -> None:
        content = (ROOT / "scripts" / "healthcheck.py").read_text()
        assert "ffmpeg" in content
        assert "ffprobe" in content

    def test_healthcheck_checks_buffer_connector(self) -> None:
        content = (ROOT / "scripts" / "healthcheck.py").read_text()
        assert "BufferAPIClient" in content

    def test_healthcheck_checks_video_intelligence(self) -> None:
        content = (ROOT / "scripts" / "healthcheck.py").read_text()
        assert "video_intelligence" in content


class TestGitIgnore:
    def test_artifacts_in_gitignore(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text()
        assert "artifacts/" in gitignore, "artifacts/ must be in .gitignore — runtime outputs must not be committed"


class TestDeploymentDocs:
    def test_railway_deployment_doc_exists(self) -> None:
        assert (ROOT / "docs" / "RAILWAY_DEPLOYMENT.md").exists(), "docs/RAILWAY_DEPLOYMENT.md missing"

    def test_deployment_doc_covers_required_env_vars(self) -> None:
        content = (ROOT / "docs" / "RAILWAY_DEPLOYMENT.md").read_text()
        required = [
            "BUFFER_ACCESS_TOKEN",
            "LIVE_PUBLISHING_ENABLED",
            "VIDEO_PROCESSING_ENABLED",
            "ANTHROPIC_API_KEY",
        ]
        for var in required:
            assert var in content, f"docs/RAILWAY_DEPLOYMENT.md must document {var}"
