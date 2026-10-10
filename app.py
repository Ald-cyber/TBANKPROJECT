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

st.markdown("""
<style>
.zhk-card {
    border: 1px solid #e6e6e6;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    background: #ffffff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.zhk-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.zhk-title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 4px;
    color: #1a1a1a;
}
.zhk-sub {
    color: #666;
    font-size: 13px;
    margin-bottom: 8px;
}
.zhk-price {
    font-size: 22px;
    font-weight: 700;
    color: #0d7a3f;
    margin: 6px 0;
}
.zhk-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    margin-right: 6px;
    background: #eef3ff;
    color: #2b4d9b;
}
.zhk-badge-warn {
    background: #fff4e5;
    color: #b05a00;
}
.zhk-badge-green {
    background: #e7f6ec;
    color: #0d7a3f;
}
</style>
""", unsafe_allow_html=True)


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

    if "price_per_sqm" not in df.columns and "price_rub" in df.columns and "total_area" in df.columns:
        df["price_per_sqm"] = df["price_rub"] / df["total_area"]

    df = df.loc[:, ~df.columns.duplicated()]

    if "id" not in df.columns:
        df["id"] = df.index.astype(str)

    return df


df = load()

if df.empty:
    st.error("Файл production_data_merged.csv пуст или не найден.")
    st.stop()

if "favorites" not in st.session_state:
    st.session_state.favorites = set()


def toggle_fav(zhk_id):
    if zhk_id in st.session_state.favorites:
        st.session_state.favorites.remove(zhk_id)
    else:
        st.session_state.favorites.add(zhk_id)


def reset_filters():
    for k in list(st.session_state.keys()):
        if k.startswith("flt_"):
            del st.session_state[k]


with st.sidebar:
    st.header("🔍 Фильтры")

    st.button("♻️ Сбросить фильтры", on_click=reset_filters, use_container_width=True)

    if "city" in df.columns:
        cities = sorted(df["city"].dropna().unique().tolist())
        sel_cities = st.multiselect(
            "Город", cities,
            default=st.session_state.get("flt_cities", []),
            key="flt_cities",
        )
    else:
        sel_cities = []

    if "source" in df.columns:
        sources = sorted(df["source"].dropna().unique().tolist())
        sel_sources = st.multiselect(
            "Источник данных", sources,
            default=st.session_state.get("flt_sources", sources),
            key="flt_sources",
        )
    else:
        sel_sources = []

    if "developer" in df.columns:
        developers = sorted(df["developer"].dropna().unique().tolist())
        sel_devs = st.multiselect(
            "Застройщик", developers,
            default=st.session_state.get("flt_devs", []),
            key="flt_devs",
        )
    else:
        sel_devs = []

    if "complex_class" in df.columns:
        classes = sorted(df["complex_class"].dropna().unique().tolist())
        sel_classes = st.multiselect(
            "Класс ЖК", classes,
            default=st.session_state.get("flt_classes", []),
            key="flt_classes",
        )
    else:
        sel_classes = []

    st.markdown("**Цена, млн ₽**")
    col_p1, col_p2 = st.columns(2)
    price_from = col_p1.number_input(
        "от", min_value=0.0, value=st.session_state.get("flt_price_from", 0.0),
        step=0.5, key="flt_price_from", label_visibility="collapsed",
    )
    price_to = col_p2.number_input(
        "до", min_value=0.0,
        value=st.session_state.get("flt_price_to", float(np.nanmax(df["price_mln"])) if "price_mln" in df else 0.0),
        step=0.5, key="flt_price_to", label_visibility="collapsed",
    )
    st.caption("от / до")

    st.markdown("**Этаж**")
    col_f1, col_f2 = st.columns(2)
    floor_from = col_f1.number_input(
        "от ", min_value=0, value=st.session_state.get("flt_floor_from", 0),
        step=1, key="flt_floor_from", label_visibility="collapsed",
    )
    floor_to = col_f2.number_input(
        "до ", min_value=0,
        value=st.session_state.get("flt_floor_to", int(np.nanmax(df["floor"])) if "floor" in df else 100),
        step=1, key="flt_floor_to", label_visibility="collapsed",
    )
    st.caption("от / до")

    if "rooms" in df.columns:
        rooms_all = sorted(df["rooms"].dropna().unique().tolist())
        sel_rooms = st.multiselect(
            "Комнат", rooms_all,
            default=st.session_state.get("flt_rooms", []),
            key="flt_rooms",
        )
    else:
        sel_rooms = []

    area_from = st.number_input(
        "Площадь от, м²", min_value=0.0,
        value=st.session_state.get("flt_area_from", 0.0),
        step=1.0, key="flt_area_from",
    )

    if "metro_distance_min" in df.columns and df["metro_distance_min"].notna().any():
        m_max = int(np.nanmax(df["metro_distance_min"]))
        metro_max = st.slider(
            "До метро, мин", 0, m_max, m_max,
            key="flt_metro_max",
        )
    else:
        metro_max = None

    only_mortgage = st.checkbox(
        "Только со льготной ипотекой", value=False, key="flt_mortgage",
    )


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

if "price_mln" in f.columns:
    f = f[
        (f["price_mln"].between(price_from, price_to)) | f["price_mln"].isna()
    ]
if "floor" in f.columns:
    f = f[
        (f["floor"].between(floor_from, floor_to)) | f["floor"].isna()
    ]
if "total_area" in f.columns and area_from > 0:
    f = f[(f["total_area"] >= area_from) | f["total_area"].isna()]
if metro_max is not None and "metro_distance_min" in f.columns:
    f = f[(f["metro_distance_min"] <= metro_max) | f["metro_distance_min"].isna()]
if only_mortgage and "mortgage_allowed" in f.columns:
    f = f[f["mortgage_allowed"] == True]


def fmt_price(row):
    if pd.notna(row.get("price_mln")):
        return f"{row['price_mln']:.2f} млн ₽"
    if pd.notna(row.get("price_rub")):
        return f"{int(row['price_rub']):,} ₽".replace(",", " ")
    return "цена не указана"


def fmt_metro(row):
    name = row.get("metro_station")
    dist = row.get("metro_distance_min")
    if pd.isna(name) and pd.isna(dist):
        return "нет метро"
    if pd.isna(name):
        return f"{int(dist)} мин"
    if pd.isna(dist):
        return str(name)
    return f"{name} · {int(dist)} мин"


def render_card(row, key_prefix):
    zhk_id = str(row["id"])
    is_fav = zhk_id in st.session_state.favorites

    col_left, col_right = st.columns([5, 1])

    with col_left:
        st.markdown(f"""
        <div class="zhk-card">
            <div class="zhk-title">{row.get('complex_name', 'ЖК без названия')}</div>
            <div class="zhk-sub">{row.get('developer', '—')} · {row.get('city', '')} {row.get('district', '') or ''}</div>
            <div>
                <span class="zhk-badge">{row.get('complex_class', 'класс не указан')}</span>
                <span class="zhk-badge">{row.get('rooms', '—')} комн</span>
                <span class="zhk-badge">{row.get('total_area', '—')} м²</span>
                <span class="zhk-badge">этаж {row.get('floor', '—')} из {row.get('total_floors', '—')}</span>
                <span class="zhk-badge-green zhk-badge">{fmt_metro(row)}</span>
            </div>
            <div class="zhk-price">{fmt_price(row)}</div>
            <div class="zhk-sub">
                Сдача: {row.get('completion_year', '—')} ·
                Статус: {row.get('status', '—')} ·
                Источник: {row.get('source', '—')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if pd.notna(row.get("url")):
            st.markdown(f"[🔗 Открыть на {row.get('source', 'сайте')}]({row['url']})")

    with col_right:
        label = "💔 Убрать" if is_fav else "❤ В избранное"
        if st.button(label, key=f"{key_prefix}_{zhk_id}"):
            toggle_fav(zhk_id)
            st.rerun()


tab_cards, tab_map, tab_table, tab_fav, tab_stats = st.tabs(
    ["🏠 Карточки", "🗺 Карта", "📋 Таблица", f"❤ Избранное ({len(st.session_state.favorites)})", "📊 Аналитика"]
)


with tab_cards:
    st.markdown(f"### Найдено: **{len(f)}** из {len(df)} ЖК")

    if len(f) == 0:
        st.info("Нет объектов под текущие фильтры. Попробуй сбросить фильтры.")
    else:
        page_size = 10
        total_pages = max(1, (len(f) + page_size - 1) // page_size)
        page = st.number_input("Страница", min_value=1, max_value=total_pages, value=1, step=1)
        start = (page - 1) * page_size
        end = start + page_size

        for idx, row in f.iloc[start:end].iterrows():
            render_card(row, key_prefix=f"card_{idx}")

        st.caption(f"Страница {page} из {total_pages}")


with tab_map:
    geo = f.dropna(subset=["lat", "lon"]) if "lat" in f.columns else pd.DataFrame()
    if len(geo) == 0:
        st.warning("Нет объектов с координатами под текущие фильтры")
    else:
        center = [geo["lat"].mean(), geo["lon"].mean()]
        m = folium.Map(location=center, zoom_start=10, tiles="OpenStreetMap")
        cluster = MarkerCluster().add_to(m)

        colors = {
            "business": "green", "comfort": "blue", "elite": "red",
            "эконом": "gray", "комфорт": "blue",
            "бизнес": "green", "элит": "red",
        }

        for _, r in geo.iterrows():
            cls = str(r.get("complex_class", "")).lower()
            color = colors.get(cls, "purple")
            popup_html = (
                f"<b>{r.get('complex_name', '—')}</b><br>"
                f"{fmt_price(r)}<br>"
                f"{fmt_metro(r)}<br>"
                f"{r.get('rooms', '—')} комн · {r.get('total_area', '—')} м²"
            )
            folium.CircleMarker(
                [r["lat"], r["lon"]],
                radius=7, color=color, fill=True, fill_opacity=0.85, weight=1,
                popup=folium.Popup(popup_html, max_width=280),
            ).add_to(cluster)

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


with tab_fav:
    fav_ids = st.session_state.favorites
    if not fav_ids:
        st.info("Ты ещё не добавил ни одной новостройки в избранное.")
    else:
        fav_df = df[df["id"].astype(str).isin(fav_ids)]
        st.markdown(f"### В избранном: **{len(fav_df)}** ЖК")

        if st.button("🗑 Очистить избранное"):
            st.session_state.favorites = set()
            st.rerun()

        for idx, row in fav_df.iterrows():
            render_card(row, key_prefix=f"fav_{idx}")


with tab_stats:
    if len(f) == 0:
        st.warning("Нет данных для аналитики")
    else:
        if "price_mln" in f.columns and f["price_mln"].notna().any():
            st.subheader("Распределение цен, млн ₽")
            st.plotly_chart(
                px.histogram(f.dropna(subset=["price_mln"]), x="price_mln", nbins=30),
                use_container_width=True,
            )

        if "complex_class" in f.columns and "price_per_sqm" in f.columns and f["price_per_sqm"].notna().any():
            box_df = f.dropna(subset=["price_per_sqm", "complex_class"])
            if len(box_df) > 0:
                st.subheader("Цена за м² по классу")
                st.plotly_chart(
                    px.box(box_df, x="complex_class", y="price_per_sqm"),
                    use_container_width=True,
                )

        if "city" in f.columns and "price_per_sqm" in f.columns:
            grp = (
                f.dropna(subset=["city", "price_per_sqm"])
                .groupby("city")["price_per_sqm"]
                .mean()
                .sort_values(ascending=False)
                .head(15)
            )
            if len(grp) > 0:
                st.subheader("Средняя цена за м² по городам")
                st.bar_chart(grp)

        if "developer" in f.columns and f["developer"].notna().any():
            st.subheader("Топ застройщиков по числу ЖК")
            st.bar_chart(f["developer"].value_counts().head(15))

        if "completion_year" in f.columns and f["completion_year"].notna().any():
            st.subheader("Распределение по годам сдачи")
            st.bar_chart(f["completion_year"].value_counts().sort_index())
