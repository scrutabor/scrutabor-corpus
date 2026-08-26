"""The reader edition: what the corpus looks like once nobody has to review it.

The authored corpus is written to be read by a philologist in a diff — one fact
to a line, every editorial claim visible, the text and its two gloss layers in
separate documents so each can be worked on alone. That is the right shape for
the work and the wrong shape for a phone.

This package derives the other shape: one compact neutral document per text and
one independently loadable artifact per target language. Repeated parse,
analysis and citation layers become indices into shared tables, while the
reviewer's apparatus stays behind. Root and language manifests are also package
boundaries for mobile downloads and offline archives.

What it leaves behind is named in DROP_DOC and is exactly four things: the
schema version, which the manifest names once, the mint, the editorial notes,
and the witness line ranges. Everything a reader is
SHOWN travels, including the analysis under the parse and every source note --
the first draft dropped both, and an edition that ships the doubt and withholds
the note of it is not the edition this corpus claims to be.

The saving is 39% of the bytes to parse and 412 parse objects on the heap where
the corpus has 6,143. It is NOT a saving in the bytes sent: the corpus repeats
one parse object at every word and gzip is very good at that, so compressed the
edition is a little larger than its source. The download is made small by not
shipping 1,961 prerendered pages, which is a different lever and lives in the
app.

Two things make it trustworthy rather than merely small:

- `verify()` reads every artifact back and compares it, word by word and gloss
  by gloss, against the authored documents it came from. A compression nobody
  checks is a corpus with a second, quieter edition in it.
- the build is deterministic. Run it twice and the bytes match, which is what
  lets CI diff a rebuild against what was committed.

Nothing here is authored and nothing here is committed. `build/` is generated.
"""
