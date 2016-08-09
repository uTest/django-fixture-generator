from django.utils.module_loading import module_has_submodule
from collections import namedtuple
from importlib import import_module



class Fixture(namedtuple("Fixture", "app name export func")):
    __slots__ = ()

    def __hash__(self):
        return hash((self.app, self.name))

    def __eq__(self, other):
        return self[:2] == other[:2]

    @property
    def models(self):
        return self.func.models

    @property
    def requires(self):
        return self.func.requires

    @property
    def label(self):
        return "%s.%s" % (self.app, self.name)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

class CircularDependencyError(Exception):
    """
    Raised when there is a circular dependency in fixture requirements.
    """
    pass


def unique_seq(l):
    seen = set()
    for e in l:
        if e not in seen:
            seen.add(e)
            yield e


def calculate_requirements(available_fixtures, fixture, seen=None):
    if seen is None:
        seen = set([fixture])
    models = list(reversed(fixture.models))
    requirements = []
    for requirement in fixture.requires:
        app_label, fixture_name = requirement.rsplit(".", 1)
        fixture_func = available_fixtures[(app_label, fixture_name)]
        if fixture_func in seen:
            raise CircularDependencyError
        r, m = calculate_requirements(
            available_fixtures,
            fixture_func,
            seen | set([fixture_func])
        )
        requirements.extend([req for req in r if req not in requirements])
        models.extend(reversed(m))
    requirements.append(fixture)
    return requirements, list(unique_seq(reversed(models)))


def get_available_fixtures(apps):
    fixtures = {}
    for app in apps:
        try:
            fixture_gen = import_module(".fixture_gen", app)
        except ImportError:
            if module_has_submodule(import_module(app), "fixture_gen"):
                raise
            continue
        for obj in fixture_gen.__dict__.values():
            if not getattr(obj, "__fixture_gen__", None):
                continue
            fixture = Fixture(app.rsplit(".", 1)[-1], obj.__name__, obj.export, obj)
            fixtures[fixture] = fixture
    return fixtures

def fixture_generator(*models, **kwargs):
    """
    Define function as a fixture generator
    """
    requires = kwargs.pop("requires", [])
    export = kwargs.pop("export", False)
    if kwargs:
        raise TypeError("fixture_generator got an unexpected keyword argument: %r", iter(kwargs).next())
    def decorator(func):
        func.models = models
        func.requires = requires
        func.export = func.__name__ if export is True else export
        func.__fixture_gen__ = True
        return func
    return decorator
