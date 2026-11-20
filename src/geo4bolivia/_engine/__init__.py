"""The analysis engine: estimators, figures, tables and interpretation texts.

Ported from the sister package geometrics (MIT, same author), without its sandboxes,
explainers and apps. The functions here keep geometrics' vocabulary (``var``, ``period``,
``entity``, ``time``, ``start``/``end``) and take every input explicitly (``df``, ``gdf``,
``w``); the package's public functions wrap them with this package's own vocabulary and
find boundaries, weights and labels from the metadata.

Names resolve lazily (PEP 562), so importing the package does not import the
estimation libraries.
"""

from __future__ import annotations

import importlib

_EXPORTS = {
    "maps": ("explore_choropleth_map",),
    "weights": ("explore_connectivity_map", "make_weights"),
    "dependence": ("explore_moran_plot", "explore_lisa_cluster_map", "explore_moran_over_time"),
    "spacetime": ("explore_distribution_over_time", "explore_spacetime_heatmap"),
    "convergence": ("analyze_beta_convergence", "analyze_sigma_convergence", "growth_cross_section"),
    "clubs": ("analyze_convergence_clubs",),
    "spatial_models": ("analyze_spatial_model", "analyze_spatial_diagnostics", "analyze_spatial_model_by_weights"),
    "distribution_dynamics": ("analyze_markov_transitions", "analyze_spatial_markov"),
    "regional_inequality": ("analyze_inequality_over_time", "analyze_theil_decomposition"),
    "gwr": ("analyze_gwr", "analyze_mgwr"),
    "_geo": ("read_gdf",),
    "_panel": ("set_panel", "resolve_panel"),
    "_labels": ("set_labels", "resolve_label"),
    "_roles": ("set_roles",),
    "_data_dict": ("build_data_dict",),
    "_theme": ("set_palette", "get_palette"),
}
_WHERE = {name: module for module, names in _EXPORTS.items() for name in names}

__all__ = sorted(_WHERE)


def __getattr__(name: str):
    module = _WHERE.get(name)
    if module is None:
        if name.endswith("Result"):
            return getattr(importlib.import_module("._types", __name__), name)
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(f".{module}", __name__), name)
    globals()[name] = value
    return value
