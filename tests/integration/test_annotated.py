from typing import Annotated

from pydantic import BaseModel, PositiveInt

from quart_depends import Depends, inject


class User(BaseModel):
    user_id: PositiveInt


def get_user(user: int) -> User:
    return User(user_id=user)


CurrentUser = Annotated[User, Depends(get_user)]


class TestAnnotations:
    def test_duplicated_syntax(self):
        @inject
        def do_smth_with_user(user: User = Depends(get_user)):
            return user

        @inject
        def do_another_smth_with_user(user: User = Depends(get_user)):
            return user

        user_id = 1

        first, second = do_smth_with_user(user=user_id), do_another_smth_with_user(user=user_id)

        assert isinstance(first, User)
        assert first == second
        assert first.user_id == user_id
        assert second.user_id == user_id

    def test_annotated_syntax(self):
        @inject
        def do_smth_with_user(user: CurrentUser):
            return user

        @inject
        def do_another_smth_with_user(user: CurrentUser):
            return user

        user_id = 1

        first, second = do_smth_with_user(user=user_id), do_another_smth_with_user(user=user_id)

        assert first == second
        assert first == second
        assert first.user_id == user_id
        assert second.user_id == user_id
