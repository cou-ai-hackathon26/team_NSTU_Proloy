from app.core.privacy import scrub_pii

def test_scrub_ip_addresses():
    raw = "User connected from IP 192.168.1.105 with request"
    scrubbed = scrub_pii(raw)
    assert "192.168.1.105" not in scrubbed
    assert "[IP_REDACTED]" in scrubbed

def test_scrub_emails():
    raw = "Contact patient at fatima123@gmail.com for follow up"
    scrubbed = scrub_pii(raw)
    assert "fatima123@gmail.com" not in scrubbed
    assert "[EMAIL_REDACTED]" in scrubbed

def test_scrub_bangladesh_phone_numbers():
    raw_en = "Emergency contact: 01712345678 call urgently"
    scrubbed_en = scrub_pii(raw_en)
    assert "01712345678" not in scrubbed_en
    assert "[PHONE_REDACTED]" in scrubbed_en

    raw_bn = "রোগীর ফোন নম্বর: ০১৭১২৩৪৫৬৭৮"
    scrubbed_bn = scrub_pii(raw_bn)
    assert "০১৭১২৩৪৫৬৭৮" not in scrubbed_bn
    assert "[PHONE_REDACTED]" in scrubbed_bn
