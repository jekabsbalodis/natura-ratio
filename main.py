"""Main Streamlit app "Natura ratio" entrypoint.

The app is designed to display layers for municipality borders and Natura2000 areas,
as well as calculating the ratio of Natura2000 area to total municipality's area.
"""

import json
import os
import tempfile

import geopandas as gpd
import httpx
import py7zr
import pydeck as pdk
import streamlit as st


@st.cache_data(show_spinner='Ielādē datus par Natura2000 teritorijām...')
def _load_natura():
    gdf = gpd.read_file(
        st.secrets['natura2000_url'],
        use_arrow=True,
    )
    return gdf


@st.cache_data(show_spinner='Ielādē datus par administratīvajām robežām...')
def _load_admin():
    pagasti_url = st.secrets['pagasti_url']
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = os.path.join(tmpdir, 'archive.7z')
        with httpx.Client() as client:
            response = client.get(pagasti_url)

            with open(archive_path, 'wb') as f:
                f.write(response.content)

        with py7zr.SevenZipFile(archive_path, mode='r') as z:
            z.extractall(path=tmpdir)
        pagasti_gdf = gpd.read_file(os.path.join(tmpdir, 'Pagasti.shp'))

    novadi_gdf = gpd.read_file(st.secrets['novadi_url'])

    return pagasti_gdf, novadi_gdf


@st.cache_data(show_spinner='Veic aprēķinus...')
def compute_ratio(admin_level) -> tuple[gpd.GeoDataFrame, ...]:
    """Compute the ratio of the Natura2000 area to selected administrative level.

    Args:
        admin_level: The user selected admin_level, either "Pagasti" or "Novadi"

    Returns:
        Tuple of GeoDataFrames with computed ratios.

    """
    natura_gdf = _load_natura()
    pagasti_gdf, novadi_gdf = _load_admin()

    admin_gdf = pagasti_gdf if admin_level == 'Pagasti' else novadi_gdf

    admin_metric = admin_gdf.to_crs(epsg=3059)
    natura_metric = natura_gdf.to_crs(epsg=3059)

    admin_metric['muni_id'] = range(len(admin_gdf))
    admin_metric['muni_area'] = admin_metric.geometry.area

    natura_metric['total_site_area'] = natura_metric.geometry.area

    overlap = admin_metric.overlay(
        natura_metric, how='intersection', keep_geom_type=False
    )
    overlap['nature_area'] = overlap.geometry.area

    overlap['nature_ratio_pct'] = (
        overlap['nature_area']
        / admin_metric.set_index('muni_id').loc[overlap['muni_id'], 'muni_area'].values
        * 100
    ).round(1)

    overlap['site_ratio_pct'] = (
        overlap['nature_area'] / overlap['total_site_area'] * 100
    ).round(1)

    nature_by_muni = overlap.groupby('muni_id')['nature_area'].sum().reset_index()

    admin_metric = admin_metric.merge(nature_by_muni, on='muni_id', how='left')
    admin_metric['nature_area'] = admin_metric['nature_area'].fillna(0)
    admin_metric['nature_ratio'] = (
        admin_metric['nature_area'] / admin_metric['muni_area']
    )
    admin_metric['nature_ratio_pct'] = (admin_metric['nature_ratio'] * 100).round(1)

    return admin_metric.to_crs(epsg=4326), natura_gdf.to_crs(epsg=4326), overlap


def _gdf_to_geojson(gdf):
    return json.loads(gdf.to_json())


def _main():
    st.set_page_config(
        page_title='Natura ratio',
        page_icon='🏞️',
        layout='wide',
        menu_items={
            'Get help': 'https://mastodon.social/@khorticija',
            'Report a bug': 'https://codeberg.org/clear9550/natura-ratio/issues',
            'About': None,
        },
    )

    col1, col2 = st.columns([0.7, 0.3])

    with col1:
        st.title('Natura2000 teritoriju platības pagastos un novados')

    with col2:
        admin_level = st.pills(
            'Administratīvais iedalījums',
            ['Pagasti', 'Novadi'],
            default='Pagasti',
            help=(
                'Izvēlies pēc kāda administratīvā iedalījuma attēlot datus. '
                '"Novadi", iekļauj arī pilsētas.'
            ),
        )

    (admin_wgs, natura_wgs, overlap) = compute_ratio(admin_level)

    admin_layer = pdk.Layer(
        'GeoJsonLayer',
        data=_gdf_to_geojson(admin_wgs),
        stroked=True,
        filled=True,
        get_fill_color='[20, 80 + nature_ratio * 170, 80, 180]',
        get_line_color=[255, 255, 255, 200],
        line_width_min_pixels=1,
        pickable=True,
    )

    natura_layer = pdk.Layer(
        'GeoJsonLayer',
        data=_gdf_to_geojson(natura_wgs),
        stroked=True,
        filled=True,
        get_fill_color=[255, 200, 0, 180],
        get_line_color=[200, 150, 0, 255],
        line_width_min_pixels=1,
        pickable=False,
    )

    view_state = pdk.ViewState(
        latitude=56.9,
        longitude=24.6,
        zoom=6.5,
        pitch=0,
    )

    name_col = 'LABEL' if admin_level == 'Pagasti' else 'NOSAUKUMS'

    tooltip_html = (
        f'<b>{{{name_col}}}</b><br/>Natura2000 pārklājums: <b>{{nature_ratio_pct}}%</b>'
    )

    deck = pdk.Deck(
        layers=[admin_layer, natura_layer],
        initial_view_state=view_state,
        map_style='light',
        tooltip={
            'html': tooltip_html,
            'style': {'backgroundColor': 'white', 'color': 'black', 'padding': '8px'},
        },
    )
    col3, col4 = st.columns([0.65, 0.35])

    with col3:
        st.pydeck_chart(deck, height=700)

    with col4:
        admin_name_col = 'LABEL' if admin_level == 'Pagasti' else 'NOSAUKUMS'
        admin_name_col_label = 'Pagasts' if admin_level == 'Pagasti' else 'Novads'
        nature_ratio_pct_label = (
            '% no pagasta' if admin_level == 'Pagasti' else '% no novada'
        )
        st.dataframe(
            overlap[[admin_name_col, 'text', 'nature_ratio_pct', 'site_ratio_pct']]
            .rename(
                columns={
                    admin_name_col: admin_name_col_label,
                    'text': 'Natura2000 teritorija',
                    'nature_ratio_pct': nature_ratio_pct_label,
                    'site_ratio_pct': '% no Natura2000 ter.',
                }
            )
            .sort_values('Natura2000 teritorija', ascending=True)
            .reset_index(drop=True),
            hide_index=True,
            height=700,
        )

    st.divider()

    st.caption(
        body=(
            'Dati no Latvijas Atvērto datu portāla | '
            '[Natura2000 teritorijas]'
            '(https://data.gov.lv/dati/lv/dataset/lv-natura2000-data) | '
            '[Novadu robežas]'
            '(https://data.gov.lv/dati/lv/dataset/atr) | '
            '[Pagastu robežas]'
            '(https://data.gov.lv/dati/lv/dataset/administrativo-teritoriju-karte)'
        )
    )


if __name__ == '__main__':
    _main()
