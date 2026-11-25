from unittest.mock import MagicMock, patch

from app.util.git_util import fetch_remote_branches_via_git


def test_fetch_remote_branches_via_git_parses_branches() -> None:
    fake_output = (
        "4c3a1b2c3d4e refs/heads/10.x\n"
        "8f9a0b1c2d3e refs/heads/alpha\n"
        "1a2b3c4d5e6f refs/heads/feat/awesome-feature\n"
        "9f8e7d6c5b4a refs/heads/main\n"
        "5b4a3c2d1e0f refs/heads/next\n"
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=fake_output)
        branches = fetch_remote_branches_via_git("https://github.com/trpc/trpc.git")

    assert branches == ["10.x", "alpha", "feat/awesome-feature", "main", "next"]
