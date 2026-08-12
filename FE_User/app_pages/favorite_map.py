import pydeck as pdk
import streamlit as st

from clients.location_client import geocode_location
from core.api_client import BackendAPIError

MAP_STYLE = (
    "https://basemaps.cartocdn.com/gl/positron-gl-style/"
    "style.json"
)
DEFAULT_MAP_LATITUDE = 37.5665
DEFAULT_MAP_LONGITUDE = 126.9780


@st.cache_data(show_spinner=False)
def geocode_favorite_address(address: str) -> tuple[float, float] | None:
    """백엔드 위치 API를 통해 즐겨찾기 주소를 지도 좌표로 변환합니다."""

    response = geocode_location(address)
    location = response.get("data") or {}
    latitude = location.get("latitude")
    longitude = location.get("longitude")

    if latitude is None or longitude is None:
        return None

    return float(latitude), float(longitude)


def build_favorite_deck(points: list[dict]) -> pdk.Deck:
    """좌표가 없어도 기본 지도를 만들고, 좌표가 있으면 모든 위치에 핀을 표시합니다."""

    if points:
        latitude = sum(point["latitude"] for point in points) / len(points)
        longitude = sum(point["longitude"] for point in points) / len(points)

        latitude_span = max(point["latitude"] for point in points) - min(
            point["latitude"] for point in points
        )
        longitude_span = max(point["longitude"] for point in points) - min(
            point["longitude"] for point in points
        )
        coordinate_span = max(latitude_span, longitude_span)

        if len(points) == 1:
            zoom = 13
        elif coordinate_span >= 5:
            zoom = 5
        elif coordinate_span >= 2:
            zoom = 6
        elif coordinate_span >= 1:
            zoom = 7
        elif coordinate_span >= 0.5:
            zoom = 8
        elif coordinate_span >= 0.2:
            zoom = 9
        else:
            zoom = 11
    else:
        latitude = DEFAULT_MAP_LATITUDE
        longitude = DEFAULT_MAP_LONGITUDE
        zoom = 9

    layers = []
    if points:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=points,
                get_position="[longitude, latitude]",
                get_fill_color=[229, 57, 53],
                get_line_color=[255, 255, 255],
                get_radius=120,
                radius_min_pixels=9,
                radius_max_pixels=18,
                line_width_min_pixels=2,
                stroked=True,
                pickable=True,
                auto_highlight=True,
            )
        )

    return pdk.Deck(
        map_style=MAP_STYLE,
        initial_view_state=pdk.ViewState(
            latitude=latitude,
            longitude=longitude,
            zoom=zoom,
            pitch=0,
        ),
        layers=layers,
        tooltip={
            "html": "<b>{title}</b><br/>{location}",
            "style": {
                "backgroundColor": "#263238",
                "color": "white",
            },
        },
    )


def render_favorite_map(favorites: list[dict]) -> None:
    """기본 지도를 먼저 띄우고 즐겨찾기 주소 전체를 핀으로 표시합니다."""

    points = []
    failed_locations = []
    map_placeholder = st.empty()

    map_placeholder.pydeck_chart(
        build_favorite_deck(points),
        use_container_width=True,
    )

    with st.spinner("즐겨찾기 위치를 찾는 중입니다..."):
        for favorite in favorites:
            listing = favorite.get("listing") or {}
            location = (
                listing.get("detail_address")
                or listing.get("location")
                or ""
            ).strip()
            if not location:
                continue

            try:
                coordinates = geocode_favorite_address(location)
            except (BackendAPIError, KeyError, TypeError, ValueError):
                failed_locations.append(location)
                continue

            if coordinates is None:
                failed_locations.append(location)
                continue

            latitude, longitude = coordinates
            points.append(
                {
                    "title": listing.get("title") or "제목 없음",
                    "location": location,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )

    map_placeholder.pydeck_chart(
        build_favorite_deck(points),
        use_container_width=True,
    )

    if points:
        st.caption(f"즐겨찾기 위치 {len(points)}건을 지도에 표시했습니다.")
    else:
        st.info("지도에 표시할 수 있는 즐겨찾기 주소가 없습니다.")

    if failed_locations:
        st.caption(f"좌표를 찾지 못한 위치: {len(failed_locations)}건")
