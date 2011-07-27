#!/usr/bin/env python
import sys

from os.path import dirname, abspath
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "fixture_generator",
            "fixture_generator.tests",
        ]
    )

from django.test.simple import DjangoTestSuiteRunner


def runtests(*test_args):
    if not test_args:
        test_args = ["tests"]
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    runner = DjangoTestSuiteRunner(verbosity=2, interactive=True, failfast=False)
    failures = runner.run_tests(test_args)
    sys.exit(failures)


def generate_fixture(sink, fixture, options):
    import tempfile
    from django.core.management import call_command
    import os
    import shutil

    tmpdir = tempfile.mkdtemp()
    try:
        options["dest_dir"] = tmpdir
        call_command("generate_fixture", fixture, **options)
        outs = []
        for fname in os.listdir(tmpdir):
            with open(os.path.join(tmpdir, fname), "rb") as f:
                outs.append((fname, f.read()))
        sink.send(outs)
    finally:
        shutil.rmtree(tmpdir)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

