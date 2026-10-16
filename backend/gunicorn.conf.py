import os

bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = 4
timeout = 60
accesslog = "-"
errorlog = "-"
