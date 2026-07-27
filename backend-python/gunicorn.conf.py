import os
worker_class = 'gthread'
threads = 100
workers = 1
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
