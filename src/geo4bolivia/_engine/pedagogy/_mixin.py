"""The ``Interpretable`` mixin shared by the result dataclasses.

It declares a small, uniform surface: ``interpret`` (a plain-language reading of these
results) and ``tidy`` / ``glance`` (per-term and one-row summary frames). Result classes
override the methods that make sense for them; the defaults raise ``NotImplementedError``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

__all__ = ["Interpretable"]

# The engine names the unit and time columns of its tables generically; the package's
# own names are used in the results that the public functions return.
_TO_PUBLIC = {"entity": "geo_id", "period": "year"}
_TO_ENGINE = {v: k for k, v in _TO_PUBLIC.items()}


class Interpretable:
    """Mixin adding ``interpret`` / ``tidy`` / ``glance`` to result objects."""

    def interpret(self, *, lang: str = "en") -> str:
        """A plain-language reading of these results (Markdown)."""
        raise NotImplementedError(f"interpret() is not available for {type(self).__name__}")

    def tidy(self) -> pd.DataFrame:
        """A tidy data frame, one row per term or unit."""
        raise NotImplementedError(f"tidy() is not available for {type(self).__name__}")

    def glance(self) -> pd.DataFrame:
        """A one-row summary data frame."""
        raise NotImplementedError(f"glance() is not available for {type(self).__name__}")

    @property
    def variable(self):
        """The variable analysed (the engine calls it ``var``)."""
        return self.var

    @property
    def year(self):
        """The year analysed (the engine calls it ``period``)."""
        return self.period

    def _frames(self) -> dict:
        """The DataFrame-valued fields of this result."""
        import pandas as pd
        return {name: value for name in getattr(self, "__dataclass_fields__", {})
                if isinstance(value := getattr(self, name), pd.DataFrame)}

    def _renamed(self, mapping: dict[str, str]):
        """A copy whose tables have their columns (and index names) renamed."""
        import dataclasses
        changes = {}
        for name, frame in self._frames().items():
            if any(c in mapping for c in frame.columns) or any(n in mapping for n in frame.index.names):
                changes[name] = frame.rename(columns=mapping).rename_axis(
                    index=[mapping.get(n, n) for n in frame.index.names] if frame.index.nlevels > 1
                    else mapping.get(frame.index.name, frame.index.name))
        return dataclasses.replace(self, **changes) if changes else self

    def _public_view(self):
        """This result with the package's column names (``geo_id``, ``year``) in its tables."""
        return self._renamed(_TO_PUBLIC)

    def _engine_view(self):
        """This result with the engine's column names, which the interpretation texts read."""
        return self._renamed(_TO_ENGINE)

    def __repr__(self) -> str:
        import pandas as pd
        parts = []
        for name in getattr(self, "__dataclass_fields__", {}):
            value = getattr(self, name)
            if isinstance(value, bool | int | str) or value is None:
                parts.append(f"{name}={value!r}")
            elif isinstance(value, float):
                parts.append(f"{name}={value:.4g}")
            elif isinstance(value, pd.DataFrame):
                parts.append(f"{name}=<table {value.shape[0]}x{value.shape[1]}>")
            else:
                parts.append(f"{name}=<{type(value).__name__}>")
        return f"{type(self).__name__}({', '.join(parts)})"

    def _ipython_display_(self) -> None:
        """In a notebook, a result shows its main figure (or table) and its reading."""
        from IPython.display import Markdown, display
        main = getattr(self, "fig", None)
        if main is None:
            main = getattr(self, "gt", None)
        if main is None:
            main = getattr(self, "df", None)
        if main is not None:
            display(main)
        try:
            display(Markdown(self.interpret()))
        except NotImplementedError:
            pass
