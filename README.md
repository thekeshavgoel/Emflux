# Emflux
Python based email processing for storing in InfluxDB

InfluxDB is widely used for time-series data storage and has several agents that help in Infrastructure monitoring by collecting metrics from various soruces. But there is no agent that collects alerts being generated in the form of Email.

This is a Python processor for reading emails form a Microsoft Outlook email account and insert them into InfluxDB.

## Pre-requisites
1. Microsoft Graph App with required scope (read/write/send)
2. Microsoft Outlook email account that gets all email alerts.
3. InfluxDB up and running.

**Note:** The application can also intelligently process alerts into generating priority alerts based on the provided Alerts configuration.

Further enhancements:
1) Abstract-out & generalise the email based code
2) Include more Email apps - Gmail etc.
3) Include more target DBs like InfluxDB.
