"""HMAC evidence envelope for the isolated laboratory, not a production protocol."""
import hashlib
import hmac
import json
import math


def canonical(body):
    return json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sign(key, session, sequence, captured_s, payload, source='collector'):
    body = dict(session=session, source=source, sequence=sequence,
                captured_s=captured_s, payload=payload)
    return dict(body=body, tag=hmac.new(key, canonical(body), hashlib.sha256).hexdigest())


class Verifier:
    def __init__(self, key, session, max_age=0.06, source='collector'):
        self.key, self.session, self.max_age, self.source = key, session, max_age, source
        self.last_sequence = -1

    def verify(self, packet, now_s):
        if packet is None:
            return False, 'missing', None
        try:
            body, tag = packet['body'], packet['tag']
            expected = hmac.new(self.key, canonical(body), hashlib.sha256).hexdigest()
            if not isinstance(tag, str) or not hmac.compare_digest(tag, expected):
                return False, 'mac', None
            if body['session'] != self.session or body['source'] != self.source:
                return False, 'context', None
            seq, captured = body['sequence'], body['captured_s']
            if type(seq) is not int or seq < 0 or seq <= self.last_sequence:
                return False, 'replay', None
            if not math.isfinite(captured) or not math.isfinite(now_s) or not 0 <= now_s-captured <= self.max_age:
                return False, 'age', None
            p = body['payload']
            if not isinstance(p, dict) or type(p['service_ok']) is not bool or type(p['monitor_present']) is not bool:
                return False, 'schema', None
            if p['probe_blocked'] is not None and type(p['probe_blocked']) is not bool:
                return False, 'schema', None
            level = p['observed_level']
            if level is not None and (type(level) not in (int,float) or not math.isfinite(level)):
                return False, 'schema', None
            self.last_sequence = seq
            accepted = dict(p, age_s=now_s-captured)
            return True, 'accepted', accepted
        except (KeyError, TypeError, ValueError, OverflowError):
            return False, 'malformed', None
