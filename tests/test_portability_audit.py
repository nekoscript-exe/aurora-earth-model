"""Portable installation/path regressions; arbitrary bytes are not observations."""
import pytest
from aurora.distribution import safe_path


@pytest.mark.parametrize('directory_link', [False, True])
def test_package_rejects_internal_symlink_even_with_identical_bytes(tmp_path, directory_link):
    actual = tmp_path / 'actual'
    actual.mkdir()
    (actual / 'payload').write_text('EXPLICIT UNIT TEST BYTES')
    if directory_link:
        (tmp_path / 'alias').symlink_to(actual, target_is_directory=True)
        name = 'alias/payload'
    else:
        (tmp_path / 'alias').symlink_to(actual / 'payload')
        name = 'alias'
    with pytest.raises(ValueError, match='symbolic links'):
        safe_path(tmp_path, name)



def test_missing_install_lock_does_not_create_environment(tmp_path, monkeypatch):
    from scripts import install
    monkeypatch.setattr(install.sys, 'version_info', (3, 14, 4))
    monkeypatch.setattr(install.platform, 'system', lambda: 'Linux')
    prefix = tmp_path / 'independent'
    with pytest.raises(FileNotFoundError, match='lock unavailable'):
        install.install(tmp_path, prefix)
    assert not prefix.exists()



def test_distribution_does_not_discover_unrequested_sibling_project(tmp_path):
    from aurora.distribution import build_demo
    root = tmp_path / 'checkout'
    root.mkdir()
    # A sibling must never silently become an implicit data source.
    sibling = tmp_path / 'aurora-earth-model/data/processed/queretaro'
    sibling.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match='Missing payload: data/processed/queretaro;'):
        build_demo(root, tmp_path / 'new-distribution')
