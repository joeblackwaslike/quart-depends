# quart-depends

[![PyPI - Version](https://img.shields.io/pypi/v/quart-depends.svg)](https://pypi.org/project/quart-depends)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/quart-depends.svg)](https://pypi.org/project/quart-depends)

-----

**Table of Contents**

- [quart-depends](#quart-depends)
  - [Installation](#installation)
  - [Usage](#usage)
    - [Manual wiring](#manual-wiring)
    - [Autowiring](#autowiring)
    - [Nested dependencies](#nested-dependencies)
    - [Async support](#async-support)
    - [Generator style dependencies](#generator-style-dependencies)
      - [SQLAlchemy example](#sqlalchemy-example)
      - [Httpx AsyncClient example](#httpx-asyncclient-example)
    - [Annotated form](#annotated-form)
    - [Defining reusable dependencies](#defining-reusable-dependencies)
    - [Overriding dependencies](#overriding-dependencies)
    - [Binders](#binders)
      - [Learn more](#learn-more)
    - [Related documentation](#related-documentation)
  - [License](#license)

## Installation

```console
pip install quart-depends
```

## Usage
### Manual wiring
This default mode of operation requires the developer to opt in wherever they want dependency
injection by applying the `inject`` decorator.
```python
from quart import Quart

from quart_depends import QuartDepends, Depends, inject

app = Quart(__name__)
depends = QuartDepends(app)

def get_db():
    with Session() as session:
        yield session

@app.route("/", methods=["POST"])
@inject
def index(session: Session = Depends(get_db)):
    statement = select(User).where(User.id == 1)
    obj = session.execute(statement).one()
    return dict(status="ok", data=obj.to_dict())

app.run(port=8080)
```

### Autowiring
If you prefer to have the inject decorator applied automatically to all views, hooks, and callbacks
you can enable auto wiring via the Quart config mechanism.  You'll want to set the key
`QUART_DEPENDS_AUTO_WIRE` to `True` as shown below.  When doing this, you'll want to delay app
initialization by not passing it to the QuartDepends constructor.  After all the views and
callbacks have been defined and registered, call init_app(app) on the extension object.

```python
from quart import Quart

from quart_depends import QuartDepends, Depends, inject

app = Quart(__name__)
app.config['QUART_DEPENDS_AUTO_WIRE'] = True
depends = QuartDepends()

def get_db():
    with Session() as session:
        yield session

@app.route("/", methods=["POST"])
def index(session: Session = Depends(get_db)):
    statement = select(User).where(User.id == 1)
    obj = session.execute(statement).one()
    return dict(status="ok", data=obj.to_dict())


depends.init_app(app)
app.run(port=8080)
```

### Nested dependencies
Dependencies can be nested as deeply as you like, lookup will be resolved automatically and and wherever dependencies appear more than once in the graph, they will be resolved only once and the value shared among all dependents.

### Async support
If you're using an async first framework such as quart, you probably want to leverage async dependencies as well as sync dependencies.  Luckily this extension will analyze each callable to see whether its async or blocking, and automatically wrap blocking calls that occur alongside async ones.  No need to apply `run_wait`!

```python
from quart import Quart

from quart_depends import QuartDepends, Depends, inject

app = Quart(__name__)
app.config['QUART_DEPENDS_AUTO_WIRE'] = True
depends = QuartDepends()

def get_db():
    async with AsyncSession() as session:
        yield session

@app.route("/", methods=["POST"])
async def index(session: AsyncSession = Depends(get_db)):
    statement = select(User).where(User.id == 1)
    obj = (await session.execute(statement)).one()
    return dict(status="ok", data=obj.to_dict())


depends.init_app(app)
app.run(port=8080)
```

**Remember this important caveat:**  With async code we can use sync and async dependencies both, but with sync runtime only sync dependencies are available.

### Generator style dependencies
A common pattern when dealing with external IO such as databases, caches, connection pools, etc is for a set of calls to be wrapped in a context manager that handles the lifecycle of the underlying connection pool.  Some examples of this are SQLAlchemy's Connection, Session, and Transactions, Httx's async connection pooling, and even for instance, a redis pipeline execution.

#### SQLAlchemy example
```python
import sqlalchemy as sa

engine = sa.create_engine("sqlite://")
metadata = sa.MetaData(bind=engine)
Session = sa.orm.sessionmaker()

user = sa.Table('user', metadata, ...)

with engine.connect() as connection:
    with Session(bind=connection) as session:
        with session.begin():
            session.add(sa.insert(user).values(name="Joe"))
        # when this context closes, the session will have flush() and commit() called on it automatically
    # when this context closes, the Session will have close() called on it automaticaly
# When this context closes, the connection will have close() called on it automatically.
```

#### Httpx AsyncClient example
```python
import httpx

async with httpx.AsyncClient() as client:
    r = await client.post('https://github.com', json=dict(job=1, now=True))
# connection pool will be closed automatically
```

This is the most natural style to manage such dependencies using QuartDepends.  Just like we do with pytest fixtures, we'll open any necessary context managers, and within that nesting yield the dependency.  This will be the value injected by this Depends value at runtime.  However the framework will automatically take care of opening the context before and closing the context afterwards.  This works equally for both sync and async workflows.

```python
def get_db():
    async with AsyncSession() as session:
        yield session

@app.route("/", methods=["POST"])
async def index(session: AsyncSession = Depends(get_db)):
    statement = select(User).where(User.id == 1)
    obj = (await session.execute(statement)).one()
    return dict(status="ok", data=obj.to_dict())
```

### Annotated form
Leveraging the power of typing.Annotated, many advanced patterns can be developed and cleanly packaged preserving type safety in most IDEs while remaining succinct and readable.  A popular pattern is to Wrap the Depends object along with the expected type using Annotated and assigning that a friendly, reusable name.
```python
from fast_depends import Depends, inject
from pydantic import BaseModel, PositiveInt

class User(BaseModel):
    user_id: PositiveInt

def get_user(user: id) -> User:
    return User(user_id=user)

@inject
def do_smth_with_user(user: User = Depends(get_user)):
    ...
```
becomes
```python
from typing import Annotated
from fast_depends import Depends, inject
from pydantic import BaseModel, PositiveInt

class User(BaseModel):
    user_id: PositiveInt

def get_user(user: id) -> User:
    return User(user_id=user)

CurrentUser = Annotated[User, Depends(get_user)]

@inject
def do_smth_with_user(user: CurrentUser):
```

The caveat to using this is ensuring the correct ordering of argument types in callables.  Since `do_smth_with_user(user: CurrentUser)` no longer has a default value, it must appear before keyword only arguments in the signature of the callable.  You can address this by either assigning a default value of None or using Annotated with all arguments (where possible).  Nearly any argument can be converted to Annotated style using `pydantic.Field` and the following form:
```python
def func(number):
    ...
```
becomes
```python
def func(number: Annotated[int, Field(...)]):
    ...
```
And you get pydantic style validation of any arguments for free.  Note this even be combined with the Annotated + Depends style for ultimate control!


### Defining reusable dependencies
Whether the @inject decorator is applied explicitely or automatically, its important to understand the scope for caching resolved dependencies.  The lifetime is scoped to a single call of the @inject decoratoed function/method.  This can often involve many deeply nested branches whenever a decorated view function is called and regardless of how deep, two dependencies of the same Depends will receive the same value shared amongst them.

### Overriding dependencies
For testing purposes, its common to want to override a dependency to replace something with a mock, spy, etc.  It's recommended to turn QuartDepends.provider into a pytest fixture and use the methods override and clear for dependency overrides.  To override a dependency you want to provide an alternative callable to be swapped in for the original.

```python
from quart import Quart
import pytest

from quart_depends import QuartDepends, Depends, inject

app = Quart(__name__)
app.config['QUART_DEPENDS_AUTO_WIRE'] = True
depends = QuartDepends()

async def get_db():
    async with AsyncSession() as session:
        yield session

@app.route("/", methods=["POST"])
async def index(session: AsyncSession = Depends(get_db)):
    statement = select(User).where(User.id == 1)
    obj = (await session.execute(statement)).one()
    return dict(status="ok", data=obj.to_dict())

depends.init_app(app)


@pytest.fixture
def dependency_provider():
    return depends.provider


async def test_the_db(dependency_provider)
    async def new_db():
        yield MagicMock()

    dependency_provider.override(get_db, new_db)

    test_client = app.test_client()

    resp = await test_client.post("/")

    dependency_provider.clear()
    
    ...
```

### Binders
Binders are classes allowing important bits of a request to be extracted and type coerced, sometimes even into pydantic models using a very succinct syntax that doesn't require defining functions that parse the request object.

```python
class CommonQuery(BaseModel):
    q: t.Optional[str] = None
    skip: int = 0
    limit: int = 100
 

@app.route(uri, methods=["GET"])
async def view(
    paging: FromQueryData[CommonQuery] = None,
    sort: FromQueryField[t.Literal["asc", "desc"]] = None,
):
    return dict(paging=paging.dict(), sort=sort)
```

```python
class ReqPayload(BaseModel):
    name: str = ""
    age: int = 0


@app.route("/use/<string:label>", methods=["POST"])
async def view(
    accept: FromHeader[str] = None,
    q: FromQueryField[str] = None,
    label: FromPath[str] = None,
    payload: FromJson[ReqPayload] = None,
    cookie: FromCookie[str] = None,
):
    assert isinstance(request, QuartRequest)
    assert payload.dict() == jsondict

    return dict(
        body=body,
        accept=accept,
        q=str(q),
        label=label,
        payload=payload.dict(),
        common=common.dict(),
        cookie=cookie,
    )
```

#### Learn more
* [Checkout more examples in the test suite.](tests/integration/test_custom_fields.py)
* [FastDepends docs for CustomField](https://lancetnik.github.io/FastDepends/advanced/)


### Related documentation
* [FastDepends Docs](https://lancetnik.github.io/FastDepends/)
* [FastAPI Dependencies Docs](https://fastapi.tiangolo.com/tutorial/dependencies/)
* [FastAPI Advanced Dependencies Docs](https://fastapi.tiangolo.com/advanced/advanced-dependencies/)

## License
`quart-depends` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
