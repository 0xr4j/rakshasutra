# Contributing to Rakshasutra

Thank you for helping. Three kinds of contribution help most:

1. **Measurements.** Roof loss and range under a steel shelter, Bluetooth scanning in a crowd, coin cells in the cold.
   Use the [offer a measurement or field access](https://github.com/0xr4j/rakshasutra/issues/new?template=offer-data.yml)
   form. Full credit is given in every result that uses your data.
2. **Problem reports.** A bug, a wrong number, a flaw in the protocol, or an unclear sentence. Use the problem form.
   For a weakness that could put a wearer at risk, use [SECURITY.md](SECURITY.md) instead.
3. **Code.** Fork, branch, and open a pull request against `main`.

## Before you open a pull request

```bash
pip install -r requirements.txt && pip install --no-deps -e .
make test          # all tests must pass; they also compile the firmware core and run the browser kernel under Node
```

- Keep each pull request to one change, and add or update a test for it.
- Every number shown in the book, the white paper, the README or the website is written from result files by script.
  Change the script or the model, then run `make results generated site`. Do not edit a number, `README.md`,
  `AUDIT.md` or anything in `docs/*.html` by hand; edit the template.
- If a change moves a pinned headline number, update the pinned test in the same commit and say why.
- Label calculated results as calculated and simulated results as simulated. Nothing is "measured" unless the raw
  data are in `data/`.
- New parameters go in `src/rakshasutra/params.py` with a status and a source.
- Follow the [rules fixed in advance](ROADMAP.md#rules-fixed-in-advance).

## Data and privacy

Never commit personal data about a real person: no names, phone numbers, card numbers or location trails. Keys in
this repository are public demonstration keys and are marked as such; never commit a real one.

## Licence

By contributing you agree that your contribution is released under the [MIT licence](LICENSE).
