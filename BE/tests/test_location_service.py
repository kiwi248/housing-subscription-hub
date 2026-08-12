import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.services.location_service import (
    estimate_walking_minutes,
    find_nearby_living_facilities,
    find_nearby_subway_stations,
    geocode_address,
)


class WalkingTimeTest(unittest.TestCase):
    def test_직선거리를_예상_도보시간으로_변환한다(self):
        self.assertEqual(estimate_walking_minutes(300), 5)
        self.assertEqual(estimate_walking_minutes(420), 7)
        self.assertEqual(estimate_walking_minutes(800), 14)
        self.assertEqual(estimate_walking_minutes(1200), 20)

    def test_거리가_0이어도_최소_1분을_반환한다(self):
        self.assertEqual(estimate_walking_minutes(0), 1)


class GeocodeTest(unittest.TestCase):
    @patch("app.services.location_service.request_kakao")
    def test_주소_검색에_성공하면_키워드_검색을_하지_않는다(
        self,
        request_kakao,
    ):
        request_kakao.return_value = {
            "documents": [
                {
                    "address_name": "서울 중구 세종대로 110",
                    "road_address": {
                        "address_name": "서울 중구 세종대로 110",
                    },
                    "address": None,
                    "x": "126.977918351844",
                    "y": "37.566370776634",
                }
            ]
        }

        result = geocode_address(
            "서울특별시 중구 세종대로 110"
        )

        self.assertEqual(result.matched_by, "address")
        self.assertEqual(result.longitude, 126.977918351844)
        self.assertEqual(result.latitude, 37.566370776634)
        self.assertEqual(request_kakao.call_count, 1)

    @patch("app.services.location_service.request_kakao")
    def test_주소가_없으면_키워드로_다시_검색한다(
        self,
        request_kakao,
    ):
        request_kakao.side_effect = [
            {
                "documents": [],
            },
            {
                "documents": [
                    {
                        "place_name": "서울특별시청",
                        "road_address_name": (
                            "서울 중구 세종대로 110"
                        ),
                        "address_name": "서울 중구 태평로1가 31",
                        "x": "126.978652258823",
                        "y": "37.56682420267543",
                    }
                ],
            },
        ]

        result = geocode_address("서울시청")

        self.assertEqual(result.matched_by, "keyword")
        self.assertEqual(
            result.address,
            "서울 중구 세종대로 110",
        )
        self.assertEqual(request_kakao.call_count, 2)

    @patch("app.services.location_service.request_kakao")
    def test_주소와_장소를_모두_찾지_못하면_404이다(
        self,
        request_kakao,
    ):
        request_kakao.side_effect = [
            {"documents": []},
            {"documents": []},
        ]

        with self.assertRaises(HTTPException) as context:
            geocode_address("존재하지않는장소123456789")

        self.assertEqual(
            context.exception.status_code,
            404,
        )


class NearbySubwayTest(unittest.TestCase):
    @patch("app.services.location_service.request_kakao")
    def test_가까운_지하철역을_모델로_변환한다(
        self,
        request_kakao,
    ):
        request_kakao.return_value = {
            "documents": [
                {
                    "place_name": "시청역 1호선",
                    "road_address_name": (
                        "서울 중구 세종대로 지하 101"
                    ),
                    "address_name": "",
                    "x": "126.97719821079865",
                    "y": "37.56534539636417",
                    "distance": "130",
                },
                {
                    "place_name": "시청역 2호선",
                    "road_address_name": (
                        "서울 중구 서소문로 지하 127"
                    ),
                    "address_name": "",
                    "x": "126.97559827045151",
                    "y": "37.56368183746611",
                    "distance": "362",
                },
            ]
        }

        stations = find_nearby_subway_stations(
            latitude=37.566370776634,
            longitude=126.977918351844,
            radius_m=2000,
            limit=3,
        )

        self.assertEqual(len(stations), 2)
        self.assertEqual(stations[0].name, "시청역 1호선")
        self.assertEqual(stations[0].distance_m, 130)
        self.assertEqual(
            stations[0].estimated_walking_minutes,
            3,
        )

        request_params = request_kakao.call_args.kwargs[
            "params"
        ]
        self.assertEqual(
            request_params["category_group_code"],
            "SW8",
        )
        self.assertEqual(request_params["radius"], 2000)
        self.assertEqual(request_params["size"], 3)

    @patch("app.services.location_service.request_kakao")
    def test_주변에_역이_없으면_빈_목록이다(
        self,
        request_kakao,
    ):
        request_kakao.return_value = {
            "documents": [],
        }

        stations = find_nearby_subway_stations(
            latitude=37.5663,
            longitude=126.9779,
        )

        self.assertEqual(stations, [])



class NearbyLivingFacilitiesTest(unittest.TestCase):
    @patch("app.services.location_service.request_kakao")
    def test_지하철역_마트_병원을_함께_반환한다(
        self,
        request_kakao,
    ):
        request_kakao.side_effect = [
            {
                "documents": [
                    {
                        "place_name": "시청역 1호선",
                        "road_address_name": "서울 중구 세종대로",
                        "x": "126.9771",
                        "y": "37.5654",
                        "distance": "130",
                    }
                ],
            },
            {
                "documents": [
                    {
                        "place_name": "서울역 롯데마트",
                        "road_address_name": "서울 중구 한강대로",
                        "x": "126.9706",
                        "y": "37.5560",
                        "distance": "800",
                    }
                ],
            },
            {
                "documents": [
                    {
                        "place_name": "서울시립병원",
                        "road_address_name": "서울 중구 을지로",
                        "x": "126.9820",
                        "y": "37.5660",
                        "distance": "500",
                    }
                ],
            },
        ]

        facilities = find_nearby_living_facilities(
            latitude=37.5663,
            longitude=126.9779,
            radius_m=2000,
            limit=3,
        )

        self.assertEqual(
            facilities.subways[0].name,
            "시청역 1호선",
        )
        self.assertEqual(
            facilities.subways[0].category,
            "subway",
        )
        self.assertEqual(
            facilities.marts[0].name,
            "서울역 롯데마트",
        )
        self.assertEqual(
            facilities.marts[0].category,
            "mart",
        )
        self.assertEqual(
            facilities.hospitals[0].name,
            "서울시립병원",
        )
        self.assertEqual(
            facilities.hospitals[0].category,
            "hospital",
        )

        category_codes = [
            call.kwargs["params"]["category_group_code"]
            for call in request_kakao.call_args_list
        ]

        self.assertEqual(
            category_codes,
            ["SW8", "MT1", "HP8"],
        )


if __name__ == "__main__":
    unittest.main()