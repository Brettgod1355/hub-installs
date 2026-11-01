import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import record_releases  # noqa: E402


def setUpModule():
    global _quiet
    _quiet = contextlib.redirect_stdout(io.StringIO())
    _quiet.__enter__()


def tearDownModule():
    _quiet.__exit__(None, None, None)


def plugin(slug, version, status="ok"):
    return {"slug": slug, "name": slug.title(), "version": version, "status": status}


def make_root(plugins, releases=None):
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "data"))
    with open(os.path.join(root, "data", "health.json"), "w", encoding="utf-8") as f:
        json.dump({"plugins": plugins}, f)
    if releases is not None:
        with open(os.path.join(root, "data", "releases.csv"), "w", encoding="utf-8", newline="") as f:
            f.write(releases)
    return root


def read(root):
    with open(os.path.join(root, "data", "releases.csv"), encoding="utf-8", newline="") as f:
        return f.read()


class RecordReleasesTest(unittest.TestCase):
    def test_a_new_version_gets_a_row_dated_today(self):
        root = make_root([plugin("a", "1.1")], "date,plugin,version\n2026-10-01,a,1.0\n")
        self.assertEqual(record_releases.run(root, "2026-11-02"), [["2026-11-02", "a", "1.1"]])
        self.assertEqual(read(root), "date,plugin,version\n2026-10-01,a,1.0\n2026-11-02,a,1.1\n")

    def test_the_same_version_adds_nothing(self):
        before = "date,plugin,version\n2026-10-01,a,1.0\n"
        root = make_root([plugin("a", "1.0")], before)
        self.assertEqual(record_releases.run(root, "2026-11-02"), [])
        self.assertEqual(read(root), before)

    def test_a_plugin_seen_first_is_its_release(self):
        root = make_root([plugin("b", "1.0")])
        record_releases.run(root, "2026-11-02")
        self.assertEqual(read(root), "date,plugin,version\n2026-11-02,b,1.0\n")

    def test_only_a_version_players_can_install_counts(self):
        root = make_root([plugin("a", "1.1", "unavailable"), plugin("b", "2.0", "pending")],
                         "date,plugin,version\n2026-10-01,a,1.0\n")
        self.assertEqual(record_releases.run(root, "2026-11-02"), [])

    def test_compares_with_the_latest_row_not_any_row(self):
        root = make_root([plugin("a", "1.0")], "date,plugin,version\n2026-10-01,a,1.0\n2026-10-05,a,1.1\n")
        self.assertEqual(record_releases.run(root, "2026-11-02"), [["2026-11-02", "a", "1.0"]])

    def test_no_health_file_is_not_an_error(self):
        root = tempfile.mkdtemp()
        self.assertEqual(record_releases.run(root, "2026-11-02"), [])
        self.assertFalse(os.path.exists(os.path.join(root, "data", "releases.csv")))

    def test_a_bad_header_is_an_error(self):
        root = make_root([plugin("a", "1.0")], "when,what\n")
        with self.assertRaises(record_releases.ReleaseError):
            record_releases.run(root, "2026-11-02")


if __name__ == "__main__":
    unittest.main()
