import os
import re

from aws_cloudwatch_insights import __version__


def test_version():
    """
    Make sure version in version.txt (used by setup.py) is the same as that in curl_arguments_url/__init__.py
    and also that latest version is in the CHANGELOG.md
    """
    content_root = os.path.dirname(__file__)
    version_file = os.path.join(content_root, 'version.txt')
    with open(version_file, 'r') as f:
        version_from_file = f.read()
        version_from_file = version_from_file.strip()

    assert version_from_file == __version__, 'Versions in version.txt and curl_arguments_url/__init__.py should be' \
                                             ' the same'

    changelog_file = os.path.join(content_root, 'CHANGELOG.md')
    with open(changelog_file, 'r') as f:
        changelog_str = f.read()
    assert re.search(r'^' + re.escape(f"**{__version__}**"), changelog_str, flags=re.MULTILINE), \
        f"Version {__version__} not referenced in CHANGELOG.md"
