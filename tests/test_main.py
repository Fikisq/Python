import unittest


from src.main import Agent, DataModel, run_line


class DataModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = DataModel()
        self.model.create_agent(key=1, timestamp=1000)

    def create_command(
        self,
        key: int = 10,
        timestamp: int = 1000,
        tags: str = "demo",
    ) -> None:
        self.model.create_command(
            key=key,
            timestamp=timestamp,
            argument="--help",
            agent=1,
            description="пример",
            tags=tags,
            processing=0,
        )

    def create_result(
        self,
        key: int = 100,
        command: int = 10,
        cache_hit: int = 1,
    ) -> None:
        self.model.create_result(
            key=key,
            timestamp=1000,
            output="готово",
            state="ok",
            failure="",
            command=command,
            cache_hit=cache_hit,
            duration=25,
        )

    def test_records_are_tuples(self) -> None:
        self.assertIsInstance(self.model.get_agents()[0], tuple)
        self.assertEqual(self.model.get_agents(), [Agent(1, 1000)])

    def test_agent_crud(self) -> None:
        updated = self.model.update_agent(1, timestamp=1001)
        self.assertEqual(updated.timestamp, 1001)
        self.assertEqual(self.model.delete_agent(1), updated)
        self.assertEqual(self.model.get_agents(), [])

    def test_duplicate_and_missing_keys(self) -> None:
        with self.assertRaises(ValueError):
            self.model.create_agent(key=1, timestamp=1000)
        with self.assertRaises(KeyError):
            self.model.delete_agent(999)
        with self.assertRaises((TypeError, ValueError)):
            self.model.update_agent(1, unknown=2)

    def test_command_crud_and_agent_relation(self) -> None:
        self.create_command()
        updated = self.model.update_command(10, processing=1)
        self.assertEqual(updated.processing, 1)
        with self.assertRaises(ValueError):
            self.model.delete_agent(1)
        with self.assertRaises(KeyError):
            self.model.update_command(10, agent=999)
        self.assertEqual(self.model.delete_command(10), updated)
        self.assertEqual(self.model.get_commands(), [])

    def test_foreign_keys_are_required_on_create(self) -> None:
        with self.assertRaises(KeyError):
            self.model.create_command(
                key=10,
                timestamp=1000,
                argument="--help",
                agent=999,
                description="пример",
                tags="demo",
                processing=0,
            )
        self.create_command()
        with self.assertRaises(KeyError):
            self.create_result(command=999)

    def test_result_crud_and_command_relation(self) -> None:
        self.create_command()
        self.create_result()
        updated = self.model.update_result(100, duration=30)
        self.assertEqual(updated.duration, 30)
        with self.assertRaises(ValueError):
            self.model.delete_command(10)
        with self.assertRaises(KeyError):
            self.model.update_result(100, command=999)
        self.assertEqual(self.model.delete_result(100), updated)
        self.assertEqual(self.model.get_results(), [])

    def test_recent_cache_uses_left_join_and_time_boundary(self) -> None:
        self.create_command(key=10, timestamp=640, tags="boundary")
        self.create_command(key=11, timestamp=639, tags="old")
        self.create_command(key=12, timestamp=900, tags="without-result")
        self.create_result(key=100, command=10, cache_hit=0)
        self.create_result(key=101, command=10, cache_hit=1)

        self.assertEqual(
            self.model.get_recent_cache(now=1000),
            [("boundary", 0), ("boundary", 1), ("without-result", None)],
        )

    def test_run_line(self) -> None:
        result = run_line(self.model, "get_agents")
        self.assertEqual(result, [Agent(1, 1000)])
        with self.assertRaises(ValueError):
            run_line(self.model, "unknown")
        with self.assertRaises(ValueError):
            run_line(self.model, "get_agents []")


if __name__ == "__main__":
    unittest.main()
