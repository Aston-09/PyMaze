"""
Content Hot-Reload

Story, challenge and interaction files are authored content, not code. They
are edited constantly while writing a chapter, and `uvicorn --reload` only
watches `*.py` — so a `.scene` edit would sit invisible behind an already-
running server until someone thought to restart it.

That silently serves a stale chapter, which is very hard to diagnose from the
UI: the text updates when you restart, but a background or mission you added
just... isn't there.

This module fingerprints the content directories and reloads them whenever
anything changes on disk, so the authoring loop is "save the file, refresh the
page" exactly as the content-creator workflow promises.

ponytail: stats every content file on each check, which is fine for the
low hundreds of files a single-player game has. If the content tree ever grows
large enough for that to show up in latency, swap the fingerprint for a
watchdog observer — the public interface here would not change.
"""
import os
from typing import Any, Callable, Dict, Iterable, Tuple


def fingerprint(directories: Iterable[str], suffixes: Tuple[str, ...]) -> Tuple:
    """A cheap signature of the content tree: every matching file's path and
    modification time. Any add, delete or edit changes it."""
    stamps = []
    for directory in directories:
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if name.endswith(suffixes):
                path = os.path.join(directory, name)
                try:
                    stamps.append((path, os.path.getmtime(path)))
                except OSError:
                    # File vanished mid-scan (an editor's atomic save). The
                    # next check will pick up whatever replaced it.
                    continue
    return tuple(stamps)


class ContentStore:
    """Holds loaded content and reloads it when the files behind it change."""

    def __init__(self, sources: Dict[str, Tuple[str, Tuple[str, ...], Callable[[str], Any]]]):
        """`sources` maps a name to (directory, suffixes, loader)."""
        self._sources = sources
        self._fingerprint = None
        self.data: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        for name, (directory, _suffixes, loader) in self._sources.items():
            self.data[name] = loader(directory)
        self._fingerprint = self._current_fingerprint()

    def _current_fingerprint(self) -> Tuple:
        return tuple(
            fingerprint([directory], suffixes)
            for directory, suffixes, _loader in self._sources.values()
        )

    def refresh(self) -> bool:
        """Reload if anything on disk changed. Returns True if it did."""
        current = self._current_fingerprint()
        if current != self._fingerprint:
            self.reload()
            return True
        return False


def demo() -> None:
    """Self-check: an edited file must be picked up, an untouched one must not."""
    import tempfile
    import time

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "a.scene")
        with open(path, "w", encoding="utf-8") as f:
            f.write("one")

        def load(directory):
            return {
                n: open(os.path.join(directory, n), encoding="utf-8").read()
                for n in os.listdir(directory)
            }

        store = ContentStore({"files": (tmp, (".scene",), load)})
        assert store.data["files"]["a.scene"] == "one"

        # Untouched tree: no reload.
        assert store.refresh() is False

        # Edited file: reload, and the new content is visible.
        time.sleep(0.01)          # ensure a distinct mtime
        with open(path, "w", encoding="utf-8") as f:
            f.write("two")
        os.utime(path, (time.time() + 1, time.time() + 1))
        assert store.refresh() is True
        assert store.data["files"]["a.scene"] == "two"

        # A new file is picked up too.
        with open(os.path.join(tmp, "b.scene"), "w", encoding="utf-8") as f:
            f.write("three")
        assert store.refresh() is True
        assert set(store.data["files"]) == {"a.scene", "b.scene"}

        # Files of another suffix are ignored.
        with open(os.path.join(tmp, "notes.txt"), "w", encoding="utf-8") as f:
            f.write("ignored")
        assert store.refresh() is False

    print("content hot-reload: all checks passed")


if __name__ == "__main__":
    demo()
