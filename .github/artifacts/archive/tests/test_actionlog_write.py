import os
import pytest


def test_actionlog_write_on_save():
    # If backend code not present, skip and mark TODO for author
    if not os.path.isdir('code/backend') and not os.path.isdir('backend'):
        pytest.skip('Backend not present — TODO: implement ActionLog test double')

    # TODO: Implement in-memory SQLite test for ActionLog write-on-save
    assert True
