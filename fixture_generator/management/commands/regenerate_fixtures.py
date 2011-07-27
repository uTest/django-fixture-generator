import os
import sys
from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.core.management import call_command
from django.conf import settings
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule
from fixture_generator.base import get_availble_fixtures

class Command(NoArgsCommand):
    """
    Regenerate fixtures for all applications.
    """

    def handle_noargs(self):
        available_fixtures = get_availble_fixtures()

