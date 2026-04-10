import time
from flask import Flask

import throttle


def test_rate_limit_decorator_memory_fallback():
    app = Flask(__name__)

    # Ensure a clean state
    throttle._reset_all()

    @throttle.rate_limit(limit=2, window=1, key_func=lambda: "unit-test-actor", prefix="utrl")
    def ping():
        return "pong"

    with app.test_request_context("/"):
        r1 = ping()
        assert r1 == "pong"
        r2 = ping()
        assert r2 == "pong"
        r3 = ping()
        # Exceeded: should return (response, 429)
        assert isinstance(r3, tuple) and r3[1] == 429

    # Wait for window to expire and try again
    time.sleep(1.1)
    with app.test_request_context("/"):
        r4 = ping()
        assert r4 == "pong"
