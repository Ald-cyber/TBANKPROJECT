import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(layout="wide", page_title="Витрина новостроек России")
st.title("🏙 Витрина новостроек")

# ---------- Загрузка ----------
@st.cache_data
def load():
    df = pd.read_csv("production_data_merged.csv")
    df["rooms"] = pd.to_numeric(df["rooms"], errors="coerce").fillna(0).astype(int)
    df["completion_year"] = pd.to_numeric(df["completion_year"], errors="coerce")
    df["metro_distance_min"] = pd.to_numeric(df["metro_distance_min"], errors="coerce")
    df["price_mln"] = pd.to_numeric(df["price_mln"], errors="coerce")
    df["price_per_sqm"] = pd.to_numeric(df["price_per_sqm"], errors="coerce")
    return df

df = load()

# ---------- Сайдбар: МНОГО фильтров ----------
with st.sidebar:
    st.header("🔍 Фильтры")

    # 1. Город
    cities = sorted(df["city"].dropna().unique())
    sel_cities = st.multiselect("Город", cities, default=cities[:1])

    # 2. Источник
    sources = sorted(df["source"].dropna().unique())
    sel_sources = st.multiselect("Источник данных", sources, default=sources)

    # 3. Застройщик
    developers = sorted(df["developer"].dropna().unique()) if "developer" in df else []
    sel_devs = st.multiselect("Застройщик", developers, default=[])

    # 4. Класс
    classes = sorted(df["complex_class"].dropna().unique()) if "complex_class" in df else []
    sel_classes = st.multiselect("Класс ЖК", classes, default=classes)

    # 5. Цена
    if df["price_mln"].notna().any():
        pmin, pmax = float(df["price_mln"].min()), float(df["price_mln"].max())
        price_range = st.slider("Цена, млн ₽", pmin, pmax, (pmin, min(pmax, 30.0)), step=0.5)

    # 6. Цена за м²
    if df["price_per_sqm"].notna().any():
        sqm_min = int(df["price_per_sqm"].min(skipna=True))
        sqm_max = int(df["price_per_sqm"].max(skipna=True))
        sqm_range = st.slider("₽ за м²", sqm_min, sqm_max,
                              (sqm_min, min(sqm_max, 400_000)), step=1000)

    # 7. Комнаты
    rooms = sorted(df["rooms"].unique())
    sel_rooms = st.multiselect("Комнат", rooms, default=rooms)

    # 8. Площадь
    if df["total_area"].notna().any():
        a_min, a_max = float(df["total_area"].min()), float(df["total_area"].max())
        area_range = st.slider("Площадь, м²", a_min, a_max, (a_min, min(a_max, 150.0)), step=1.0)

    # 9. Этаж
    if df["floor"].notna().any():
        f_min, f_max = int(df["floor"].min()), int(df["floor"].max())
        floor_range = st.slider("Этаж", f_min, f_max, (f_min, f_max))

    # 10. Этажей в доме
    if df["total_floors"].notna().any():
        tf_min, tf_max = int(df["total_floors"].min()), int(df["total_floors"].max())
        tf_range = st.slider("Этажей в доме", tf_min, tf_max, (tf_min, tf_max))

    # 11. Метро (расстояние)
    if df["metro_distance_min"].notna().any():
        m_max = int(df["metro_distance_min"].max(skipna=True))
        metro_max = st.slider("До метро, мин", 0, min(m_max, 60), 30)

    # 12. Год сдачи
    if df["completion_year"].notna().any():
        y_min = int(df["completion_year"].min(skipna=True))
        y_max = int(df["completion_year"].max(skipna=True))
        year_range = st.slider("Год сдачи", y_min, y_max, (y_min, y_max))

    # 13. Готовность
    statuses = sorted(df["status"].dropna().unique()) if "status" in df else []
    sel_status = st.multiselect("Статус", statuses, default=statuses)

    # 14. Отделка
    finishes = sorted(df["decoration"].dropna().unique()) if "decoration" in df else []
    sel_finish = st.multiselect("Отделка", finishes, default=[])

    # 15. Ипотека
    only_mortgage = st.checkbox("Только со льготной ипотекой", value=False)

    # 16. Только с координатами
    only_geo = st.checkbox("Только с координатами на карте", value=True)

# ---------- Применение фильтров ----------
f = df.copy()
f = f[f["city"].isin(sel_cities)]
f = f[f["source"].isin(sel_sources)]
if sel_devs:
    f = f[f["developer"].isin(sel_devs)]
if sel_classes:
    f = f[f["complex_class"].isin(sel_classes)]
f = f[f["rooms"].isin(sel_rooms)]
f = f[f["price_mln"].between(*price_range)]
f = f[f["price_per_sqm"].between(*sqm_range) | f["price_per_sqm"].isna()]
f = f[f["total_area"].between(*area_range) | f["total_area"].isna()]
f = f[f["floor"].between(*floor_range) | f["floor"].isna()]
f = f[f["total_floors"].between(*tf_range) | f["total_floors"].isna()]
f = f[(f["metro_distance_min"] <= metro_max) | f["metro_distance_min"].isna()]
f = f[f["completion_year"].between(*year_range) | f["completion_year"].isna()]
if sel_status:
    f = f[f["status"].isin(sel_status)]
if sel_finish:
    f = f[f["decoration"].isin(sel_finish)]
if only_mortgage:
    f = f[f["mortgage_allowed"] == True]
if only_geo:
    f = f[f["lat"].notna() & f["lon"].notna()]

st.markdown(f"### Найдено: **{len(f)}** из {len(df)} ЖК")

# ---------- Метрики ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("ЖК", len(f))
c2.metric("Ср. цена, млн ₽", f"{f['price_mln'].mean():.2f}" if len(f) else "—")
c3.metric("Ср. ₽/м²", f"{int(f['price_per_sqm'].mean()):,}".replace(",", " ") if len(f) else "—")
c4.metric("Ср. до метро, мин", f"{f['metro_distance_min'].mean():.1f}" if len(f) else "—")

# ---------- Карта + таблица в табах ----------
tab_map, tab_table, tab_compare, tab_stats = st.tabs(
    ["🗺 Карта", "📋 Таблица", "⚖️ Сравнение", "📊 Аналитика"]
)

with tab_map:
    if len(f) == 0:
        st.warning("Нет объектов под фильтры")
    else:
        center = [f["lat"].mean(), f["lon"].mean()]
        m = folium.Map(location=center, zoom_start=10, tiles="OpenStreetMap")

        # Кластеры точек
        cluster = MarkerCluster().add_to(m)

        colors = {"business": "green", "comfort": "blue", "elite": "red",
                  "эконом": "gray", "комфорт": "blue", "бизнес": "green", "элит": "red"}

        for _, r in f.iterrows():
            color = colors.get(str(r.get("complex_class", "")).lower(), "purple")
            popup = folium.Popup(
                f"<b>{r.get('complex_name','—')}</b><br>"
                f"Застройщик: {r.get('developer','—')}<br>"
                f"Класс: {r.get('complex_class','—')}<br>"
                f"Цена: {r.get('price_mln', 0):.2f} млн ₽<br>"
                f"₽/м²: {int(r.get('price_per_sqm', 0) or 0):,}<br>".replace(",", " ") +
                f"{r.get('rooms', '—')} комн · {r.get('total_area', '—')} м²<br>"
                f"Метро: {r.get('metro_station','—')} ({r.get('metro_distance_min','—')} мин)<br>"
                f"Сдача: {r.get('completion_year','—')}<br>"
                f"<a href='{r.get('url','#')}' target='_blank'>Открыть источник</a>",
                max_width=300,
            )
            folium.CircleMarker(
                [r["lat"], r["lon"]],
                radius=7, color=color, fill=True, fill_opacity=0.85, weight=1,
                popup=popup,
            ).add_to(cluster)

        # Легенда
        legend = """
        <div style="position:fixed;bottom:30px;left:30px;z-index:9999;background:white;
        padding:10px;border:1px solid #999;border-radius:6px;font-size:12px">
        <b>Класс:</b><br>🟢 бизнес &nbsp; 🔵 комфорт &nbsp; 🔴 элит &nbsp; ⚪ эконом
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend))
        st_folium(m, height=650, use_container_width=True)

with tab_table:
    st.dataframe(
        f[["complex_name", "developer", "complex_class", "city", "district",
           "rooms", "total_area", "floor", "total_floors", "price_mln",
           "price_per_sqm", "metro_station", "metro_distance_min",
           "completion_year", "status", "source", "url"]],
        use_container_width=True, height=600,
    )
    st.download_button("📥 Скачать CSV",
                       f.to_csv(index=False).encode("utf-8"),
                       "filtered.csv", "text/csv")

with tab_compare:
    if len(f) < 2:
        st.info("Выбери минимум 2 ЖК для сравнения")
    else:
        names = f["complex_name"].dropna().unique().tolist()
        picks = st.multiselect("Выбери ЖК", names, default=names[:3], max_selections=5)
        cmp = f[f["complex_name"].isin(picks)].set_index("complex_name")
        st.dataframe(cmp.T, use_container_width=True)

with tab_stats:
    if len(f) == 0:
        st.warning("Нет данных")
    else:
        import plotly.express as px
        # Распределение цен
        st.subheader("Распределение цен, млн ₽")
        st.plotly_chart(px.histogram(f, x="price_mln", nbins=30), use_container_width=True)

        # Цена по классу
        st.subheader("Цена за м² по классу")
        st.plotly_chart(
            px.box(f.dropna(subset=["price_per_sqm", "complex_class"]),
                   x="complex_class", y="price_per_sqm"),
            use_container_width=True,
        )

        # Средняя цена по округам
        if "okrug" in f and f["okrug"].notna().any():
            st.subheader("Средняя цена за м² по округам")
            grp = f.groupby("okrug")["price_per_sqm"].mean().sort_values(ascending=False).head(15)
            st.bar_chart(grp)

        # Топ застройщиков
        if "developer" in f:
            st.subheader("Топ застройщиков по числу ЖК")
            st.bar_chart(f["developer"].value_counts().head(15))