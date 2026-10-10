import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import plotly.express as px

st.set_page_config(
    layout="wide",
    page_title="Витрина новостроек",
    page_icon="🏙",
)

st.title("🏙 Витрина новостроек России")
st.caption("Данные: ЦИАН + ПИК · единая витрина · фильтры · карта · аналитика")


@st.cache_data
def load():
    df = pd.read_csv("production_data_merged.csv")

    num_cols = [
        "price_rub", "price_per_sqm", "price_mln",
        "total_area", "living_area", "kitchen_area",
        "floor", "total_floors", "ceiling_height",
        "metro_distance_min", "completion_year", "build_year",
        "lat", "lon", "views",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "rooms" in df.columns:
        df["rooms"] = pd.to_numeric(df["rooms"], errors="coerce").fillna(0).astype(int)

    if "price_mln" not in df.columns and "price_rub" in df.columns:
        df["price_mln"] = df["price_rub"] / 1_000_000

    if "price_per_sqm" not in df.columns:
        df["price_per_sqm"] = df["price_rub"] / df["total_area"]

    df = df.loc[:, ~df.columns.duplicated()]

    return df


df = load()

if df.empty:
    st.error("Файл production_data_merged.csv пуст или не найден.")
    st.stop()


with st.sidebar:
    st.header("🔍 Фильтры")

    if "city" in df.columns:
        cities = sorted(df["city"].dropna().unique().tolist())
        sel_cities = st.multiselect("Город", cities, default=cities[:1] if cities else [])
    else:
        sel_cities = []

    if "source" in df.columns:
        sources = sorted(df["source"].dropna().unique().tolist())
        sel_sources = st.multiselect("Источник данных", sources, default=sources)
    else:
        sel_sources = []

    if "developer" in df.columns:
        developers = sorted(df["developer"].dropna().unique().tolist())
        sel_devs = st.multiselect("Застройщик", developers, default=[])
    else:
        sel_devs = []

    if "complex_class" in df.columns:
        classes = sorted(df["complex_class"].dropna().unique().tolist())
        sel_classes = st.multiselect("Класс ЖК", classes, default=classes)
    else:
        sel_classes = []

    price_range = None
    if "price_mln" in df.columns and df["price_mln"].notna().any():
        pmin = float(np.nanmin(df["price_mln"]))
        pmax = float(np.nanmax(df["price_mln"]))
        if pmin < pmax:
            price_range = st.slider(
                "Цена, млн ₽",
                pmin, pmax,
                (pmin, min(pmax, 30.0)),
                step=0.5,
            )

    sqm_range = None
    if "price_per_sqm" in df.columns and df["price_per_sqm"].notna().any():
        s_min = int(np.nanmin(df["price_per_sqm"]))
        s_max = int(np.nanmax(df["price_per_sqm"]))
        if s_min < s_max:
            sqm_range = st.slider(
                "₽ за м²",
                s_min, s_max,
                (s_min, min(s_max, 400_000)),
                step=1000,
            )

    if "rooms" in df.columns:
        rooms_all = sorted(df["rooms"].dropna().unique().tolist())
        sel_rooms = st.multiselect("Комнат", rooms_all, default=rooms_all)
    else:
        sel_rooms = []

    area_range = None
    if "total_area" in df.columns and df["total_area"].notna().any():
        a_min = float(np.nanmin(df["total_area"]))
        a_max = float(np.nanmax(df["total_area"]))
        if a_min < a_max:
            area_range = st.slider(
                "Площадь, м²",
                a_min, a_max,
                (a_min, min(a_max, 150.0)),
                step=1.0,
            )

    floor_range = None
    if "floor" in df.columns and df["floor"].notna().any():
        f_min = int(np.nanmin(df["floor"]))
        f_max = int(np.nanmax(df["floor"]))
        if f_min < f_max:
            floor_range = st.slider("Этаж", f_min, f_max, (f_min, f_max))

    tf_range = None
    if "total_floors" in df.columns and df["total_floors"].notna().any():
        tf_min = int(np.nanmin(df["total_floors"]))
        tf_max = int(np.nanmax(df["total_floors"]))
        if tf_min < tf_max:
            tf_range = st.slider("Этажей в доме", tf_min, tf_max, (tf_min, tf_max))

    metro_max = None
    if "metro_distance_min" in df.columns and df["metro_distance_min"].notna().any():
        m_max = int(np.nanmax(df["metro_distance_min"]))
        if m_max > 0:
            metro_max = st.slider("До метро, мин", 0, min(m_max, 60), min(m_max, 30))

    year_range = None
    if "completion_year" in df.columns and df["completion_year"].notna().any():
        y_min = int(np.nanmin(df["completion_year"]))
        y_max = int(np.nanmax(df["completion_year"]))
        if y_min < y_max:
            year_range = st.slider("Год сдачи", y_min, y_max, (y_min, y_max))

    if "status" in df.columns:
        statuses = sorted(df["status"].dropna().unique().tolist())
        sel_status = st.multiselect("Статус", statuses, default=statuses)
    else:
        sel_status = []

    if "decoration" in df.columns:
        finishes = sorted(df["decoration"].dropna().unique().tolist())
        sel_finish = st.multiselect("Отделка", finishes, default=[])
    else:
        sel_finish = []

    only_mortgage = st.checkbox("Только со льготной ипотекой", value=False)
    only_geo = st.checkbox("Только с координатами на карте", value=True)


f = df.copy()

if sel_cities:
    f = f[f["city"].isin(sel_cities)]
if sel_sources:
    f = f[f["source"].isin(sel_sources)]
if sel_devs:
    f = f[f["developer"].isin(sel_devs)]
if sel_classes:
    f = f[f["complex_class"].isin(sel_classes)]
if sel_rooms:
    f = f[f["rooms"].isin(sel_rooms)]

if price_range is not None:
    f = f[f["price_mln"].between(*price_range) | f["price_mln"].isna()]
if sqm_range is not None:
    f = f[f["price_per_sqm"].between(*sqm_range) | f["price_per_sqm"].isna()]
if area_range is not None:
    f = f[f["total_area"].between(*area_range) | f["total_area"].isna()]
if floor_range is not None:
    f = f[f["floor"].between(*floor_range) | f["floor"].isna()]
if tf_range is not None:
    f = f[f["total_floors"].between(*tf_range) | f["total_floors"].isna()]
if metro_max is not None:
    f = f[(f["metro_distance_min"] <= metro_max) | f["metro_distance_min"].isna()]
if year_range is not None:
    f = f[f["completion_year"].between(*year_range) | f["completion_year"].isna()]

if sel_status:
    f = f[f["status"].isin(sel_status)]
if sel_finish:
    f = f[f["decoration"].isin(sel_finish)]
if only_mortgage and "mortgage_allowed" in f.columns:
    f = f[f["mortgage_allowed"] == True]
if only_geo:
    f = f[f["lat"].notna() & f["lon"].notna()]

st.markdown(f"### Найдено: **{len(f)}** из {len(df)} ЖК")


c1, c2, c3, c4 = st.columns(4)
c1.metric("ЖК", len(f))

if len(f) and f["price_mln"].notna().any():
    c2.metric("Ср. цена, млн ₽", f"{f['price_mln'].mean():.2f}")
else:
    c2.metric("Ср. цена, млн ₽", "—")

if len(f) and f["price_per_sqm"].notna().any():
    c3.metric("Ср. ₽/м²", f"{int(f['price_per_sqm'].mean()):,}".replace(",", " "))
else:
    c3.metric("Ср. ₽/м²", "—")

if len(f) and f["metro_distance_min"].notna().any():
    c4.metric("Ср. до метро, мин", f"{f['metro_distance_min'].mean():.1f}")
else:
    c4.metric("Ср. до метро, мин", "—")


tab_map, tab_table, tab_stats = st.tabs(["🗺 Карта", "📋 Таблица", "📊 Аналитика"])


with tab_map:
    if len(f) == 0:
        st.warning("Нет объектов под текущие фильтры")
    else:
        center = [f["lat"].mean(), f["lon"].mean()]
        m = folium.Map(location=center, zoom_start=10, tiles="OpenStreetMap")
        cluster = MarkerCluster().add_to(m)

        colors = {
            "business": "green", "comfort": "blue", "elite": "red",
            "эконом": "gray", "комфорт": "blue",
            "бизнес": "green", "элит": "red",
        }

        for _, r in f.iterrows():
            cls = str(r.get("complex_class", "")).lower()
            color = colors.get(cls, "purple")

            price_mln = r.get("price_mln", 0)
            price_str = f"{price_mln:.2f} млн ₽" if pd.notna(price_mln) else "—"

            sqm = r.get("price_per_sqm", 0)
            sqm_str = f"{int(sqm):,}".replace(",", " ") if pd.notna(sqm) else "—"

            popup_html = (
                f"<b>{r.get('complex_name', '—')}</b><br>"
                f"Застройщик: {r.get('developer', '—')}<br>"
                f"Класс: {r.get('complex_class', '—')}<br>"
                f"Цена: {price_str}<br>"
                f"₽/м²: {sqm_str}<br>"
                f"{r.get('rooms', '—')} комн · {r.get('total_area', '—')} м²<br>"
                f"Метро: {r.get('metro_station', '—')} "
                f"({r.get('metro_distance_min', '—')} мин)<br>"
                f"Сдача: {r.get('completion_year', '—')}<br>"
                f"<a href='{r.get('url', '#')}' target='_blank'>Открыть источник</a>"
            )

            folium.CircleMarker(
                [r["lat"], r["lon"]],
                radius=7,
                color=color,
                fill=True,
                fill_opacity=0.85,
                weight=1,
                popup=folium.Popup(popup_html, max_width=300),
            ).add_to(cluster)

        legend = """
        <div style="position:fixed;bottom:30px;left:30px;z-index:9999;
        background:white;padding:10px;border:1px solid #999;
        border-radius:6px;font-size:12px">
        <b>Класс:</b><br>
        🟢 бизнес &nbsp; 🔵 комфорт &nbsp; 🔴 элит &nbsp; ⚪ эконом
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend))
        st_folium(m, height=650, use_container_width=True)


with tab_table:
    show_cols = [
        "complex_name", "developer", "complex_class", "city", "district",
        "rooms", "total_area", "floor", "total_floors",
        "price_mln", "price_per_sqm",
        "metro_station", "metro_distance_min",
        "completion_year", "status", "source", "url",
    ]
    show_cols = [c for c in show_cols if c in f.columns]

    if len(f) == 0:
        st.info("Нет данных")
    else:
        table = f[show_cols].copy()
        table = table.loc[:, ~table.columns.duplicated()]

        st.dataframe(table, use_container_width=True, height=600)

        st.download_button(
            "📥 Скачать CSV",
            table.to_csv(index=False).encode("utf-8"),
            "filtered.csv",
            "text/csv",
        )


with tab_stats:
    if len(f) == 0:
        st.warning("Нет данных для аналитики")
    else:
        if f["price_mln"].notna().any():
            st.subheader("Распределение цен, млн ₽")
            st.plotly_chart(
                px.histogram(f.dropna(subset=["price_mln"]), x="price_mln", nbins=30),
                use_container_width=True,
            )

        if "complex_class" in f.columns and f["price_per_sqm"].notna().any():
            box_df = f.dropna(subset=["price_per_sqm", "complex_class"])
            if len(box_df) > 0:
                st.subheader("Цена за м² по классу")
                st.plotly_chart(
                    px.box(box_df, x="complex_class", y="price_per_sqm"),
                    use_container_width=True,
                )

        if "okrug" in f.columns and f["okrug"].notna().any() and f["price_per_sqm"].notna().any():
            st.subheader("Средняя цена за м² по округам")
            grp = (
                f.dropna(subset=["okrug", "price_per_sqm"])
                .groupby("okrug")["price_per_sqm"]
                .mean()
                .sort_values(ascending=False)
                .head(15)
            )
            if len(grp) > 0:
                st.bar_chart(grp)

        if "developer" in f.columns and f["developer"].notna().any():
            st.subheader("Топ застройщиков по числу ЖК")
            top_dev = f["developer"].value_counts().head(15)
            if len(top_dev) > 0:
                st.bar_chart(top_dev)

        if "completion_year" in f.columns and f["completion_year"].notna().any():
            st.subheader("Распределение по годам сдачи")
            yc = f["completion_year"].value_counts().sort_index()
            st.bar_chart(yc)
