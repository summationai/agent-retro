"""render.py: deck text is HTML-escaped, and the deck is self-contained."""
import json, os, re, subprocess, sys, tempfile, unittest

import support

RENDER = os.path.join(support.SCRIPTS, 'render.py')
EVIL = '<script>alert(1)</script><img src=x onerror=alert(2)>'


class RenderTest(unittest.TestCase):
    def render(self, slides):
        with tempfile.TemporaryDirectory() as d:
            spec, out = os.path.join(d, 'slides.json'), os.path.join(d, 'deck.html')
            with open(spec, 'w') as f:
                json.dump(dict(title='Agent Retro, Sep 22–29', brand='Agent Retro', seed=7, slides=slides), f)
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
