# Security policy

Rakshasutra is a design for a system that would follow children and vulnerable adults. Weaknesses in it matter more
than in most research code, and reports are very welcome.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Report it privately through GitHub:
**Security → Report a vulnerability** on this repository. You will get a reply within seven days, and a fix or a clear
answer as soon as the problem is understood. Credit is given in the release notes unless you ask otherwise.

## Scope

| Part | Examples of what counts |
|---|---|
| The protocol (`protocol.py`, `resolver.py`, the book, WP-01) | a way to link a wristband across slots, forge an SOS or a wake token, recover a key, or make the server misplace a wearer beyond the limits already documented |
| Python package and command line (`src/rakshasutra`) | a crafted log or registry file that crashes the reader, runs code or reads files it should not |
| Firmware (`firmware/`) | memory errors in the C core, input that drives the edge filter into a wrong state, a way to exhaust a pole |
| Website and explorer (`docs/`, `demo/`) | script injection, unsafe links, anything that runs code a visitor did not expect |
| Repository and CI (`.github/`) | workflow permissions, untrusted input reaching a workflow |

## Known limits, already documented

These are stated in the README, the book and the audit, and do not need a private report. Ideas for closing them are
welcome as ordinary issues.

- Arrival reports are not authenticated, so a sighting can be replayed inside its three-slot window.
- A wristband can be followed within one 15-minute slot; the counter and battery byte are sent in clear.
- Whoever holds the master key and the pairing table can follow every wristband.
- The AES in this repository is a reference for checking bytes. It is not constant-time.

## Keys in this repository

Every key here is a public demonstration key (`000102...0f` and keys derived from it). They protect nothing. Never
use them on a device, and never commit a real key.

## Not a security issue

Rakshasutra is a design study. A calculated range or battery life that turns out wrong in the field is a limitation
of the model, documented under *Limits* in the README, not a vulnerability. Please report it as an ordinary issue.

## Supported versions

Only the latest release on the `main` branch receives fixes.
