import time
import unittest
from network_lab_stage3 import laboratory, request, run_trial, decide


class GatewayTests(unittest.TestCase):
    def test_actual_write_blocked_then_allowed_then_blocked(self):
        with laboratory() as (process, state, plc, hmi, it):
            self.assertEqual(request(hmi)[0], 200)
            self.assertEqual(request(it, 'POST', '/setpoint', {'value': 80})[0], 403)
            self.assertEqual(process.sample()['writes'], 0)
            state.configure(permissive=True)
            self.assertEqual(request(it, 'POST', '/setpoint', {'value': 80})[0], 200)
            self.assertEqual(process.sample()['writes'], 1)
            state.configure(permissive=False)
            self.assertEqual(request(it, 'POST', '/setpoint', {'value': 80})[0], 403)

    def test_ingress_cannot_write_via_hmi_listener(self):
        with laboratory() as (_, state, _, hmi, _):
            state.configure(permissive=True)
            self.assertEqual(request(hmi, 'POST', '/setpoint', {'value': 80})[0], 403)

    def test_outage_and_recovery(self):
        with laboratory() as (_, state, _, hmi, _):
            state.configure(outage=True)
            self.assertEqual(request(hmi)[0], 503)
            state.configure(outage=False)
            self.assertEqual(request(hmi)[0], 200)

    def test_replay_retains_original_timestamp(self):
        with laboratory() as (_, state, _, hmi, _):
            original = request(hmi)[1]
            state.configure(stale=True)
            time.sleep(0.01)
            replay = request(hmi)[1]
            self.assertEqual(original['measured_at'], replay['measured_at'])

    def test_backend_is_directly_accessible_on_loopback(self):
        # Explicitly document why this is not host/network isolation.
        with laboratory() as (_, _, plc, _, _):
            self.assertEqual(request(plc, 'POST', '/setpoint', {'value': 80})[0], 200)

    def test_persistent_fault_is_not_reported_as_recovery(self):
        _, results, _ = run_trial('persistent_outage', 0, steps=20, interval=0.001)
        self.assertTrue(all(r['declaration_missing'] for r in results))

    def test_missing_monitor_blocks_gate(self):
        obs=[dict(index=i, post_injection=True, service_ok=True, monitor_present=False,
                  probe_blocked=None, age_s=None, observed_level=None) for i in range(5)]
        self.assertIsNone(decide(obs,'gate'))
        self.assertEqual(decide(obs,'connectivity'),2)

    def test_dishonest_observations_are_not_authenticated(self):
        obs=[dict(index=i, post_injection=True, service_ok=True, monitor_present=True,
                  probe_blocked=True, age_s=0, observed_level=50) for i in range(5)]
        self.assertEqual(decide(obs,'gate'),2)


if __name__ == '__main__':
    unittest.main()
