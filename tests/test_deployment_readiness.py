"""Deployment readiness tests — verify Railway Docker setup is complete."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).parents[1]


class TestDockerfile:
    def test_root_dockerfile_exists(self) -> None:
        assert (ROOT / "Dockerfile").exists(), "Dockerfile missing at repo root — Railway will not auto-detect it"

    def test_dockerfile_no_editable_install(self) -> None:
        content = (ROOT / "Dockerfile").read_text()
        assert "pip install -e" not in content, (
            "Editable install (-e) in Dockerfile creates a .pth file with the build-time "
            "absolute path. That path does not exist in the production stage, causing "
            "'No module named sfc'. Use 'pip install .' instead."
        )

    def test_dockerfile_package_installed_in_builder(self) -> None:
        content = (ROOT / "Dockerfile").read_text()
        builder_section = content.split("# ---- Stage 2")[0]
        assert "pip install" in builder_section and "pyproject.toml" in builder_section, (
            "The sfc package must be installed in the builder stage so the venv is "
            "self-contained when copied to the production stage."
        )

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

    def test_railway_toml_builder_uppercase(self) -> None:
        content = (ROOT / "railway.toml").read_text()
        # Railway requires uppercase enum values. Lowercase "dockerfile" is not recognised
        # and causes Railway to fall back to Railpack/Nixpacks auto-detection.
        assert 'builder = "DOCKERFILE"' in content, (
            'railway.toml must use builder = "DOCKERFILE" (uppercase). '
            'Lowercase "dockerfile" is silently ignored and Railway falls back to Railpack.'
        )

    def test_railway_toml_specifies_dockerfile_path(self) -> None:
        content = (ROOT / "railway.toml").read_text()
        assert "dockerfilePath" in content, "railway.toml must set dockerfilePath"
        assert '"Dockerfile"' in content, "dockerfilePath must point to root Dockerfile"

    def test_railway_toml_has_start_command(self) -> None:
        content = (ROOT / "railway.toml").read_text()
        assert "startCommand" in content, "railway.toml must define startCommand"

    def test_railway_toml_restart_policy_uppercase(self) -> None:
        content = (ROOT / "railway.toml").read_text()
        assert "ON_FAILURE" in content, (
            'restartPolicyType must be "ON_FAILURE" (uppercase) — Railway enum values are case-sensitive.'
        )


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


class TestRailwayWorker:
    def test_railway_worker_exists(self) -> None:
        assert (ROOT / "scripts" / "railway_worker.py").exists(), (
            "scripts/railway_worker.py missing — this is the production start command for Railway"
        )

    def test_dockerfile_cmd_uses_railway_worker(self) -> None:
        content = (ROOT / "Dockerfile").read_text()
        assert "railway_worker.py" in content, (
            "Dockerfile CMD must use railway_worker.py — run_demo.py exits after one scenario "
            "and is not suitable as a long-running Railway process"
        )

    def test_railway_toml_start_command_uses_worker(self) -> None:
        content = (ROOT / "railway.toml").read_text()
        assert "railway_worker.py" in content, (
            "railway.toml startCommand must use railway_worker.py"
        )

    def test_worker_imports_master_orchestrator(self) -> None:
        content = (ROOT / "scripts" / "railway_worker.py").read_text()
        assert "MasterOrchestrator" in content, "worker must import and use MasterOrchestrator"

    def test_worker_does_not_publish_by_default(self) -> None:
        content = (ROOT / "scripts" / "railway_worker.py").read_text()
        assert "LIVE_PUBLISHING_ENABLED" in content, "worker must check LIVE_PUBLISHING_ENABLED"
        assert '"false"' in content or "false" in content, (
            "worker must default to dry-run (LIVE_PUBLISHING_ENABLED=false)"
        )

    def test_worker_verifies_ffmpeg(self) -> None:
        content = (ROOT / "scripts" / "railway_worker.py").read_text()
        assert "ffmpeg" in content and "ffprobe" in content, (
            "worker must verify ffmpeg and ffprobe at startup"
        )

    def test_worker_has_heartbeat(self) -> None:
        content = (ROOT / "scripts" / "railway_worker.py").read_text()
        assert "heartbeat" in content.lower() or "sleep" in content, (
            "worker must have a heartbeat/sleep loop to stay alive"
        )

    def test_worker_exits_nonzero_on_fatal_error(self) -> None:
        content = (ROOT / "scripts" / "railway_worker.py").read_text()
        assert "sys.exit(1)" in content, (
            "worker must call sys.exit(1) on fatal startup errors"
        )


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
