from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import Polygon
from streamlit.testing.v1 import AppTest

from main import _load_admin, _load_natura, compute_ratio


@pytest.fixture
def mock_natura_gdf():
    # Create a simple mock GeoDataFrame for Natura2000 areas with real geometry
    return gpd.GeoDataFrame(
        {
            'geometry': [
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
            ],
            'text': ['Site1', 'Site2'],
        },
        crs='EPSG:4326',
    )


@pytest.fixture
def mock_pagasti_gdf():
    # Create a simple mock GeoDataFrame for pagasti with real geometry
    return gpd.GeoDataFrame(
        {
            'geometry': [
                Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
                Polygon([(2, 2), (4, 2), (4, 4), (2, 4)]),
            ],
            'LABEL': ['Pagasts1', 'Pagasts2'],
        },
        crs='EPSG:4326',
    )


@pytest.fixture
def mock_novadi_gdf():
    # Create a simple mock GeoDataFrame for novadi with real geometry
    return gpd.GeoDataFrame(
        {
            'geometry': [
                Polygon([(0, 0), (4, 0), (4, 4), (0, 4)]),
                Polygon([(4, 4), (8, 4), (8, 8), (4, 8)]),
            ],
            'NOSAUKUMS': ['Novads1', 'Novads2'],
        },
        crs='EPSG:4326',
    )


def test_load_natura(mock_natura_gdf):
    with patch('main.gpd.read_file') as mock_read:
        mock_read.return_value = mock_natura_gdf
        result = _load_natura()
        assert result.equals(mock_natura_gdf)


def test_load_admin(mock_pagasti_gdf, mock_novadi_gdf):
    with patch('main.gpd.read_file') as mock_read:
        mock_read.side_effect = [mock_pagasti_gdf, mock_novadi_gdf]
        pagasti, novadi = _load_admin()
        assert pagasti.equals(mock_pagasti_gdf)
        assert novadi.equals(mock_novadi_gdf)


def test_compute_ratio_pagasti(mock_natura_gdf, mock_pagasti_gdf):
    with (
        patch('main._load_natura') as mock_load_natura,
        patch('main._load_admin') as mock_load_admin,
    ):
        mock_load_natura.return_value = mock_natura_gdf
        mock_load_admin.return_value = (mock_pagasti_gdf, None)

        admin_metric, natura_wgs, overlap = compute_ratio('Pagasti')

        # Basic checks
        assert admin_metric is not None
        assert natura_wgs is not None
        assert overlap is not None
        assert 'nature_ratio_pct' in admin_metric.columns


def test_compute_ratio_novadi(mock_natura_gdf, mock_novadi_gdf):
    with (
        patch('main._load_natura') as mock_load_natura,
        patch('main._load_admin') as mock_load_admin,
    ):
        mock_load_natura.return_value = mock_natura_gdf
        mock_load_admin.return_value = (None, mock_novadi_gdf)

        admin_metric, natura_wgs, overlap = compute_ratio('Novadi')

        # Basic checks
        assert admin_metric is not None
        assert natura_wgs is not None
        assert overlap is not None
        assert 'nature_ratio_pct' in admin_metric.columns


def test_main_function_with_apptest():
    """Test the main function using Streamlit's AppTest class."""
    # Create a script that includes the necessary imports and calls _main
    script = """
import streamlit as st
from main import _main
_main()
"""

    # Create an AppTest instance from the script
    at = AppTest.from_string(script)

    # Mock the data loading and computation functions
    with (
        patch('main._load_natura') as mock_load_natura,
        patch('main._load_admin') as mock_load_admin,
        patch('main.compute_ratio') as mock_compute,
    ):
        # Setup mock data
        mock_natura = gpd.GeoDataFrame(
            {
                'geometry': [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
                'text': ['TestSite'],
            },
            crs='EPSG:4326',
        )

        mock_pagasti = gpd.GeoDataFrame(
            {
                'geometry': [Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])],
                'LABEL': ['TestPagasts'],
            },
            crs='EPSG:4326',
        )

        mock_load_natura.return_value = mock_natura
        mock_load_admin.return_value = (mock_pagasti, None)
        mock_compute.return_value = (
            mock_pagasti,
            mock_natura,
            gpd.GeoDataFrame(
                {
                    'geometry': [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
                    'LABEL': ['TestPagasts'],
                    'text': ['TestSite'],
                    'nature_ratio_pct': [50.0],
                    'site_ratio_pct': [25.0],
                },
                crs='EPSG:4326',
            ),
        )

        # Run the app
        at.run()

        # Test that the title is displayed
        assert len(at.title) == 1
        assert 'Natura2000 teritoriju platības pagastos un novados' in at.title[0].value

        # Test that the pills widget is displayed with correct options
        assert len(at.button_group) == 1
        pills = at.button_group[0]
        assert pills.label == 'Administratīvais iedalījums'
        assert pills.options == ['Pagasti', 'Novadi']
        assert pills.value == 'Pagasti'

        # Test that the dataframe is displayed
        assert len(at.dataframe) == 1

        # Test that the divider is displayed
        assert len(at.divider) == 1

        # Test that the caption is displayed
        assert len(at.caption) == 1
        assert 'Dati no Latvijas Atvērto datu portāla' in at.caption[0].value


def test_main_function_admin_level_switch():
    """Test switching between admin levels in the app."""
    script = """
import streamlit as st
from main import _main
_main()
"""

    at = AppTest.from_string(script)

    with (
        patch('main._load_natura') as mock_load_natura,
        patch('main._load_admin') as mock_load_admin,
        patch('main.compute_ratio') as mock_compute,
    ):
        # Setup mock data for both admin levels
        mock_natura = gpd.GeoDataFrame(
            {
                'geometry': [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
                'text': ['TestSite'],
            },
            crs='EPSG:4326',
        )

        mock_pagasti = gpd.GeoDataFrame(
            {
                'geometry': [Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])],
                'LABEL': ['TestPagasts'],
            },
            crs='EPSG:4326',
        )

        mock_novadi = gpd.GeoDataFrame(
            {
                'geometry': [Polygon([(0, 0), (4, 0), (4, 4), (0, 4)])],
                'NOSAUKUMS': ['TestNovads'],
            },
            crs='EPSG:4326',
        )

        mock_load_natura.return_value = mock_natura
        mock_load_admin.return_value = (mock_pagasti, mock_novadi)

        # Mock compute_ratio to return appropriate data based on admin level
        def compute_ratio_side_effect(admin_level):
            if admin_level == 'Pagasti':
                return (
                    mock_pagasti,
                    mock_natura,
                    gpd.GeoDataFrame(
                        {
                            'geometry': [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
                            'LABEL': ['TestPagasts'],
                            'text': ['TestSite'],
                            'nature_ratio_pct': [50.0],
                            'site_ratio_pct': [25.0],
                        },
                        crs='EPSG:4326',
                    ),
                )
            else:
                return (
                    mock_novadi,
                    mock_natura,
                    gpd.GeoDataFrame(
                        {
                            'geometry': [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
                            'NOSAUKUMS': ['TestNovads'],
                            'text': ['TestSite'],
                            'nature_ratio_pct': [25.0],
                            'site_ratio_pct': [12.5],
                        },
                        crs='EPSG:4326',
                    ),
                )

        mock_compute.side_effect = compute_ratio_side_effect

        # Run the app with default (Pagasti)
        at.run()

        # Verify the compute_ratio was called with correct parameter
        assert mock_compute.call_args_list[-1][0][0] == 'Pagasti'

        # Switch to Novadi by setting the widget value directly
        at.button_group[0].set_value('Novadi').run()
        at.run()

        # Verify the compute_ratio was called with correct parameter
        assert mock_compute.call_args_list[-1][0][0] == 'Novadi'

        # Verify the dataframe shows Novadi data
        df = at.dataframe[0]
        assert 'TestNovads' in str(df.value)
