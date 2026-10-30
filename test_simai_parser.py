"""Slide-parsing checks; every token below is copied from a real maidata.txt.
Run: python3 test_simai_parser.py"""
from simai_parser import parse_chart_string


def slides(token, bpm=120):
    return [n for n in parse_chart_string(f'({bpm}){{4}}{token},E', bpm) if n.note_type == 'slide']


def test_v_slide_ends_at_last_vertex():
    s, = slides('2V41[16:5]')
    assert (s.position, s.slide_shape, s.slide_end) == (2, 'V', 1)
    assert s.slide_duration_ms == 625.0


def test_explicit_delay_and_duration():
    s, = slides('6-1[0.219##0.1429]')
    assert round(s.slide_delay_ms, 1) == 219.0
    assert round(s.slide_duration_ms, 1) == 142.9


def test_chain_ends_at_last_vertex_and_sums_durations():
    s, = slides('5-2-7[2:1]')
    assert (s.slide_end, s.slide_duration_ms) == (7, 1000.0)
    s, = slides('1-3[4:1]-5[4:1]')
    assert (s.slide_end, s.slide_duration_ms) == (5, 1000.0)


def test_break_marker_after_endpoint():
    s, = slides('6-1b[4:1]')
    assert s.slide_duration_ms == 500.0


def test_tapless_slide_is_a_slide():
    s, = slides('8?-5[2:1]')
    assert s.headless and s.slide_end == 5


def test_sibling_slides_share_one_star():
    a, b = slides('3b-1[8:1]*-7[8:1]')
    assert (a.slide_end, a.headless) == (1, False)
    assert (b.position, b.slide_end, b.headless) == (3, 7, True)


def test_plain_tokens_unchanged():
    notes = parse_chart_string('(120){4}1,2b,3h[4:1],4-8[4:1],E', 120)
    assert [n.note_type for n in notes] == ['tap', 'break', 'hold', 'slide']
    assert notes[2].hold_duration_ms == 500.0
    assert (notes[3].slide_end, notes[3].slide_delay_ms, notes[3].slide_duration_ms) == (8, 500.0, 500.0)


if __name__ == '__main__':
    tests = [f for k, f in sorted(globals().items()) if k.startswith('test_')]
    failed = 0
    for t in tests:
        try:
            t()
            print('PASS', t.__name__)
        except Exception as e:
            failed += 1
            print('FAIL', t.__name__, type(e).__name__, e)
    print(f'{len(tests) - failed}/{len(tests)} passed')
    raise SystemExit(failed > 0)
