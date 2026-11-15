"""Static contracts for scalar scientific results."""

from typing import Protocol


class LinearRegressionResult(Protocol):
    @property
    def slope(self) -> float: ...

    @property
    def intercept(self) -> float: ...

    @property
    def rvalue(self) -> float: ...

    @property
    def pvalue(self) -> float: ...

    @property
    def stderr(self) -> float: ...

    @property
    def intercept_stderr(self) -> float: ...
