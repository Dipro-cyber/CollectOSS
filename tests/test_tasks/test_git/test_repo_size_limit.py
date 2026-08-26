import unittest
from unittest.mock import MagicMock, patch
import collectoss.tasks.github.util.github_data_access
from collectoss.tasks.git.util.facade_worker.facade_worker.repofetch import check_repo_size_limit, GitCloneError


class TestRepoSizeLimit(unittest.TestCase):

    def setUp(self):
        self.github_access_patcher = patch("collectoss.tasks.github.util.github_data_access.GithubDataAccess.__init__", return_value=None)
        self.mock_github_init = self.github_access_patcher.start()

    def tearDown(self):
        self.github_access_patcher.stop()

    def test_size_limit_disabled(self):
        allowed, reported_kb, estimated_kb = check_repo_size_limit("https://github.com/chaoss/CollectOSS", 0)
        self.assertTrue(allowed)
        self.assertIsNone(reported_kb)
        self.assertIsNone(estimated_kb)

    @patch("collectoss.tasks.github.util.github_data_access.GithubDataAccess.get_resource")
    def test_github_repo_under_limit(self, mock_get_resource):
        mock_get_resource.return_value = {"size": 1000}
        allowed, reported_kb, estimated_kb = check_repo_size_limit(
            "https://github.com/chaoss/CollectOSS", max_clone_size_kb=2000, clone_size_safety_margin=0.5
        )
        self.assertTrue(allowed)
        self.assertEqual(reported_kb, 1000)
        self.assertEqual(estimated_kb, 1500.0)

    @patch("collectoss.tasks.github.util.github_data_access.GithubDataAccess.get_resource")
    def test_github_repo_exceeds_limit(self, mock_get_resource):
        mock_get_resource.return_value = {"size": 2000}
        allowed, reported_kb, estimated_kb = check_repo_size_limit(
            "https://github.com/chaoss/CollectOSS", max_clone_size_kb=2500, clone_size_safety_margin=0.5
        )
        self.assertFalse(allowed)
        self.assertEqual(reported_kb, 2000)
        self.assertEqual(estimated_kb, 3000.0)

    @patch("httpx.get")
    def test_gitlab_repo_exceeds_limit(self, mock_httpx_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"statistics": {"repository_size": 5242880}} # 5120 KB
        mock_httpx_get.return_value = mock_response

        allowed, reported_kb, estimated_kb = check_repo_size_limit(
            "https://gitlab.com/group/project", max_clone_size_kb=5000, clone_size_safety_margin=0.5
        )
        self.assertFalse(allowed)
        self.assertEqual(reported_kb, 5120)
        self.assertEqual(estimated_kb, 7680.0)

    @patch("collectoss.tasks.github.util.github_data_access.GithubDataAccess.get_resource")
    def test_api_error_fallback(self, mock_get_resource):
        mock_get_resource.side_effect = Exception("API rate limit exceeded")
        allowed, reported_kb, estimated_kb = check_repo_size_limit(
            "https://github.com/chaoss/CollectOSS", max_clone_size_kb=1000, clone_size_safety_margin=0.5
        )
        self.assertTrue(allowed)
        self.assertIsNone(reported_kb)
        self.assertIsNone(estimated_kb)


if __name__ == "__main__":
    unittest.main()
