import copy
import unittest

import savn_iteration2 as study
import savn_priority_based_selection as baseline
import savn_priority_sa as annealing


def check(name, start, duration=14, earliest=0, latest=100):
    return {
        "check": name,
        "start": start,
        "duration": duration,
        "earliest_start": earliest,
        "latest_start": latest,
    }


class DisplacementLimitTests(unittest.TestCase):
    def test_a_check_moved_past_the_limit_is_a_breach(self):
        as_loaded = {"Aircraft 1": [check("A", 100)]}
        schedule = {"Aircraft 1": [check("A", 90)]}

        breaches = study.operational_breaches(
            schedule,
            {"displacement_limit_days": 5},
            as_loaded,
            horizon=200,
        )

        self.assertEqual(
            ["Aircraft 1 check 1 moved 10 days from its as-loaded start"],
            breaches,
        )

    def test_a_move_inside_the_limit_is_legal(self):
        as_loaded = {"Aircraft 1": [check("A", 100)]}
        schedule = {"Aircraft 1": [check("A", 90)]}

        breaches = study.operational_breaches(
            schedule,
            {"displacement_limit_days": 20},
            as_loaded,
            horizon=200,
        )

        self.assertEqual([], breaches)


class BusyPeriodTests(unittest.TestCase):
    def test_a_window_below_its_required_availability_is_a_breach(self):
        schedule = {
            "Aircraft 1": [check("A", 0, duration=14)],
            "Aircraft 2": [check("A", 100, duration=14)],
        }

        breaches = study.operational_breaches(
            schedule,
            {
                "busy_periods": [{
                    "start_day": 0,
                    "end_day": 13,
                    "minimum_availability": 2,
                }],
            },
            as_loaded=schedule,
            horizon=200,
        )

        self.assertEqual(
            ["busy period days 0-13 worst-day availability 1 is below 2"],
            breaches,
        )


class DependencyGroupTests(unittest.TestCase):
    def test_a_group_that_drops_below_its_minimum_is_a_breach(self):
        schedule = {
            "Aircraft 1": [check("A", 0, duration=14)],
            "Aircraft 2": [check("A", 100, duration=14)],
            "Aircraft 3": [check("A", 100, duration=14)],
        }

        breaches = study.operational_breaches(
            schedule,
            {
                "dependency_groups": [{
                    "aircraft": ["Aircraft 1", "Aircraft 2"],
                    "minimum_available": 2,
                }],
            },
            as_loaded=schedule,
            horizon=200,
        )

        self.assertEqual(
            ["dependency group Aircraft 1, Aircraft 2 falls to 1 available"],
            breaches,
        )


class NeighborLimitTests(unittest.TestCase):
    def test_a_neighbor_past_the_displacement_limit_is_not_legal(self):
        as_loaded = {
            "Aircraft 1": [check("A", 100, earliest=50, latest=100)],
        }
        schedule = copy.deepcopy(as_loaded)
        neighbor = {
            "aircraft": "Aircraft 1",
            "events": [check("A", 80, earliest=50, latest=100)],
        }

        legal = study.neighbor_is_legal(
            schedule,
            neighbor,
            {"displacement_limit_days": 5},
            as_loaded,
            horizon=200,
        )

        self.assertFalse(legal)

    def test_feasible_neighbors_drop_moves_past_the_displacement_limit(self):
        events = [
            check("A", 100, duration=14, earliest=58, latest=100),
            check("B", 430, duration=28, earliest=395, latest=465),
        ]
        rebuilt = baseline.rebuild_aircraft_schedule(events, horizon=2900)
        schedule = {"Aircraft 1": rebuilt}
        availability = baseline.compute_availability(schedule, 2900)
        as_loaded = copy.deepcopy(schedule)

        open_neighbors = annealing.generate_feasible_neighbors(
            schedule,
            availability,
            2900,
            shifts=(-10,),
        )
        limited = annealing.generate_feasible_neighbors(
            schedule,
            availability,
            2900,
            shifts=(-10,),
            scenario={"displacement_limit_days": 0},
            as_loaded=as_loaded,
        )

        self.assertTrue(open_neighbors)
        self.assertEqual([], limited)


class TunedNeighbourhoodTests(unittest.TestCase):
    def setUp(self):
        events = [
            check("A", 100, duration=14, earliest=58, latest=100),
            check("B", 430, duration=28, earliest=395, latest=465),
        ]
        rebuilt = baseline.rebuild_aircraft_schedule(events, horizon=2900)
        self.horizon = 2900
        self.schedule = {"Aircraft 1": rebuilt}
        self.availability = baseline.compute_availability(
            self.schedule,
            self.horizon,
        )

    def test_vns_neighbors_use_only_the_supplied_shifts(self):
        neighbors = annealing.generate_vns_neighbors(
            self.schedule,
            self.availability,
            self.horizon,
            shift_sets=((-10,),),
        )

        self.assertTrue(neighbors)
        self.assertTrue(all(item["shift"] == -10 for item in neighbors))

    def test_polish_with_no_shifts_leaves_the_start_schedule(self):
        polished, _, _ = annealing.greedy_polish(
            self.schedule,
            horizon=self.horizon,
            max_iters=3,
            shift_sets=(),
        )

        self.assertEqual(
            self.schedule["Aircraft 1"][0]["start"],
            polished["Aircraft 1"][0]["start"],
        )


def rebuilt_aircraft(first_start):
    events = [
        check(
            "A",
            first_start,
            duration=14,
            earliest=first_start - 42,
            latest=first_start,
        ),
        check(
            "B",
            first_start + 365,
            duration=28,
            earliest=first_start + 365 - 70,
            latest=first_start + 365,
        ),
    ]
    return baseline.rebuild_aircraft_schedule(events, horizon=2900)


class StartScheduleTests(unittest.TestCase):
    def setUp(self):
        self.horizon = 2900
        self.schedule = {
            "Aircraft 1": rebuilt_aircraft(100),
            "Aircraft 2": rebuilt_aircraft(80),
        }

    def test_bunched_start_moves_the_first_movable_check_toward_the_median(self):
        bunched = study.build_start_schedule(
            self.schedule,
            "bunched",
            self.horizon,
        )

        self.assertEqual(100, bunched["Aircraft 1"][0]["start"])
        self.assertEqual(455, bunched["Aircraft 1"][1]["start"])
        self.assertEqual(445, bunched["Aircraft 2"][1]["start"])
        self.assertEqual("A", bunched["Aircraft 1"][0]["check"])
        self.assertEqual("B", bunched["Aircraft 1"][1]["check"])
        self.assertEqual(465, bunched["Aircraft 1"][1]["latest_start"])
        self.assertEqual(445, bunched["Aircraft 2"][1]["latest_start"])

    def test_spread_start_moves_the_first_movable_check_away_from_the_median(self):
        spread = study.build_start_schedule(
            self.schedule,
            "spread",
            self.horizon,
        )

        self.assertEqual(395, spread["Aircraft 1"][1]["start"])
        self.assertEqual(375, spread["Aircraft 2"][1]["start"])
        self.assertEqual(465, spread["Aircraft 1"][1]["latest_start"])

    def test_as_loaded_start_keeps_the_loaded_dates(self):
        as_loaded = study.build_start_schedule(
            self.schedule,
            "as-loaded",
            self.horizon,
        )

        self.assertEqual(100, as_loaded["Aircraft 1"][0]["start"])
        self.assertEqual(80, as_loaded["Aircraft 2"][0]["start"])
        as_loaded["Aircraft 1"][0]["start"] = 0
        self.assertEqual(100, self.schedule["Aircraft 1"][0]["start"])


class ScenarioFileTests(unittest.TestCase):
    def test_loose_and_medium_accept_the_loaded_schedule_and_tight_does_not(self):
        schedule, base_date = baseline.load_heavy_schedule(
            baseline.FILE_PATH,
            baseline.SHEET_NAME,
        )
        horizon = baseline.get_forecast_horizon(schedule)
        scenarios = study.load_scenarios(
            "operational_constraints.json",
            base_date,
        )

        self.assertEqual(
            [70, 42, 21],
            [item["displacement_limit_days"] for item in scenarios],
        )

        for scenario in scenarios:
            breaches = study.operational_breaches(
                schedule,
                scenario,
                schedule,
                horizon,
            )

            if scenario["name"] == "tight":
                self.assertTrue(breaches)
            else:
                self.assertEqual([], breaches)


class DecisionTests(unittest.TestCase):
    def test_keeps_the_candidate_when_the_median_clears_every_bar(self):
        decision = study.judge_candidate(
            tuned={"smoothness": 1.40, "worst_day": 18},
            runs=[
                {"smoothness": 1.390, "worst_day": 18, "seconds": 100},
                {"smoothness": 1.392, "worst_day": 18, "seconds": 120},
                {"smoothness": 1.394, "worst_day": 18, "seconds": 110},
            ],
        )

        self.assertTrue(decision["keep"])
        self.assertEqual(1.392, decision["median_smoothness"])
        self.assertEqual(0.004, round(decision["spread"], 3))

    def test_drops_the_candidate_when_the_smoothness_gain_is_too_small(self):
        decision = study.judge_candidate(
            tuned={"smoothness": 1.40, "worst_day": 18},
            runs=[
                {"smoothness": 1.397, "worst_day": 18, "seconds": 100},
                {"smoothness": 1.396, "worst_day": 18, "seconds": 100},
                {"smoothness": 1.398, "worst_day": 18, "seconds": 100},
            ],
        )

        self.assertFalse(decision["keep"])

    def test_drops_the_candidate_when_a_seed_loses_the_worst_day(self):
        decision = study.judge_candidate(
            tuned={"smoothness": 1.40, "worst_day": 18},
            runs=[
                {"smoothness": 1.30, "worst_day": 18, "seconds": 100},
                {"smoothness": 1.30, "worst_day": 17, "seconds": 100},
                {"smoothness": 1.30, "worst_day": 18, "seconds": 100},
            ],
        )

        self.assertFalse(decision["keep"])

    def test_drops_the_candidate_when_the_typical_run_exceeds_five_minutes(self):
        decision = study.judge_candidate(
            tuned={"smoothness": 1.40, "worst_day": 18},
            runs=[
                {"smoothness": 1.30, "worst_day": 18, "seconds": 100},
                {"smoothness": 1.30, "worst_day": 18, "seconds": 400},
                {"smoothness": 1.30, "worst_day": 18, "seconds": 500},
            ],
        )

        self.assertFalse(decision["keep"])


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now


class ScreeningTests(unittest.TestCase):
    def test_screening_stops_when_the_hour_is_spent(self):
        clock = Clock()

        def run_trial(variant):
            clock.now += 1000
            return {
                "name": variant["name"],
                "smoothness": 1.4,
                "worst_day": 18,
                "seconds": 1000,
                "seed": variant["seed"],
            }

        results = study.run_screening(
            run_trial,
            time_limit_seconds=2500,
            clock=clock,
        )

        self.assertEqual(3, len(results))
        self.assertTrue(all(item["seed"] == 99 for item in results))

    def test_a_second_seed_follows_the_smoothest_variant_when_time_remains(self):
        clock = Clock()

        def run_trial(variant):
            clock.now += 1
            smoothness = 1.0 if "escape_cycles_8" in variant["name"] else 1.2
            return {
                "name": variant["name"],
                "smoothness": smoothness,
                "worst_day": 18,
                "seconds": 1,
                "seed": variant["seed"],
            }

        results = study.run_screening(
            run_trial,
            time_limit_seconds=3600,
            clock=clock,
        )

        self.assertEqual(9, len(results))
        self.assertEqual(1, results[-1]["seed"])
        self.assertIn("escape_cycles_8", results[-1]["name"])

    def test_second_seed_keeps_the_winning_setting_when_the_trial_renames_itself(self):
        clock = Clock()
        seen = []

        def run_trial(variant):
            clock.now += 1
            seen.append(dict(variant))
            smoothness = 1.0 if variant.get("escape_temperature") == 1.0 else 1.2
            return {
                "name": f"{variant['name']}-seed-{variant['seed']}",
                "variant": variant["name"],
                "smoothness": smoothness,
                "worst_day": 18,
                "seconds": 1,
                "seed": variant["seed"],
            }

        study.run_screening(
            run_trial,
            time_limit_seconds=3600,
            clock=clock,
        )

        self.assertEqual(1.0, seen[-1]["escape_temperature"])
        self.assertEqual(1, seen[-1]["seed"])
