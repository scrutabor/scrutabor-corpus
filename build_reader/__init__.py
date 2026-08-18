"""The reader edition: what the corpus looks like once nobody has to review it.

The authored corpus is written to be read by a philologist in a diff — one fact
to a line, every editorial claim visible, the text and its two gloss layers in
separate documents so each can be worked on alone. That is the right shape for
the work and the wrong shape for a phone.

This package derives the other shape. One document per text carrying both
languages, the parse replaced by an index into a table the whole corpus shares,
the editorial layer left behind, and a lexicon slice holding only the entries
that text's own words need. Measured over the whole corpus the result is 80%
smaller raw and 64% smaller gzipped, and it is the form the app is meant to
fetch rather than the form a reviewer is meant to read.

Two things make it trustworthy rather than merely small:

- `verify()` reads every artifact back and compares it, word by word and gloss
  by gloss, against the authored documents it came from. A compression nobody
  checks is a corpus with a second, quieter edition in it.
- the build is deterministic. Run it twice and the bytes match, which is what
  lets CI diff a rebuild against what was committed.

Nothing here is authored and nothing here is committed. `build/` is generated.
"""
