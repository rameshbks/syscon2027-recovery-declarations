import contextlib
import copy
import io
import tempfile
import unittest
from evidence import sign, Verifier
from stage4_campaign import run_trial, evaluate, main, SCENARIOS, PRIMARY, STRATEGIES

KEY=b'a'*32


def payload():
    return dict(service_ok=True,monitor_present=True,probe_blocked=True,
                age_s=0.0,observed_level=50.0)


class AuthenticationTests(unittest.TestCase):
    def test_valid_packet(self):
        self.assertTrue(Verifier(KEY,'s').verify(sign(KEY,'s',0,1,payload()),1.01)[0])

    def test_payload_tampering(self):
        packet=sign(KEY,'s',0,1,payload())
        packet['body']['payload']['observed_level']=80
        self.assertEqual(Verifier(KEY,'s').verify(packet,1.01)[1],'mac')

    def test_wrong_key(self):
        self.assertFalse(Verifier(b'b'*32,'s').verify(sign(KEY,'s',0,1,payload()),1.01)[0])

    def test_tag_tampering(self):
        packet=sign(KEY,'s',0,1,payload())
        packet['tag']='0'*64
        self.assertFalse(Verifier(KEY,'s').verify(packet,1.01)[0])

    def test_duplicate_replay(self):
        v=Verifier(KEY,'s')
        packet=sign(KEY,'s',0,1,payload())
        self.assertTrue(v.verify(packet,1.01)[0])
        self.assertEqual(v.verify(packet,1.02)[1],'replay')

    def test_out_of_order(self):
        v=Verifier(KEY,'s')
        self.assertTrue(v.verify(sign(KEY,'s',5,1,payload()),1.01)[0])
        self.assertEqual(v.verify(sign(KEY,'s',4,1,payload()),1.01)[1],'replay')

    def test_cross_session(self):
        self.assertEqual(Verifier(KEY,'other').verify(sign(KEY,'s',0,1,payload()),1.01)[1],'context')

    def test_source_binding(self):
        self.assertEqual(Verifier(KEY,'s').verify(sign(KEY,'s',0,1,payload(),source='other'),1.01)[1],'context')

    def test_stale_but_authentic(self):
        self.assertEqual(Verifier(KEY,'s').verify(sign(KEY,'s',0,1,payload()),1.2)[1],'age')

    def test_future_timestamp(self):
        self.assertEqual(Verifier(KEY,'s').verify(sign(KEY,'s',0,2,payload()),1)[1],'age')

    def test_missing_packet(self):
        self.assertEqual(Verifier(KEY,'s').verify(None,1)[1],'missing')

    def test_bad_mac_does_not_consume_sequence(self):
        v=Verifier(KEY,'s')
        bad=sign(KEY,'s',900,1,payload())
        bad['tag']='bad'
        self.assertFalse(v.verify(bad,1.01)[0])
        self.assertTrue(v.verify(sign(KEY,'s',0,1,payload()),1.01)[0])

    def test_signed_malformed_payload(self):
        p=payload()
        p['service_ok']='True'
        self.assertEqual(Verifier(KEY,'s').verify(sign(KEY,'s',0,1,p),1.01)[1],'schema')

    def test_compromised_signer_is_not_detected_by_mac(self):
        # A fresh false measurement from a key holder is cryptographically valid.
        self.assertTrue(Verifier(KEY,'s').verify(sign(KEY,'s',0,1,payload()),1.01)[0])


class CampaignTests(unittest.TestCase):
    def test_design(self):
        self.assertEqual((len(SCENARIOS),len(PRIMARY),len(STRATEGIES)),(14,4,6))

    def test_tampered_evidence_control(self):
        trace, records, _, checks, _, _=run_trial('misleading_evidence',0,interval=0)
        self.assertTrue(any(c['reason']=='mac' for c in checks))
        r={r['strategy']:r for r in records}
        self.assertTrue(r['gate_v2']['unsafe_declaration'])
        self.assertFalse(r['gate_v3']['unsafe_declaration'])
        self.assertGreater(r['gate_v3']['declaration_step'],r['gate_v2']['declaration_step'])

    def test_compromised_source_negative_control(self):
        trace, records, _, checks, _, _=run_trial('source_compromise',0,interval=0)
        r={r['strategy']:r for r in records}
        self.assertTrue(r['gate_v3']['unsafe_declaration'])
        self.assertTrue(r['gate_v3']['invalid_evidence_declaration'])

    def test_replay_is_rejected(self):
        _,records,_,checks,_,_=run_trial('replay_evidence',1,interval=0)
        self.assertTrue(any(c['reason']=='replay' for c in checks))
        self.assertFalse(next(r for r in records if r['strategy']=='gate_v3')['unsafe_declaration'])

    def test_missing_signed_evidence(self):
        _,records,_,checks,_,_=run_trial('missing_signed',0,interval=0)
        self.assertTrue(any(c['reason']=='missing' for c in checks))

    def test_persistent_outage_censored(self):
        _,records,_,_,_,_=run_trial('persistent_outage',0,interval=0)
        self.assertTrue(all(r['declaration_missing'] for r in records))
        self.assertTrue(all(r['unsafe_declaration'] is None for r in records))

    def test_longer_window_delays_normal_declaration(self):
        _,records,_,_,_,_=run_trial('normal',0,interval=0)
        r={r['strategy']:r for r in records}
        self.assertEqual(r['gate_v3']['declaration_step']-r['auth_only']['declaration_step'],5)

    def test_oracle_truth_not_used_by_verifier(self):
        trace,records,_,_,key,session=run_trial('normal',0,interval=0)
        for row in trace:
            row['ground_truth']['controller_target']=80
        altered,_=evaluate(trace,bytes.fromhex(key),session)
        before={r['strategy']:r['declaration_step'] for r in records}
        self.assertEqual(before,{r['strategy']:r['declaration_step'] for r in altered})
        self.assertTrue(all(r['unsafe_declaration'] for r in altered))

    def test_non_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                main(['--out',folder])

    def test_freshness_derived_from_signed_timestamp(self):
        p=payload()
        p['age_s']=0
        self.assertFalse(Verifier(KEY,'s').verify(sign(KEY,'s',0,1,p),2)[0])


if __name__=='__main__':
    unittest.main()
