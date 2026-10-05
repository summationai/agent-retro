"""Optional Chromium execution tests: RETRO_BROWSER_TESTS=1 python -m unittest discover -s tests."""
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

import support
import render
from deck_fixtures import components, default_deck
from io_utils import write_json


@unittest.skipUnless(os.environ.get('RETRO_BROWSER_TESTS') == '1', 'set RETRO_BROWSER_TESTS=1 to run Chromium tests')
class BrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.page = self.browser.new_page(reduced_motion='reduce', viewport=dict(width=1280,height=800))
        self.page.set_default_timeout(5000)
        self.errors = []
        self.page.on('pageerror', lambda error:self.errors.append(str(error)))
        # Test offline fallbacks and prevent font requests from leaving the browser.
        self.page.route('https://**/*', lambda route:route.abort())

    def tearDown(self):
        self.page.close()
        self.tmp.cleanup()

    def load(self, spec):
        src,out = Path(self.tmp.name)/'slides.json',Path(self.tmp.name)/'deck.html'
        write_json(src,spec)
        with contextlib.redirect_stdout(io.StringIO()):
            render.main(src,out)
        self.page.goto(out.as_uri())

    def activate(self, index):
        self.page.locator('section').nth(index).evaluate('(s) => s.scrollIntoView()')
        self.page.wait_for_function('(i) => document.querySelectorAll("section")[i].classList.contains("in")',arg=index)

    def test_all_components_execute_offline_and_navigation_works(self):
        self.load(dict(title='All components',profile='custom',slides=components()))
        self.page.keyboard.press('ArrowDown')
        self.page.wait_for_function('document.querySelectorAll("section")[1].classList.contains("in")')
        for i in range(len(components())):
            self.activate(i)
        self.assertEqual(self.errors,[])
        self.assertEqual(self.page.locator('html').get_attribute('lang'),'en')

    def test_mobile_footnotes_are_visible_without_horizontal_page_overflow(self):
        self.page.set_viewport_size(dict(width=375,height=667))
        self.load(default_deck())
        self.activate(1)
        footnote=self.page.locator('section').nth(1).locator('.small')
        self.assertTrue(footnote.is_visible())
        self.assertNotEqual(footnote.evaluate('(e) => getComputedStyle(e).display'),'none')
        for i in range(12):
            self.activate(i)
            self.assertTrue(self.page.evaluate('document.querySelector("main").scrollWidth <= innerWidth + 1'))
        self.assertEqual(self.errors,[])

    def test_space_activates_focused_checkboxes_and_copy_buttons(self):
        self.load(default_deck())
        self.activate(3)
        copy=self.page.locator('section').nth(3).get_by_role('button',name='Copy')
        copy.focus(); self.page.keyboard.press('Space')
        self.page.wait_for_function('Array.from(document.querySelectorAll(".tryb button")).some(b => ["Copied","Selected"].includes(b.textContent))')
        self.activate(11)
        button=self.page.locator('.checks button').first
        button.focus(); self.page.keyboard.press('Space')
        self.assertEqual(button.get_attribute('aria-pressed'),'true')
        self.assertEqual(self.errors,[])

    def test_count_animation_preserves_suffix(self):
        self.page.emulate_media(reduced_motion='no-preference')
        self.load(dict(title='Animation',profile='custom',slides=[components()[5]]))
        self.page.wait_for_function('document.querySelector("[data-count]").textContent === "12"')
        self.assertEqual(self.page.locator('.tally b').inner_text(),'12×')
        self.assertEqual(self.errors,[])

    def test_reduced_motion_disables_animations(self):
        self.load(default_deck())
        self.assertEqual(self.page.locator('.hint b').evaluate('(e) => getComputedStyle(e).animationName'),'none')
        self.activate(1)
        self.assertEqual(self.page.locator('section').nth(1).locator('[data-count]').inner_text(),'1,200')
