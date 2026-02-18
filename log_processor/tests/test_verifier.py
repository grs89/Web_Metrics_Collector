import pytest
from verifier import BotVerifier

class TestBotVerifier:
    def test_genuine_googlebot(self):
        verifier = BotVerifier()
        # Case 1: Googlebot UA + crawl.googlebot.com hostname
        assert verifier.is_fake_googlebot(
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "crawl-66-249-66-1.googlebot.com"
        ) is False

        # Case 2: Googlebot UA + google.com hostname
        assert verifier.is_fake_googlebot(
            "Googlebot/2.1",
            "rate-limited-proxy-66-249-90-77.google.com"
        ) is False

    def test_fake_googlebot(self):
        verifier = BotVerifier()
        # Case 1: Googlebot UA + random hostname
        assert verifier.is_fake_googlebot(
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "bad-actor.example.com"
        ) is True

        # Case 2: Googlebot UA + no hostname
        assert verifier.is_fake_googlebot(
            "Googlebot/2.1",
            None
        ) is True

        # Case 3: Googlebot UA + misleading hostname
        assert verifier.is_fake_googlebot(
            "Googlebot/2.1",
            "googlebot.com.fake.com"
        ) is True

    def test_not_googlebot(self):
        verifier = BotVerifier()
        # Regular user agent should skip verification (return False as "not a fake bot" in this context)
        # The logic is: IF contains googlebot AND hostname mismatch -> True
        # So if not googlebot -> False
        assert verifier.is_fake_googlebot(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "1.2.3.4"
        ) is False
