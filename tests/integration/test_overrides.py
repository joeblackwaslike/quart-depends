import pytest
from fast_depends import dependency_provider

from quart_depends import Depends, inject


def original_dependency():
    return 1


def override_dependency():
    return 2


class TestOverrides:
    def test_override_dependency_provider(self):
        @inject
        def func(d=Depends(original_dependency)):
            return d

        result = func()

        assert result == 1

        dependency_provider.override(original_dependency, override_dependency)

        result = func()

        assert result == 2

        dependency_provider.clear()

    def test_override_dict_form(self):
        @inject
        def func(d=Depends(original_dependency)):
            return d

        result = func()

        assert result == 1

        dependency_provider.dependency_overrides[original_dependency] = override_dependency

        result = func()

        assert result == 2

        dependency_provider.clear()

    @pytest.fixture
    def provider(self):
        yield dependency_provider
        dependency_provider.clear()

    def test_override_fixture(self, provider):
        @inject
        def func(d=Depends(original_dependency)):
            return d

        result = func()

        assert result == 1

        provider.override(original_dependency, override_dependency)

        result = func()

        assert result == 2
