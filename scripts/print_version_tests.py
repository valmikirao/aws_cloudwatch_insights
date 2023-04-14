import os.path
import subprocess
from aws_cloudwatch_insights import __version__


def test_print_version():
    """ Kind of silly, but this did break at one point"""
    this_dir = os.path.dirname(__file__)
    print_version_script = os.path.join(this_dir, 'print_version.py')
    actual = subprocess.check_output(['python', print_version_script])\
        .decode().strip()
    assert actual == __version__
