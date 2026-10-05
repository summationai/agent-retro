"""render.py: deck text is HTML-escaped, and the deck is self-contained."""
import json, os, random, re, subprocess, sys, tempfile, unittest

import support

RENDER = os.path.join(support.SCRIPTS, 'render.py')
renderer = support.load(RENDER, 'test_renderer')
EVIL = '<script>alert(1)</script><img src=x onerror=alert(2)>'


class RenderTest(unittest.TestCase):
    def render(self, slides):
        with tempfile.TemporaryDirectory() as d:
            spec, out = os.path.join(d, 'slides.json'), os.path.join(d, 'deck.html')
            with open(spec, 'w') as f:
                json.dump(dict(title='Agent Retro, Sep 22–29', profile='custom', brand='Agent Retro', seed=7, slides=slides), f)
            subprocess.run([sys.executable, RENDER, spec, out], check=True, capture_output=True)
            with open(out) as f:
                return f.read()

    def test_text_is_escaped(self):
        html = self.render([
            dict(type='cold', big=EVIL, headline=EVIL, lede=EVIL, eyebrow=EVIL),
            dict(type='quote', headline='q', quote=EVIL, tally=[dict(value=1, label=EVIL)]),
            dict(type='coach', kind='tweak', confidence='early signal', headline=EVIL, why=EVIL, **{'try': EVIL},
                 stat=dict(type='quote', quote=EVIL)),
            dict(type='outro', title=EVIL, eyebrow='e', facts=[dict(label=EVIL, value=EVIL)] * 6, tries=[EVIL] * 3, footer=EVIL),
        ])
        self.assertNotIn('<script>alert', html)
        self.assertNotIn('<img src=x', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)

    def test_chart_attributes_reject_injection_and_invalid_numbers(self):
        for pct in [EVIL, '50', -1, 101, float('nan'), float('inf'), True]:
            with self.subTest(pct=pct), self.assertRaises(ValueError):
                renderer.compare_rows([dict(label='x', pct=pct)])
        for color in [EVIL, 'red; background:url(https://example.org)', 'var(--unknown)']:
            with self.subTest(color=color), self.assertRaises(ValueError):
                renderer.seg_bar([dict(label='x', value=1, color=color)], '')
        for value in [-1, float('nan'), float('inf'), '1']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                renderer.seg_bar([dict(label='x', value=value)], '')
        with self.assertRaises(ValueError):
            renderer.render_slide(dict(type='heatmap', days=[], cells={}, hours=[EVIL]), random.Random(1))

    def test_supported_colors_and_zero_segments(self):
        html = renderer.seg_bar([dict(label='x', value=0, color='#abc'),
                                 dict(label='y', value=10, color='var(--fg)')], 'test')
        self.assertIn('width:0.00%', html)
        self.assertIn('width:100.00%', html)

    def test_every_component_renders(self):
        from deck_fixtures import components
        slides = components()
        slides += [dict(slides[9], stat=dict(type='compare', rows=[dict(label='Sample', pct=50)])),
                   dict(slides[9], stat=dict(type='number', value=2, label='Moments'))]
        html = self.render(slides)
        self.assertEqual(len(re.findall(r'<section\b', html)), len(slides))
        self.assertIn('<!doctype html>', html)

    def test_brand_and_slide_count(self):
        html = self.render([dict(type='cold', big=str(i), headline='h') for i in range(12)])
        self.assertIn('Agent Retro', html)
        self.assertEqual(len(re.findall(r'<section\b', html)), 12)

    def test_no_external_requests_except_fonts(self):
        # the deck may be published; it must not phone home with anything but a font stylesheet
        html = self.render([dict(type='cold', big='1', headline='h')])
        hosts = set(re.findall(r'(?:src|href)=["\']https?://([^/"\']+)', html))
        self.assertTrue(hosts <= {'fonts.googleapis.com', 'fonts.gstatic.com'}, hosts)


if __name__ == '__main__':
    unittest.main()
