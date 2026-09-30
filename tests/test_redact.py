import unittest

import support  # noqa: F401  (puts the plugin scripts on sys.path)
from redact import REDACTIONS, _luhn, scrub_secrets
from support import BENIGN, SECRETS


class RedactTest(unittest.TestCase):
    def test_every_secret_kind_is_removed(self):
        for kind, text, fragment in SECRETS:
            with self.subTest(kind):
                out = scrub_secrets(text)
                self.assertNotIn(fragment, out)
                self.assertNotEqual(out, text)

    def test_secrets_are_removed_inside_longer_prompts(self):
        for kind, text, fragment in SECRETS:
            with self.subTest(kind):
                out = scrub_secrets(f'Before we start: {text}\nthen deploy it. Thanks!')
                self.assertNotIn(fragment, out)
                if kind == 'private key, cut off':  # no END line: everything after BEGIN goes, by design
                    self.assertEqual(out, 'Before we start: [redacted:private-key]')
                else:
                    self.assertIn('then deploy it. Thanks!', out)

    def test_ordinary_text_is_untouched(self):
        for text in BENIGN:
            with self.subTest(text=text):
                self.assertEqual(scrub_secrets(text), text)

    def test_markers_name_what_was_removed(self):
        self.assertIn('[email]', scrub_secrets('mail a.b@example.org'))
        self.assertIn('[phone]', scrub_secrets('call 415-555-0134'))
        self.assertEqual(scrub_secrets('see /home/someone/app'), 'see ~/app')

    def test_redaction_is_idempotent(self):
        for kind, text, _ in SECRETS:
            with self.subTest(kind):
                once = scrub_secrets(text)
                self.assertEqual(scrub_secrets(once), once)

    def test_counts_each_kind(self):
        REDACTIONS.clear()
        scrub_secrets('a.b@example.org and c.d@example.org, call 415-555-0134')
        self.assertEqual(REDACTIONS['email'], 2)
        self.assertEqual(REDACTIONS['phone'], 1)

    def test_card_numbers_need_a_valid_checksum(self):
        self.assertTrue(_luhn('4111111111111111'))
        self.assertFalse(_luhn('4111111111111112'))
        self.assertEqual(scrub_secrets('ref 4111 1111 1111 1112'), 'ref 4111 1111 1111 1112')

    def test_non_text_passes_through(self):
        for value in (None, '', 42):
            self.assertEqual(scrub_secrets(value), value)


if __name__ == '__main__':
    unittest.main()
