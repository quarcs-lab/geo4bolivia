"""Dark figures and tables for the documentation site only.

The docs kernel (registered by tools/build_docs.py with IPYTHONDIR pointing here) runs this file
at start-up, so every page renders its Plotly figures and Great Tables in the site's dark Altiplano
palette. Nothing here is part of the package: users keep Plotly's and Great Tables' defaults.
"""


def _g4_dark_setup():
    # Inside a function, so the notebook's namespace (cleared by the renderer) holds none of these names
    import plotly.graph_objects as go
    import plotly.io as pio
    from plotly.basedatatypes import BaseFigure

    _BG = "#0b1e22"          # lagoon-900
    _GRID = "#1b3c42"        # lagoon-700
    _LINE = "#29545b"        # lagoon-600
    _TEXT = "#e3ecea"        # salt-200
    _MUTED = "#a9bebb"       # salt-400
    _FONT = "Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"

    _template = go.layout.Template(pio.templates["plotly_dark"])
    _axis = {"gridcolor": _GRID, "linecolor": _LINE, "zerolinecolor": _LINE, "tickcolor": _LINE}
    _template.layout.update(
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        font={"family": _FONT, "color": _TEXT},
        title={"font": {"color": _TEXT}},
        legend={"bgcolor": "rgba(0,0,0,0)", "font": {"color": _TEXT}},
        xaxis=_axis, yaxis=_axis,
        geo={"bgcolor": _BG, "landcolor": _BG, "lakecolor": _BG, "subunitcolor": _LINE, "countrycolor": _LINE},
        map={"style": "carto-darkmatter"},
        hoverlabel={"bgcolor": "#122b30", "font": {"color": _TEXT, "family": _FONT}},
    )
    pio.templates["g4_dark"] = _template
    pio.templates.default = "g4_dark"

    _LIGHT_TILES = {"carto-positron", "open-street-map", "white-bg", "carto-voyager", "light", "basic", "streets", "outdoors"}


    def _light(colour) -> bool:
        """Whether a CSS colour (hex, rgb/rgba or a few names) is light."""
        if colour is None:
            return False
        c = str(colour).strip().lower()
        if c in {"white", "whitesmoke", "snow", "ivory"}:
            return True
        if c.startswith("#") and len(c) in (4, 7):
            c = c[1:]
            if len(c) == 3:
                c = "".join(ch * 2 for ch in c)
            r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
        elif c.startswith("rgb"):
            r, g, b = (float(v) for v in c[c.index("(") + 1:c.index(")")].split(",")[:3])
        else:
            return False
        return 0.299 * r + 0.587 * g + 0.114 * b > 160


    def _dark(colour) -> bool:
        return colour is not None and not _light(colour) and str(colour).strip().lower() not in {"", "none"}


    def _darken(fig) -> None:
        """The site's dark template over the package's light one, dark tiles, boxes and colour bars."""
        layout = fig.layout
        base = "plotly_dark+geo_dark+g4_dark" if "geo_dark" in pio.templates else "g4_dark"
        layout.template = base
        for name in ("paper_bgcolor", "plot_bgcolor"):
            if _light(layout[name]):
                layout[name] = _BG
        if _dark(layout.font.color):
            layout.font.color = _TEXT
        for note in layout.annotations or ():
            if _light(note.bgcolor):
                note.bgcolor = "rgba(11,30,34,0.85)"
                if _light(note.bordercolor):
                    note.bordercolor = _LINE
            if _dark(note.font.color) and "rgba(0,0,0,0" not in str(note.font.color):
                note.font.color = _TEXT
        if layout.legend is not None and _light(layout.legend.bgcolor):
            layout.legend.bgcolor = "rgba(11,30,34,0.6)"
        for key in ("map", "mapbox"):
            for name in [n for n in layout if n == key or n.startswith(key) and n[len(key):].isdigit()]:
                sub = layout[name]
                if sub is not None and (sub.style is None or str(sub.style) in _LIGHT_TILES):
                    sub.style = "carto-darkmatter"
        for trace in fig.data:
            bar = getattr(trace, "colorbar", None)
            if bar is not None:
                bar.update(tickfont={"color": _MUTED}, title={"font": {"color": _TEXT}}, outlinewidth=0)


    _repr = BaseFigure._repr_mimebundle_


    def _dark_repr(self, *args, **kwargs):
        _darken(self)
        return _repr(self, *args, **kwargs)


    BaseFigure._repr_mimebundle_ = _dark_repr

    _show = BaseFigure.show


    def _dark_show(self, *args, **kwargs):
        _darken(self)
        return _show(self, *args, **kwargs)


    BaseFigure.show = _dark_show

    _display = BaseFigure._ipython_display_

    def _dark_display(self):
        _darken(self)
        return _display(self)

    BaseFigure._ipython_display_ = _dark_display

    try:
        from great_tables import GT

        _gt_repr = GT._repr_html_

        import inspect

        _GT_OPTIONS = set(inspect.signature(GT.tab_options).parameters)

        def _dark_gt(self):
            options = dict(
                table_background_color=_BG, table_font_color=_TEXT, table_font_color_light=_TEXT,
                table_border_top_color=_LINE, table_border_bottom_color=_LINE,
                heading_background_color=_BG, heading_border_bottom_color=_LINE,
                column_labels_background_color="#122b30", column_labels_border_top_color=_LINE,
                column_labels_border_bottom_color="#5ad6c6",
                row_group_background_color="#122b30", row_group_border_top_color=_LINE,
                row_group_border_bottom_color=_LINE, table_body_hlines_color=_GRID,
                table_body_border_top_color=_LINE, table_body_border_bottom_color=_LINE,
                stub_background_color=_BG, stub_border_color=_LINE,
                summary_row_background_color="#122b30", grand_summary_row_background_color="#122b30",
                footnotes_background_color=_BG, source_notes_background_color=_BG,
                footnotes_border_bottom_color=_LINE, source_notes_border_bottom_color=_LINE,
            )
            dark = self.tab_options(**{k: v for k, v in options.items() if k in _GT_OPTIONS})
            return _gt_repr(dark)

        GT._repr_html_ = _dark_gt
    except Exception:  # pragma: no cover - great_tables missing or its options renamed
        pass


_g4_dark_setup()
del _g4_dark_setup
