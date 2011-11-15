import os
import sys
from optparse import make_option

from django.core.management import BaseCommand, call_command
from django.conf import settings

from fixture_generator.signals import data_dumped
from django.test.simple import DjangoTestSuiteRunner
from django.test.utils import get_runner
from django.utils import importlib

import contextlib
from fixture_generator.base import get_available_fixtures, calculate_requirements

@contextlib.contextmanager
def altered_stdout(f):
    _stdout, sys.stdout = sys.stdout, f
    yield
    sys.stdout = _stdout


@contextlib.contextmanager
def testing_environment():
    from django.core import management
    from django.core import mail
    from django.core.mail.backends import locmem
    from django.utils.translation import deactivate, activate, get_language

    original_smtp = mail.SMTPConnection,
    mail.SMTPConnection = locmem.EmailBackend

    original_email_backend = settings.EMAIL_BACKEND
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    mail.outbox = []

    current_language = get_language()
    deactivate()
    debug, settings.DEBUG = settings.DEBUG, False
    settings.DEBUG = debug
    settings.CELERY_ALWAYS_EAGER = True

    # make sure south doesn't break stuff
    management._commands['syncdb'] = 'django.core'

    yield

    activate(current_language)
    settings.EMAIL_BACKEND = original_email_backend
    mail.SMTPConnection = original_smtp


class GeneratingSuiteRunner(DjangoTestSuiteRunner):

    def __init__(self, requirements, models, options):
        super(GeneratingSuiteRunner, self).__init__(verbosity=1)
        self.requirements = requirements
        self.models = models
        self.options = options

    def run_tests(self, *args, **kwargs):
        with testing_environment():
            # make sure global URLs are loaded here
            importlib.import_module(settings.ROOT_URLCONF)
            old_config = self.setup_databases()
            try:
                self.generate_fixtures()
            finally:
                self.teardown_databases(old_config)
        return 0

    def generate_fixtures(self):
        dbs = filter(None, self.options["dbs"].split(',')) or settings.DATABASES.keys()

        # execute the fixtures
        for fixture_func in self.requirements:
            fixture_func()

        self.dump_data(dbs)

    def make_filename(self, dbname, format=None):
        return os.path.join(self.options["dest_dir"], "%s.%s.%s" % (self.options["prefix"], dbname, format or self.options["format"]))

    def dump_data(self, dbs):
        for db in dbs:
            with open(self.make_filename(db), "w+") as f:
                with altered_stdout(f):
                    call_command("dumpdata",
                         *["%s.%s" % (m._meta.app_label, m._meta.object_name) for m in self.models],
                         **dict(self.options, verbosity=0, database=db))

        # post-dump hook
        data_dumped.send(self, models=self.models, databases=dbs)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--format", default="json", dest="format",
            help="Specifies the output serialization format for fixtures."),
        make_option("--indent", default=None, dest="indent", type="int",
            help="Specifies the indent level to use when pretty-printing output"),
        make_option("-n", "--natural", default=False, dest="use_natural_keys", action="store_true",
            help="Use natural keys if they are available."),
        make_option("-d", "--dir", dest="dest_dir", default=".",
            help="Where to put the fixtures"),
        make_option("-p", "--prefix", dest="prefix", default="fixture",
            help="Prefix for the filename to which the fixture will be written. "
            "The whole name is constructed as follows: %(prefix).%(db).%(format)."),
        make_option("--databases", dest="dbs", default="",
            help="Comma separeted list of databases to dump. All databases are used by default")
    )

    args = "app_label.fixture"
    requires_model_validation = True

    def handle(self, fixture, **options):
        fixtures = get_available_fixtures(settings.INSTALLED_APPS)
        fixture = fixtures[tuple(fixture.rsplit(".", 1))]
        requirements, models = calculate_requirements(fixtures, fixture)

        # fetch the projects test runner class
        runner_class = get_runner(settings)

        FixtureRunner = type("FixtureRunner", (GeneratingSuiteRunner, runner_class), {})
        runner = FixtureRunner(requirements, models, options)
        runner.run_tests()
