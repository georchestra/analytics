# Presentation

## Component Architecture

Two scenarii will be considered:

- collecting usage data from the Security Proxy / Gateway access logs
- collecting usage data from file-based access logs data (e.g. reverse-proxy access logs)

### Scenario 1: Automated workflow
_Collecting usage data from the Security Proxy / Gateway access logs_

![workflow](../../d2/workflow_standard.svg)



### Scenario 2: Manual, file-based workflow
_Manually pushing access log files_

The Security Proxy/Gateway are the place where most of the information is available
(user information, http requests, response time and success) so this is the first
place to look at.

It is also possible to read access logs from a classic reverse proxy like Apache,
nginx etc. The only difference is that you won't get the user information (id, roles, org).

But you will also probably want to feed the database with historic access logs collected over time to preseed the database with as much information as possible.

![workflow](../../d2/workflow_manual.svg)
