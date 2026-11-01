# Security Policy

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Use [GitHub's private vulnerability reporting](https://github.com/psxdata/psxdata/security/advisories/new) to report a vulnerability confidentially.

Include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

You will receive a response within 7 days. If the vulnerability is confirmed, a fix will be released as quickly as possible and credited to the reporter (unless you prefer to remain anonymous).

## Scope

This project scrapes publicly available data from the Pakistan Stock Exchange. It does not handle user authentication, store credentials, or process payments. The primary security concern is supply-chain integrity (dependency vulnerabilities) and safe handling of user-supplied inputs to the REST API.
