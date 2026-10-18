import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from app.storage.workspace_lease import (
    WORKSPACE_LOCK_NAME,
    WorkspaceLeaseError,
    acquire_workspace_lease,
)

PROBE = """
import sys
from pathlib import Path
from app.storage.workspace_lease import acquire_workspace_lease, WorkspaceLeaseError
try:
    with acquire_workspace_lease(Path(sys.argv[1])):
        print('acquired', flush=True)
except WorkspaceLeaseError as error:
    print(error.code, flush=True)
    raise SystemExit(3)
"""

HOLDER = """
import sys
from pathlib import Path
from app.storage.workspace_lease import acquire_workspace_lease
with acquire_workspace_lease(Path(sys.argv[1])):
    Path(sys.argv[2]).write_text('ready', encoding='utf-8')
    sys.stdin.readline()
"""


def _environment():
    return {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])}


def _probe(root):
    return subprocess.run(
        [sys.executable, "-c", PROBE, str(root)],
        env=_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )


def _wait_until_ready(process, ready):
    deadline = time.monotonic() + 15
    while not ready.exists():
        if process.poll() is not None:
            raise AssertionError(f"Lease holder exited before readiness: {process.returncode}")
        if time.monotonic() >= deadline:
            raise AssertionError("Lease holder readiness timed out")
        time.sleep(0.02)


def test_lease_acquires_immediately_and_conflicts_in_same_process(tmp_path):
    root = tmp_path / "workspace"
    lease = acquire_workspace_lease(root)
    try:
        with pytest.raises(WorkspaceLeaseError, match="^workspace_in_use$") as error:
            acquire_workspace_lease(root)
        assert error.value.code == "workspace_in_use"
    finally:
        lease.release()
    lease.release()
    with acquire_workspace_lease(root):
        pass


def test_canonical_alias_and_independent_roots(tmp_path):
    root = tmp_path / "한글 workspace"
    with acquire_workspace_lease(root) as lease:
        assert lease.root == root.resolve()
        with pytest.raises(WorkspaceLeaseError, match="^workspace_in_use$"):
            acquire_workspace_lease(root / "unused" / "..")
        with acquire_workspace_lease(tmp_path / "independent"):
            pass


def test_release_after_context_error_keeps_stable_lock_file(tmp_path):
    lock_path = tmp_path / WORKSPACE_LOCK_NAME
    with pytest.raises(ValueError, match="synthetic"):
        with acquire_workspace_lease(tmp_path):
            identity = lock_path.stat().st_ino
            raise ValueError("synthetic")
    assert lock_path.exists()
    assert lock_path.stat().st_ino == identity
    assert lock_path.read_bytes() == b""
    with acquire_workspace_lease(tmp_path):
        assert lock_path.stat().st_ino == identity


def test_stale_pid_text_is_not_ownership_and_is_never_rewritten(tmp_path):
    lock_path = tmp_path / WORKSPACE_LOCK_NAME
    content = b'{"pid":1,"stale":true}'
    lock_path.write_bytes(content)
    identity = lock_path.stat().st_ino
    with acquire_workspace_lease(tmp_path):
        for _ in range(3):
            with pytest.raises(WorkspaceLeaseError, match="^workspace_in_use$"):
                acquire_workspace_lease(tmp_path)
    assert lock_path.stat().st_ino == identity
    assert lock_path.read_bytes() == content


def test_lease_descriptor_is_not_inherited_and_released_lease_cannot_reenter(tmp_path):
    lease = acquire_workspace_lease(tmp_path)
    assert lease._descriptor is not None
    assert os.get_inheritable(lease._descriptor) is False
    lease.release()
    with pytest.raises(WorkspaceLeaseError, match="^workspace_lease_unavailable$"):
        lease.__enter__()


def test_nested_entry_of_same_lease_cannot_release_outer_ownership(tmp_path):
    with acquire_workspace_lease(tmp_path) as lease:
        with pytest.raises(WorkspaceLeaseError, match="^workspace_lease_unavailable$"):
            with lease:
                pass
        with pytest.raises(WorkspaceLeaseError, match="^workspace_in_use$"):
            acquire_workspace_lease(tmp_path)


@pytest.mark.parametrize("invalid", ["root_file", "lock_directory", "hard_link"])
def test_invalid_lock_location_is_rejected_without_path_disclosure(tmp_path, invalid):
    root = tmp_path / "private workspace"
    if invalid == "root_file":
        root.write_bytes(b"private original")
    else:
        root.mkdir()
        if invalid == "lock_directory":
            (root / WORKSPACE_LOCK_NAME).mkdir()
        else:
            original = tmp_path / "original"
            original.write_bytes(b"private original")
            os.link(original, root / WORKSPACE_LOCK_NAME)
    with pytest.raises(WorkspaceLeaseError, match="^workspace_lease_unavailable$") as error:
        acquire_workspace_lease(root)
    assert str(root) not in str(error.value)
    if invalid == "hard_link":
        assert original.read_bytes() == b"private original"


def test_symlink_lock_is_rejected_without_touching_target(tmp_path):
    target = tmp_path / "target"
    target.write_bytes(b"private original")
    root = tmp_path / "workspace"
    root.mkdir()
    try:
        (root / WORKSPACE_LOCK_NAME).symlink_to(target)
    except OSError as error:
        pytest.skip(f"Symlink creation not available on this test host: {error.errno}")
    with pytest.raises(WorkspaceLeaseError, match="^workspace_lease_unavailable$"):
        acquire_workspace_lease(root)
    assert target.read_bytes() == b"private original"


def test_parent_lease_rejects_real_subprocess_then_allows_retry(tmp_path):
    with acquire_workspace_lease(tmp_path):
        rejected = _probe(tmp_path)
    assert rejected.returncode == 3, rejected.stderr
    assert rejected.stdout.strip() == "workspace_in_use"
    accepted = _probe(tmp_path)
    assert accepted.returncode == 0, accepted.stderr
    assert accepted.stdout.strip() == "acquired"


@pytest.mark.parametrize("termination", ["normal", "killed"])
def test_real_subprocess_lease_releases_after_exit_or_crash(tmp_path, termination):
    root = tmp_path / "한글 workspace"
    ready = tmp_path / "holder-ready"
    process = subprocess.Popen(
        [sys.executable, "-c", HOLDER, str(root), str(ready)],
        env=_environment(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        _wait_until_ready(process, ready)
        identity = (root / WORKSPACE_LOCK_NAME).stat().st_ino
        with pytest.raises(WorkspaceLeaseError, match="^workspace_in_use$"):
            acquire_workspace_lease(root)
        rejected = _probe(root)
        assert rejected.returncode == 3, rejected.stderr
        if termination == "killed":
            process.kill()
            process.communicate(timeout=10)
            assert process.returncode != 0
        else:
            _, stderr = process.communicate("\n", timeout=10)
            assert process.returncode == 0, stderr
        with acquire_workspace_lease(root):
            assert (root / WORKSPACE_LOCK_NAME).stat().st_ino == identity
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)
