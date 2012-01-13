import os
from optparse import make_option

from django.core.management import call_command, BaseCommand
from django.conf import settings
from fixture_generator.base import get_available_fixtures
from django.db.models.loading import get_app

class Command(BaseCommand):
    """
    Regenerate fixtures for all applications.
    """

    option_list = BaseCommand.option_list + (
        make_option("--format", default="json", dest="format",
            help="Specifies the output serialization format for fixtures."),
        make_option("--indent", default=4, dest="indent", type="int",
            help="Specifies the indent level to use when pretty-printing output"),
        make_option("--not-natural", default=True, dest="use_natural_keys", action="store_false",
            help="Don't use natural keys."),
        make_option("--databases", dest="dbs", default="",
            help="Comma separeted list of databases to dump. All databases are used by default")
    )

    args = '<app app ... app>'

    def handle(self, *apps, **options):
        fixtures = get_available_fixtures(apps or settings.INSTALLED_APPS)
        for fixture in fixtures.itervalues():
            if not isinstance(fixture.export, basestring):
                continue
            print fixture
            app = get_app(fixture.app)
            destdir = os.path.dirname(app.__file__)
            if app.__file__.rsplit('.', 1)[0].endswith("__init__"):
                destdir = os.path.dirname(destdir)
            destdir = os.path.join(destdir, "fixtures")
            call_command("generate_fixture", fixture.label, prefix=fixture.export, dest_dir=destdir, **options)
