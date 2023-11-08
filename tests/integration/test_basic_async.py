import asyncio

from quart_depends import Depends, inject


def test_basic_scenario():
    def dependency(a: int) -> int:
        return a

    async def async_dependency(b: int) -> int:
        return b

    @inject
    async def view(
        a: int,
        b: int,
        d: int = Depends(dependency),
        c: int = Depends(async_dependency),
    ) -> float:
        return a + b + c + d

    assert asyncio.run(view("1", 2)) == 6


class TestCallableTypes:
    class MyDependency:
        def __init__(self, a: int):
            self.field = a

        def __call__(self, b: int) -> int:
            return self.field + b

        def method_dep(self, a: int):
            return a**2

    def test_class_dependency(self):
        @inject
        def class_dependency(d=Depends(self.MyDependency)):
            return d

        result = class_dependency(a=3, b=3)
        assert result(b=3) == 6

    def test_instance_dependency(self):
        @inject
        def instance_dependency(d: int = Depends(self.MyDependency(3))):
            return d

        assert instance_dependency(b=3) == 6

    def test_method_dependency(self):
        @inject
        def method_dependency(d: int = Depends(self.MyDependency(3).method_dep)):
            return d

        assert method_dependency(a=3) == 3**2


class TestAdvancedCallableTypes:
    class MyOtherDependency:
        @classmethod
        def class_dep(cls, a: int):
            return a**2

        @staticmethod
        def static_dep(a: int):
            return a**2

    def test_class_method_dependency(self):
        @inject
        def class_method_dependency(d: int = Depends(self.MyOtherDependency.class_dep)):
            return d

        assert class_method_dependency(a=3) == 3**2

    def test_static_method_dependency(self):
        @inject
        def static_method_dependency(e: int = Depends(self.MyOtherDependency.static_dep)):
            return e

        assert static_method_dependency(a=3) == 3**2
