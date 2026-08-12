"""생활권 분석 결과를 PyDeck 지도로 만드는 모듈입니다."""

from typing import Any
from urllib.parse import quote

import pydeck as pdk


MAP_STYLE = (
    "https://basemaps.cartocdn.com/gl/positron-gl-style/"
    "style.json"
)

FACILITY_STYLES = {
    "subway": {
        "icon": "🚇",
        "label": "지하철역",
        "color": [52, 120, 246],
    },
    "mart": {
        "icon": "🛒",
        "label": "마트",
        "color": [34, 160, 107],
    },
    "hospital": {
        "icon": "🏥",
        "label": "병원",
        "color": [220, 53, 69],
    },
}


def make_icon_data(icon: str) -> dict[str, Any]:
    """이모지를 PyDeck IconLayer에서 사용할 SVG 이미지로 만듭니다."""

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">
        <circle
            cx="32"
            cy="32"
            r="29"
            fill="white"
            stroke="#374151"
            stroke-width="3"
        />
        <text
            x="32"
            y="43"
            text-anchor="middle"
            font-size="32"
            font-family="Segoe UI Emoji, Apple Color Emoji, sans-serif"
        >{icon}</text>
    </svg>
    """

    return {
        "url": (
            "data:image/svg+xml;charset=utf-8,"
            + quote(svg)
        ),
        "width": 64,
        "height": 64,
        "anchorY": 32,
    }


def make_listing_point(
    title: str,
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """공고 위치를 나타내는 지도 데이터를 만듭니다."""

    return {
        "name": title,
        "category_label": "공고 위치",
        "icon": "🏠",
        "icon_data": make_icon_data("🏠"),
        "color": [245, 130, 32],
        "latitude": latitude,
        "longitude": longitude,
        "distance_label": "기준 위치",
        "walking_label": "",
        "map_label": title,
    }


def make_facility_point(
    facility: dict,
) -> dict[str, Any] | None:
    """시설 API 응답 한 건을 지도 데이터로 변환합니다."""

    category = str(facility.get("category") or "")
    style = FACILITY_STYLES.get(category)

    if style is None:
        return None

    try:
        latitude = float(facility["latitude"])
        longitude = float(facility["longitude"])
    except (KeyError, TypeError, ValueError):
        return None

    name = str(facility.get("name") or "이름 없는 시설")
    distance_m = int(facility.get("distance_m") or 0)
    walking_minutes = int(
        facility.get("estimated_walking_minutes") or 1
    )

    if distance_m >= 1000:
        distance_label = f"{distance_m / 1000:.1f}km"
    else:
        distance_label = f"{distance_m}m"

    walking_label = f"예상 도보 {walking_minutes}분"

    return {
        "name": name,
        "category_label": style["label"],
        "icon": style["icon"],
        "icon_data": make_icon_data(style["icon"]),
        "color": style["color"],
        "latitude": latitude,
        "longitude": longitude,
        "distance_label": distance_label,
        "walking_label": walking_label,
        "map_label": (
            f"{name}\n"
            f"{distance_label} · 도보 {walking_minutes}분"
        ),
    }


def make_connection_lines(
    listing_point: dict[str, Any],
    facility_points: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """공고와 각 시설을 연결하는 선 데이터를 만듭니다."""

    source = [
        listing_point["longitude"],
        listing_point["latitude"],
    ]

    return [
        {
            "source": source,
            "target": [
                point["longitude"],
                point["latitude"],
            ],
            "color": point["color"],
        }
        for point in facility_points
    ]


def build_location_deck(
    title: str,
    latitude: float,
    longitude: float,
    stations: list[dict],
    marts: list[dict],
    hospitals: list[dict],
    radius_m: int,
) -> pdk.Deck:
    """공고·시설 아이콘과 연결선, 거리 문구를 포함한 PyDeck 지도를 만듭니다."""

    listing_point = make_listing_point(
        title=title,
        latitude=latitude,
        longitude=longitude,
    )

    facility_points = []

    for facility in stations + marts + hospitals:
        point = make_facility_point(facility)

        if point is not None:
            facility_points.append(point)

    all_points = [listing_point, *facility_points]

    connection_lines = make_connection_lines(
        listing_point=listing_point,
        facility_points=facility_points,
    )

    if radius_m <= 1000:
        zoom = 14
    elif radius_m <= 2000:
        zoom = 13
    else:
        zoom = 12

    layers = [
        pdk.Layer(
            "LineLayer",
            data=connection_lines,
            get_source_position="source",
            get_target_position="target",
            get_color="color",
            get_width=2,
            width_min_pixels=1,
        ),
        pdk.Layer(
            "IconLayer",
            data=all_points,
            get_position="[longitude, latitude]",
            get_icon="icon_data",
            get_size=40,
            size_scale=1,
            size_min_pixels=32,
            size_max_pixels=48,
            pickable=True,
        ),
        pdk.Layer(
            "TextLayer",
            data=all_points,
            get_position="[longitude, latitude]",
            get_text="map_label",
            get_size=14,
            get_color=[30, 30, 30],
            get_pixel_offset=[0, 25],
            get_text_anchor="'middle'",
            get_alignment_baseline="'top'",
            pickable=True,
        ),
    ]

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
            "html": (
                "<b>{icon} {name}</b><br/>"
                "{category_label}<br/>"
                "{distance_label}<br/>"
                "{walking_label}"
            ),
            "style": {
                "backgroundColor": "#263238",
                "color": "white",
            },
        },
    )
