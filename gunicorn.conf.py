"""Gunicorn settings, loaded automatically from the working directory.

The unchanged school entrypoint starts gunicorn without these options.
Measured with the default single sync worker, an admin video upload
blocked HLS segment requests for several seconds, and uploads longer
than 30 seconds would be killed by the worker timeout.
"""

worker_class = "gthread"
workers = 2
threads = 4
timeout = 300
keepalive = 5
