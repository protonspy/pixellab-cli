"""Isolation every test in this suite depends on and none of it should have to ask for.

`load_credentials` falls back to `Path.home()`, so on a machine whose home directory
holds a real `.pixellab.json` the suite reads the developer's own key and every test
asserting that a credential is absent fails. It passes in CI, where no such file
exists, which is the worst version of this: green everywhere it is watched.

Both credential variables go with it, for the same reason.
"""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def an_isolated_home(tmp_path, monkeypatch):
    """Point the home directory at this test's own empty one, for the whole suite.

    `tmp_path` rather than a directory of its own, because it has to be an *ancestor*
    of whatever a test passes as a workspace or a start directory. The upward search
    for a credentials file stops at the home directory; a home that sits off to one
    side never appears on the way up, the search carries on past it, and the first
    `.pixellab.json` it meets is the real one.
    """
    home = tmp_path
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    for variable in ("HOME", "USERPROFILE", "PIXELLAB_SECRET", "FAL_KEY"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("USERPROFILE", str(home))

    # The second stop, for the tests that name a home of their own somewhere off the
    # path — there the home stop cannot fire, and without a project marker the search
    # climbs out of the fixtures entirely. `.hg` because no test writes one.
    (tmp_path / ".hg").mkdir(exist_ok=True)
    return home
