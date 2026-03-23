# Natura2000 area ratio analysis app

A Streamlit application to display Natura2000 territories overlaid on
administrative map of Republic of Latvia and calculate ratio of
Natura2000 territory area to municipalities area.

## Features

- Load and visualize Natura2000 territories data
- Load and display administrative boundaries
- Calculate and analyze spatial ratios between protected areas and
  administrative regions

## Installation

1.  Clone this repository:

    ```bash
    git clone https://codeberg.org/clear9550/natura-ratio.git
    cd natura-ratio
    ```

2.  Install dependencies using uv:

    `uv sync`

## Usage

1. Run the Streamlit application:

   `uv run streamlit run main.py`

## Data Functions

### The application includes several key data processing functions:

• `\_load_natura()`: Loads Natura2000 protected areas data with caching
• `\_load_admin()`: Loads administrative boundaries data with caching
• `compute_ratio()`: Calculates spatial ratios between datasets
• `\_gdf_to_geojson()`: Converts GeoDataFrames to GeoJSON format

## Deployment

The application is deployed on [Streamlit Community Cloud](https://natura-ratio.streamlit.app).

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file
for details.
