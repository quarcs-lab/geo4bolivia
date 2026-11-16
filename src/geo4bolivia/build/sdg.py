"""SDG Atlas 2026: raw/sdg -> data/municipality/sdg (the IDS) and sdg01 ... sdg17 (one per goal).

The Atlas de los ODS en Bolivia 2026 (Andersen & Argandoña, SDSN Bolivia) measures 81
indicators of 15 goals (none for SDG 12 or 14) for the 343 municipalities and indigenous
autonomies (GAIOC) twice: an initial value near the 2012 census and a final value near the
2024 census. Each indicator is rescaled to 0-100 between a worst and a best value (Cuadro 21 of
the Atlas, transcribed in raw/lookups/sdg2026_thresholds.csv); a goal index is the mean of its
rescaled indicators and the Sustainable Development Index (IDS) the mean of the 15 goal indices.

The panels store both periods at the nominal years 2012 and 2024 (``year``), so that every
variable can be compared between them; each variable's actual reference years (e.g. 2008 and
2023 for the health survey, averages of 2013-15 and 2022-24 for agriculture) are in its
metadata (``geo:reference_years``). Rows are linked to geo IDs by INE code.
"""

from functools import partial

import numpy as np
import pandas as pd

from .. import metadata, store
from .common import ids_from_units, publish, write_docs

SCALE = "municipality"
RAW = "raw/sdg/atlas_ods_bolivia_2026.xlsx"
THRESHOLDS = "raw/lookups/sdg2026_thresholds.csv"
CENSUS = "raw/boundaries/sdsn2025/sdsn_municipal_boundaries_2025.dbf"
GOALS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17)   # the Atlas has no index for 12 or 14
YEARS = (2012, 2024)                                           # initial (~2012) and final (~2024) values
N_UNITS = 343
# INE codes whose 2024 population differs between the Atlas (8,679) and the SDSN map (8,279): Huarina
POPULATION_DIFFERS = ("020204",)
SHEET_VALUES, SHEET_INDICES = "Indicadores municipales", "Índices municipales"


def dataset(goal: int) -> str:
    return f"sdg{goal:02d}"


def varname(code: str) -> str:
    """Atlas indicator code -> variable name: '01_02_02_01_mpi' -> 'sdg1_2_mpi' (goal, target, code)."""
    goal, target, _, _, short = code.split("_", 4)
    return f"sdg{int(goal)}_{int(target)}_{short}"


def _codes(series: pd.Series) -> pd.Series:
    """INE codes as written in the workbook (10101) -> six-digit strings ('010101')."""
    return series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(6)


def _paired(frame: pd.DataFrame, header: pd.Series, first: int) -> dict:
    """{label: (initial column, final column)} for the column pairs starting at ``first``."""
    labels = header.iloc[first::2]
    return {label: (frame.columns[i], frame.columns[i + 1]) for i, label in zip(range(first, frame.shape[1], 2), labels)
            if isinstance(label, str) and label.strip()}


def _frame(codes: pd.Series, columns: dict) -> pd.DataFrame:
    out = pd.DataFrame({k: pd.to_numeric(v) for k, v in columns.items()})
    out.insert(0, "ine_code", _codes(codes))
    return out


def read() -> dict:
    """The Atlas's municipal values: {'values', 'normalised', 'indices', 'context'}, wide by INE code."""
    path = store.repo_root() / RAW
    vals = pd.read_excel(path, sheet_name=SHEET_VALUES, header=None, dtype=object)
    idx = pd.read_excel(path, sheet_name=SHEET_INDICES, header=None, dtype=object)

    # indicator values: codes in row 3, one (initial, final) pair per indicator from column 4
    body = vals.iloc[5:].reset_index(drop=True)
    pairs = _paired(body, vals.iloc[2], 3)
    values = _frame(body[1], {(varname(code), y): body[c] for code, cols in pairs.items() for y, c in zip(YEARS, cols)})

    # indices sheet: context, ranks and IDS, then the goal indices (row 3 holds the goal number),
    # then the code again (column 42) and each indicator's normalised value (0-100), labelled by code
    body = idx.iloc[5:].reset_index(drop=True)
    context = _frame(body[0], {"population_2024": body[2], "urbanization": body[3],
                               ("rank_sdg", YEARS[0]): body[4], ("rank_sdg", YEARS[1]): body[5],
                               ("index_sdg", YEARS[0]): body[6], ("index_sdg", YEARS[1]): body[7]})
    goals = {int(float(g)): c for g, c in _paired(body.iloc[:, :40], idx.iloc[2, :40].astype(str), 10).items()
             if g.replace(".0", "").isdigit()}
    if sorted(goals) != list(GOALS):
        raise ValueError(f"{SHEET_INDICES}: goal index columns {sorted(goals)} differ from {GOALS}")
    indices = _frame(body[0], {(f"index_sdg{g}", y): body[c] for g, cols in goals.items() for y, c in zip(YEARS, cols)})
    if not (_codes(body[41]) == _codes(body[0])).all():
        raise ValueError(f"{SHEET_INDICES}: the normalised values do not follow the codes in column 42")
    norm_pairs = _paired(body, idx.iloc[2], 43)
    if list(norm_pairs) != list(pairs):
        raise ValueError(f"{SHEET_INDICES}: the normalised values are not the indicators of {SHEET_VALUES}")
    normalised = _frame(body[0], {(varname(code), y): body[c] for code, cols in norm_pairs.items()
                                  for y, c in zip(YEARS, cols)})
    return {"values": values, "normalised": normalised, "indices": indices, "context": context,
            "codes": list(pairs)}


def _resolution(x: pd.Series) -> float:
    """The step of the displayed values: 0.01 when they have two decimals, 1 when integers."""
    decimals = x.dropna().map(lambda v: len(f"{v:.6f}".rstrip("0").split(".")[1]))
    return 10.0 ** -int(decimals.max()) if len(decimals) else 1.0


def check(atlas: dict) -> None:
    """The workbook agrees with itself and with the transcribed thresholds."""
    for name, frame in atlas.items():
        if isinstance(frame, pd.DataFrame) and (len(frame) != N_UNITS or not frame["ine_code"].is_unique):
            raise ValueError(f"{RAW}: {name} has {len(frame)} rows, expected {N_UNITS} distinct units")
    th = pd.read_csv(store.repo_root() / THRESHOLDS).set_index("code")
    if list(th.index) != atlas["codes"]:
        raise ValueError(f"{THRESHOLDS} does not list the workbook's 81 indicators in order")
    values, normalised, indices = (atlas[k].set_index("ine_code") for k in ("values", "normalised", "indices"))
    for code in atlas["codes"]:
        v, t = varname(code), th.loc[code]
        for year in YEARS:
            x = values[(v, year)]
            rescaled = ((x - t["worst"]) / (t["best"] - t["worst"]) * 100).clip(0, 100)
            gap = (rescaled - normalised[(v, year)]).abs()
            # the workbook shows rounded values (e.g. 6 conflicts for an average of 6.3), while the
            # Atlas rescaled the exact ones: allow half a displayed unit, plus the rounding of the result
            tolerance = 50 * _resolution(x) / abs(t["best"] - t["worst"]) + 0.15
            if (gap > tolerance).any():
                raise ValueError(f"{v} {year}: values rescaled with {THRESHOLDS} differ from the Atlas's "
                                 f"normalised values by up to {gap.max():.2f}")
    for g in GOALS:
        prefix = f"sdg{g}_"
        for year in YEARS:
            cols = [c for c in normalised.columns if c[0].startswith(prefix) and c[1] == year]
            gap = (normalised[cols].mean(axis=1) - indices[(f"index_sdg{g}", year)]).abs()
            if (gap > 0.1).any():
                raise ValueError(f"index_sdg{g} {year}: not the mean of its normalised indicators "
                                 f"(gap up to {gap.max():.2f})")
    for year in YEARS:
        ids = atlas["context"].set_index("ine_code")[("index_sdg", year)]
        gap = (indices[[(f"index_sdg{g}", year) for g in GOALS]].mean(axis=1) - ids).abs()
        if (gap > 0.1).any():
            raise ValueError(f"index_sdg {year}: not the mean of the 15 goal indices (gap up to {gap.max():.2f})")


def long(wide: pd.DataFrame) -> pd.DataFrame:
    """Columns (variable, year) -> one row per unit and year."""
    df = wide.set_index("ine_code")
    df.columns = pd.MultiIndex.from_tuples(df.columns, names=["variable", "year"])
    return df.stack("year", future_stack=True).reset_index()


def link(df: pd.DataFrame) -> pd.DataFrame:
    df["geo_id"] = df["ine_code"].map(ids_from_units(SCALE, "ine_code"))
    if df["geo_id"].isna().any():
        raise ValueError(f"INE codes without a {SCALE} unit: {sorted(df.loc[df['geo_id'].isna(), 'ine_code'].unique())}")
    df["mun_id"] = df["ine_code"].astype(int)
    return df


def _check_fields(name: str, df: pd.DataFrame) -> None:
    fields = [f["name"] for f in metadata.fields(name) if f.get("geo:role", "variable") == "variable"]
    extra = set(fields) - set(df.columns)
    if extra:
        raise ValueError(f"{name}: metadata variables missing from the Atlas: {sorted(extra)}")


def build(goal: int) -> None:
    name = dataset(goal)
    atlas = read()
    check(atlas)
    wide = atlas["indices"].set_index("ine_code").join(atlas["values"].set_index("ine_code"))
    keep = [c for c in wide.columns if c[0] == f"index_sdg{goal}" or c[0].startswith(f"sdg{goal}_")]
    df = link(long(wide[keep].reset_index()))
    _check_fields(name, df)
    publish(name, SCALE, df)
    write_docs(name)


def build_ids() -> None:
    """The overall index (IDS), its national ranking and the census context."""
    atlas = read()
    check(atlas)
    ctx = atlas["context"]
    census = _census()
    atlas_pop = ctx.set_index("ine_code")["population_2024"]
    differ = atlas_pop[atlas_pop != census.set_index("ine_code")[("population", 2024)].reindex(atlas_pop.index)]
    if set(differ.index) != set(POPULATION_DIFFERS):
        raise ValueError(f"the Atlas's 2024 population differs from the SDSN map's census population in {list(differ.index)}")
    wide = ctx.set_index("ine_code")[[("index_sdg", 2012), ("index_sdg", 2024), ("rank_sdg", 2012), ("rank_sdg", 2024)]]
    wide = wide.join(census.set_index("ine_code"))
    wide[("urbanization", 2012)] = np.nan
    wide[("urbanization", 2024)] = ctx.set_index("ine_code")["urbanization"]
    wide = wide.reset_index()
    df = link(long(wide))
    df["rank_sdg"] = df["rank_sdg"].astype("Int64")
    df["population"] = df["population"].astype("Int64")
    _check_fields("sdg", df)
    publish("sdg", SCALE, df)
    write_docs("sdg")


def _census() -> pd.DataFrame:
    """Census population 2012 and 2024 from the SDSN map's attribute table."""
    import geopandas as gpd

    table = gpd.read_file(store.repo_root() / CENSUS, ignore_geometry=True)
    return pd.DataFrame({"ine_code": _codes(table["Codigo_INE"]),
                         ("population", 2012): table["Pob_2012"].astype(int),
                         ("population", 2024): table["Pob_2024"].astype(int)})


BUILDERS = {"sdg": build_ids, **{dataset(g): partial(build, g) for g in GOALS}}
