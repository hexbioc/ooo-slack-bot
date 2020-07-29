import os
import multiprocessing

workers = multiprocessing.cpu_count() + 1
loglevel = "debug"
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
