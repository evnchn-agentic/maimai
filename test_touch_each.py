"""Button notes that share an each group with a touch note must not be dropped.

Run: python3 test_touch_each.py
"""
from simai_parser import parse_chart_string


def kinds(chart):
    return [(n.position, n.note_type) for n in parse_chart_string(chart, 120)]


def test_tap_after_touch():
    assert kinds('{4}B4/1,E') == [(1, 'tap')]


def test_slide_after_touch():
    notes = parse_chart_string('{4}E8/1-5[8:1],E', 120)
    assert [(n.position, n.note_type, n.slide_end) for n in notes] == [(1, 'slide', 5)]


def test_hold_after_touch_hold():
    assert kinds('{4}C1h[4:1]/6h[4:1],E') == [(6, 'hold')]


def test_several_touches_then_button():
    assert kinds('{4}B5/B6/E6f/2x,3,E') == [(2, 'tap'), (3, 'tap')]


def test_touch_alone_still_skipped():
    assert kinds('{4}B4,1,E') == [(1, 'tap')]


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
