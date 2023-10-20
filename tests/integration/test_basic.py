from fast_depends import Depends, inject


def dependency(a: int) -> int:
    return a


@inject
def view(a: int, b: int, c: int = Depends(dependency)) -> float:
    return a + b + c


class TestAppSync:
    def test_view(self):
        result = view("1", 2)
        assert result == 4.0
