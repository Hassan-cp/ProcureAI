"""Offline regressions: python -m unittest discover -s backend -p test_regressions.py -v.

No database writes or external model calls. Live checks are separate.
"""
import copy
import os
import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from query_validator import validate_pipeline, parse_iso_date, ALLOWED_FIELDS
import query_executor as executor


def date(value):
    return {"$date": value}


YEAR_2020 = [{"$match": {"Purchase Date": {
    "$gte": date("2020-01-01T00:00:00Z"),
    "$lt": date("2021-01-01T00:00:00Z"),
}}}, {"$count": "count"}]


class ValidatorTests(unittest.TestCase):
    def test_date_comparisons_and_no_mutation(self):
        original = copy.deepcopy(YEAR_2020)
        safe = validate_pipeline(YEAR_2020)
        executor.convert_match_dates(safe[0]["$match"])
        self.assertIsInstance(safe[0]["$match"]["Purchase Date"]["$gte"], datetime)
        self.assertEqual(YEAR_2020, original)

    def test_date_equality_membership_and_nested_logic(self):
        for condition in [date("2020-01-01T00:00:00Z"),
                          {"$in": [date("2020-01-01T00:00:00Z"), None]},
                          {"$nin": [date("2020-01-01T00:00:00Z")]}]:
            with self.subTest(condition=condition):
                safe = validate_pipeline([{"$match": {"$or": [{"Purchase Date": condition}]}}])
                executor.convert_match_dates(safe[0]["$match"])
                self.assertNotIn("$date", str(safe))

    def test_iso_offsets(self):
        self.assertEqual(parse_iso_date("2020-01-01T03:00:00+03:00"),
                         datetime(2020, 1, 1, tzinfo=timezone.utc))

    def test_invalid_dates(self):
        for value in ["2020-01-01", "2020-02-30T00:00:00Z", "2020-01-01T00:00:00",
                      "2020-01-01T00:00:00+99:00", 123, {"$numberLong": "1"}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_pipeline([{"$match": {"Purchase Date": {"$gte": date(value)}}}])

    def test_unsafe_dates(self):
        for condition in [{"$date": "2020-01-01T00:00:00Z", "$where": "x"},
                          {"$gte": {"$date": "2020-01-01T00:00:00Z", "$ne": None}},
                          {"$in": [{"$where": "x"}]}]:
            with self.subTest(condition=condition), self.assertRaises(ValueError):
                validate_pipeline([{"$match": {"Purchase Date": condition}}])
        with self.assertRaises(ValueError):
            validate_pipeline([{"$match": {"Supplier Name": date("2020-01-01T00:00:00Z")}}])

    def test_blocked_operations(self):
        for stage in ["$out", "$merge", "$lookup", "$unionWith", "$facet"]:
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                validate_pipeline([{stage: "purchases"}])
        for condition in [{"$where": "true"}, {"Quantity": {"$expr": "x"}},
                          {"Supplier Name": {"$regex": "(a+)+"}},
                          {"Quantity": float("nan")}, {"Quantity": float("inf")}]:
            with self.subTest(condition=condition), self.assertRaises(ValueError):
                validate_pipeline([{"$match": condition}])
        for expression in [{"$function": {}}, "$$ROOT", "$unknown"]:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                validate_pipeline([{"$project": {"x": expression}}])

    def test_limits_and_stage_types(self):
        for pipeline in [[], [{}], [{"$limit": True}], [{"$limit": 101}],
                         [{"$sort": {"Quantity": True}}], [{"$limit": 1}] * 11]:
            with self.subTest(pipeline=pipeline), self.assertRaises(ValueError):
                validate_pipeline(pipeline)

    def test_group_year_and_projection_exclusion(self):
        validate_pipeline([{"$group": {"_id": {"$year": "$Purchase Date"}, "n": {"$sum": 1}}}])
        safe = validate_pipeline([{"$project": {"_id": 0}}, {"$sort": {"Total Price": -1}}])
        self.assertEqual(safe[-1], {"$limit": 100})


class LatestTests(unittest.TestCase):
    def test_latest_variants(self):
        variants = [
            [{"$sort": {"Purchase Date": -1}}, {"$limit": 1}],
            [{"$group": {"_id": None, "latest": {"$max": "$Purchase Date"}}}],
            [{"$group": {"_id": None, "year": {"$max": {"$year": "$Purchase Date"}}}}],
            [{"$project": {"year": {"$year": "$Purchase Date"}}}, {"$sort": {"year": -1}}],
            [{"$project": {"d": "$Purchase Date"}}, {"$group": {"_id": None, "v": {"$max": "$d"}}}],
            [{"$group": {"_id": {"$year": "$Purchase Date"}, "n": {"$sum": 1}}}, {"$sort": {"_id": -1}}],
            [{"$project": {"_id": 0}}, {"$sort": {"Purchase Date": -1}}],
        ]
        now = datetime(2026, 11, 13, tzinfo=timezone.utc)
        for pipeline in variants:
            with self.subTest(pipeline=pipeline):
                safe = validate_pipeline(pipeline)
                filtered = executor.filter_future_purchase_dates(safe, now)
                bounds = filtered[0]["$match"]["Purchase Date"]
                self.assertEqual(bounds["$type"], "date")
                self.assertEqual(bounds["$lte"], now)
                self.assertEqual(bounds["$gte"].year, 1900)
                self.assertEqual(filtered[1:], safe)

    def test_ordinary_queries_unchanged(self):
        for pipeline in [YEAR_2020, [{"$sort": {"Total Price": -1}}],
                         [{"$group": {"_id": None, "v": {"$max": "$Quantity"}}}],
                         [{"$group": {"_id": None, "Purchase Date": {"$sum": 1}}},
                          {"$sort": {"Purchase Date": -1}}]]:
            safe = validate_pipeline(pipeline)
            self.assertEqual(executor.filter_future_purchase_dates(safe), safe)


class ExecutorTests(unittest.TestCase):
    def test_aggregate_read_only_and_close(self):
        client, collection = Mock(), Mock()
        collection.aggregate.return_value = iter([{"count": 3}])
        with patch.object(executor, "get_collection", return_value=(client, collection)):
            self.assertEqual(executor.execute_query(YEAR_2020), [{"count": 3}])
        client.close.assert_called_once()
        self.assertFalse(collection.insert_one.called)
        self.assertEqual(collection.aggregate.call_args.kwargs["maxTimeMS"], 30000)
        self.assertFalse(collection.aggregate.call_args.kwargs["allowDiskUse"])

    def test_invalid_query_never_connects(self):
        with patch.object(executor, "get_collection") as connect:
            with self.assertRaises(ValueError):
                executor.execute_query([{"$out": "purchases"}])
            connect.assert_not_called()

    def test_close_on_database_failure(self):
        from pymongo.errors import OperationFailure
        client, collection = Mock(), Mock()
        collection.aggregate.side_effect = OperationFailure("private detail")
        with patch.object(executor, "get_collection", return_value=(client, collection)):
            with self.assertRaises(RuntimeError):
                executor.execute_query(YEAR_2020)
        client.close.assert_called_once()


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Prevent importing or calling the model; exercise actual FastAPI routes.
        cls.stub = types.ModuleType("procurement_agent")
        cls.stub.ask_procurement = Mock()
        cls.module_patch = patch.dict(sys.modules, {"procurement_agent": cls.stub})
        cls.module_patch.start()
        os.environ.setdefault("MONGO_READER_URI", "mongodb://127.0.0.1:27017")
        import main
        from fastapi.testclient import TestClient
        cls.main = main
        cls.api = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        cls.api.close()
        cls.main.client.close()
        cls.module_patch.stop()

    def test_request_validation(self):
        for payload in [{}, {"question": "   "}, {"question": "  a  "},
                        {"question": "x" * 501}, {"question": 123}]:
            self.assertEqual(self.api.post("/api/ask", json=payload).status_code, 422)

    def test_serialization(self):
        from bson import ObjectId
        oid = ObjectId()
        with patch.object(self.main, "ask_procurement", return_value={
            "question": "count purchases", "answer": "3", "results": [{"_id": oid, "date": datetime(2025, 1, 1)}]
        }) as ask:
            response = self.api.post("/api/ask", json={"question": " count purchases "})
        self.assertEqual(response.status_code, 200)
        ask.assert_called_once_with("count purchases")
        self.assertEqual(response.json()["results"][0]["_id"], str(oid))

    def test_failures_do_not_expose_details(self):
        for error, code in [(ValueError("secret"), 400), (RuntimeError("secret"), 503)]:
            with patch.object(self.main, "ask_procurement", side_effect=error):
                response = self.api.post("/api/ask", json={"question": "count purchases"})
                self.assertEqual(response.status_code, code)
                self.assertNotIn("secret", response.text)

    def test_stats_and_spending(self):
        collection = Mock()
        collection.count_documents.return_value = 346018
        collection.aggregate.return_value = [{"total_spending": 123.456}]
        with patch.object(self.main, "collection", collection):
            self.assertEqual(self.api.get("/api/stats").json(), {"total_purchases": 346018})
            self.assertEqual(self.api.get("/api/total-spending").json()["total_spending"], 123.46)
        from pymongo.errors import OperationFailure
        collection.count_documents.side_effect = OperationFailure("secret")
        with patch.object(self.main, "collection", collection):
            self.assertEqual(self.api.get("/api/stats").status_code, 503)


if __name__ == "__main__":
    unittest.main()
