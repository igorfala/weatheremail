Newsletter app with script to send automatic weather personalized emails to subscribers
======================================================================================

Setup (Linux)
--------------------
- ``cd weatheremail``
- populate ``weatheremail/weatheremail/conf/weatheremail.conf``
- ``./devenv.sh`` to enter virtual environment
- ``make run <HOST=host> <PORT=port>`` to run the server locally (default: 0.0.0.0:8081)
- access subscription form at ``http://localhost:8081/subscribe``

Run script to populate ``subscription_city`` table
---------------------------------------------------
- ``make populate_cities <VERBOSITY={0,1}>`` default VERBOSITY == 1

Run script to send emails
--------------------------
- ``make send_emails <VERBOSITY={0,1}> <NEWSLETTER=newsletter> <API_LIMIT=limit>``
    default VERBOSITY == 1 NEWSLETTER == WD API_LIMIT == 10 (per minute for wunderground)
