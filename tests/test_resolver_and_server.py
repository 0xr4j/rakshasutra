"""Server-side identity resolution (Algorithm 1) and the control room."""
from rakshasutra import simulate
from rakshasutra.edge import FPORT_ARRIVALS, FPORT_SOS
from rakshasutra.protocol import F_SOS, build_frame, rolling_id
from rakshasutra.resolver import DROP_FORGED_SOS, DROP_FRAME, OK, Registry, collision_probability
from rakshasutra.server import ControlRoom

KEY = bytes(range(16))


def registry():
    r = Registry()
    r.register("band-1", KEY, c_init=100, t_pair=0.0, family="f", role="band")
    return r


def test_expected_counter_follows_eq_6():
    r = registry()
    assert r.expected_counter("band-1", 0) == 100
    assert r.expected_counter("band-1", 899.9) == 100
    assert r.expected_counter("band-1", 900) == 101
    r.register("old", KEY, c_init=65535, t_pair=0.0)
    assert r.expected_counter("old", 900) == 0                 # wraps at 65536


def test_resolves_current_and_adjacent_slots_only():
    r = registry()
    t = 5 * 900 + 10                                           # slot 105
    for c, status in ((104, OK), (105, OK), (106, OK), (103, DROP_FRAME), (107, DROP_FRAME)):
        assert r.resolve(7, rolling_id(KEY, c), c, -60, 0, t).status == status, c
    assert r.table_size() == 3
    assert r.stale_or_unknown[7] == 2


def test_replay_from_an_old_slot_is_dropped():
    r = registry()
    old = build_frame(KEY, 100)
    assert r.resolve_frame(1, old, -60, 10).status == OK
    assert r.resolve_frame(9, old, -60, 3 * 900 + 10).status == DROP_FRAME


def test_unknown_pseudonym_and_garbage_are_dropped():
    r = registry()
    assert r.resolve(1, b"\xde\xad\xbe\xef", 100, -60, 0, 0).status == DROP_FRAME
    assert r.resolve_frame(1, bytes(15), -60, 0).status == DROP_FRAME


def test_forged_sos_is_dropped_and_counted():
    r = registry()
    good = build_frame(KEY, 100, flags=F_SOS)
    assert r.resolve_frame(3, good, -60, 5).sos
    forged = bytearray(build_frame(KEY, 100))
    forged[9] |= F_SOS                                         # flip the SOS bit without the key
    res = r.resolve_frame(3, bytes(forged), -60, 5)
    assert res.status == DROP_FORGED_SOS and r.forged_sos[3] == 1


def test_location_arbitration_prefers_the_strongest_pole():
    r = registry()
    rid = rolling_id(KEY, 100)
    assert r.resolve(10, rid, 100, -70, 0, 1.0).location == 10
    assert r.resolve(11, rid, 100, -55, 0, 2.0).location == 11
    assert r.resolve(12, rid, 100, -80, 0, 3.0).location == 11  # weaker report inside the 15 s window
    assert r.resolve(12, rid, 100, -80, 0, 30.0).location == 12  # the strong one has expired


def test_pseudonym_clash_between_two_tags_is_separated_by_counter():
    r = Registry()
    r.register("a", KEY, 100, 0.0)
    r.register("b", bytes(16), 200, 0.0)
    r.refresh(0.0)
    rid = rolling_id(KEY, 100)
    r._table[rid].append(("b", 200))                           # force a clash
    assert r.resolve(1, rid, 100, -60, 0, 0.0).uid == "a"
    assert r.resolve(1, rid, 200, -60, 0, 0.0).uid == "b"
    assert 0.05 < collision_probability(10000) < 0.2


def test_unregister_forgets_everything():
    r = registry()
    r.resolve(1, rolling_id(KEY, 100), 100, -60, 0, 0.0)
    r.unregister("band-1")
    assert r.table_size() == 0 and not r.location and not r.sightings
    assert r.resolve(1, rolling_id(KEY, 100), 100, -60, 0, 0.0).status == DROP_FRAME


def test_sos_bit_in_an_unsigned_arrival_tuple_raises_no_alarm():
    room = ControlRoom(registry())
    tup = rolling_id(KEY, 100) + (100).to_bytes(2, "little") + bytes([60, F_SOS])
    events = room.on_uplink(1.0, 20, FPORT_ARRIVALS, tup)
    assert [e.kind for e in events] == ["ARRIVED"]


def test_sos_uplink_raises_one_alarm_at_the_strongest_pole():
    room = ControlRoom(registry())
    sos = build_frame(KEY, 100, flags=F_SOS)
    room.on_uplink(1.0, 20, FPORT_SOS, sos + bytes([80]))
    room.on_uplink(1.1, 21, FPORT_SOS, sos + bytes([55]))
    room.on_uplink(1.2, 22, FPORT_SOS, sos + bytes([70]))
    alarms = [e for e in room.events if e.kind == "SOS"]
    assert len(alarms) == 1 and alarms[0].pole == 21


def test_family_walk_end_to_end():
    w = simulate.family_walk()
    room, kinds = w["room"], [e.kind for e in w["room"].events]
    assert "SEPARATION" in kinds and kinds.count("SOS") == 1
    sep = next(e for e in room.events if e.kind == "SEPARATION")
    sos = next(e for e in room.events if e.kind == "SOS")
    assert w["split_s"] < sep.time < w["split_s"] + 240        # flagged within four minutes of the split
    assert 0 <= sos.time - w["sos_s"] < 1.0                    # alarm within a second on this path
    child = room.trek.pole(room.registry.location["band-0421"][0])
    parent = room.trek.pole(room.registry.location["tag-0421"][0])
    assert child.segment == "sanjichhat" and parent.segment == "himkoti"
    assert not room.registry.forged_sos and not room.registry.stale_or_unknown
    assert len(room.wakes) == 2 and all(len(tok) == 8 for *_x, tok in room.wakes)
