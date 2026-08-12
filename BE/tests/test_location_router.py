import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.exceptions.handlers import register_exception_handlers
from app.routers.location_router import location_router
from app.schemas.location_schema import (
    GeocodeResult,
    NearbyFacilities,
    NearbyFacility,
    NearbyStation,
)


test_app = FastAPI()
register_exception_handlers(test_app)
test_app.include_router(location_router)

client = TestClient(test_app)


class GeocodeRouterTest(unittest.TestCase):
    @patch(
        "app.routers.location_router.geocode_address"
    )
    def test_주소_검색_결과를_반환한다(
        self,
        geocode_address,
    ):
        geocode_address.return_value = GeocodeResult(
            address="서울 중구 세종대로 110",
            latitude=37.566370776634,
            longitude=126.977918351844,
            matched_by="address",
        )

        response = client.get(
            "/locations/geocode",
            params={
                "address": "서울특별시 중구 세종대로 110",
            },
        )

        self.assertEqual(response.status_code, 200)

        body = response.json()

        self.assertTrue(body["success"])
        self.assertEqual(
            body["data"]["matched_by"],
            "address",
        )
        self.assertEqual(
            body["data"]["longitude"],
            126.977918351844,
        )

        geocode_address.assert_called_once_with(
            "서울특별시 중구 세종대로 110"
        )

    def test_주소가_너무_짧으면_422이다(self):
        response = client.get(
            "/locations/geocode",
            params={
                "address": "서",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["success"])

    def test_주소가_없으면_422이다(self):
        response = client.get(
            "/locations/geocode",
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["success"])


class NearbySubwayRouterTest(unittest.TestCase):
    @patch(
        "app.routers.location_router."
        "find_nearby_subway_stations"
    )
    def test_주변_지하철역을_반환한다(
        self,
        find_nearby_subway_stations,
    ):
        find_nearby_subway_stations.return_value = [
            NearbyStation(
                name="시청역 1호선",
                address="서울 중구 세종대로 지하 101",
                latitude=37.56534539636417,
                longitude=126.97719821079865,
                distance_m=130,
                estimated_walking_minutes=3,
            )
        ]

        response = client.get(
            "/locations/nearby-subways",
            params={
                "latitude": 37.566370776634,
                "longitude": 126.977918351844,
                "radius_m": 2000,
                "limit": 3,
            },
        )

        self.assertEqual(response.status_code, 200)

        body = response.json()

        self.assertTrue(body["success"])
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(
            body["data"][0]["name"],
            "시청역 1호선",
        )
        self.assertEqual(
            body["data"][0][
                "estimated_walking_minutes"
            ],
            3,
        )

        find_nearby_subway_stations.assert_called_once_with(
            latitude=37.566370776634,
            longitude=126.977918351844,
            radius_m=2000,
            limit=3,
        )

    def test_위도_범위를_벗어나면_422이다(self):
        response = client.get(
            "/locations/nearby-subways",
            params={
                "latitude": 91,
                "longitude": 126.9779,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["success"])

    def test_검색반경이_너무_작으면_422이다(self):
        response = client.get(
            "/locations/nearby-subways",
            params={
                "latitude": 37.5663,
                "longitude": 126.9779,
                "radius_m": 50,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["success"])

    def test_필수좌표가_없으면_422이다(self):
        response = client.get(
            "/locations/nearby-subways",
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["success"])


class NearbyFacilitiesRouterTest(unittest.TestCase):
    @patch(
        "app.routers.location_router.find_nearby_living_facilities"
    )
    def test_주변_생활권_시설을_반환한다(
        self,
        find_nearby_living_facilities,
    ):
        find_nearby_living_facilities.return_value = NearbyFacilities(
            subways=[
                NearbyFacility(
                    category="subway",
                    name="시청역 1호선",
                    address="서울 중구 세종대로",
                    latitude=37.5654,
                    longitude=126.9771,
                    distance_m=130,
                    estimated_walking_minutes=3,
                )
            ],
            marts=[
                NearbyFacility(
                    category="mart",
                    name="서울역 롯데마트",
                    address="서울 중구 한강대로",
                    latitude=37.5560,
                    longitude=126.9706,
                    distance_m=800,
                    estimated_walking_minutes=14,
                )
            ],
            hospitals=[
                NearbyFacility(
                    category="hospital",
                    name="서울시립병원",
                    address="서울 중구 을지로",
                    latitude=37.5660,
                    longitude=126.9820,
                    distance_m=500,
                    estimated_walking_minutes=9,
                )
            ],
        )

        response = client.get(
            "/locations/nearby-facilities",
            params={
                "latitude": 37.5663,
                "longitude": 126.9779,
                "radius_m": 2000,
                "limit": 3,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(
            data["subways"][0]["name"],
            "시청역 1호선",
        )
        self.assertEqual(
            data["marts"][0]["category"],
            "mart",
        )
        self.assertEqual(
            data["hospitals"][0]["category"],
            "hospital",
        )

        find_nearby_living_facilities.assert_called_once_with(
            latitude=37.5663,
            longitude=126.9779,
            radius_m=2000,
            limit=3,
        )


if __name__ == "__main__":
    unittest.main()
