from checks.transcription import check_transcriptions


def make_witness(tmp_path, body, raw_body="S. Joannis Baptistæ."):
    witness_dir = tmp_path / "witnesses" / "ordinarium.test"
    raw_dir = tmp_path / "witnesses" / "raw"
    witness_dir.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    (raw_dir / "do-ordo.txt").write_text(raw_body + "\n", encoding="utf-8")
    (witness_dir / "do.txt").write_text(
        "# path: web/Latin/Ordo.txt (line 1)\n" + body + "\n", encoding="utf-8"
    )
    return witness_dir


def test_exact_transcription_passes(tmp_path, monkeypatch):
    witness_dir = make_witness(tmp_path, "Joannis Baptistæ.")
    monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
    assert check_transcriptions(witness_dir) == ([], 1)


def test_accent_introduced_during_transcription_fails(tmp_path, monkeypatch):
    witness_dir = make_witness(tmp_path, "Joannis Baptístæ.")
    monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
    errors, checked = check_transcriptions(witness_dir)
    assert checked == 0
    assert len(errors) == 1
    assert "differs from its declared raw span" in errors[0]


def test_declared_but_unarchived_source_fails(tmp_path, monkeypatch):
    witness_dir = tmp_path / "witnesses" / "ordinarium.test"
    (tmp_path / "witnesses" / "raw").mkdir(parents=True)
    witness_dir.mkdir(parents=True)
    (witness_dir / "do.txt").write_text(
        "# path: web/Latin/Missing.txt (line 1)\nAmen.\n", encoding="utf-8"
    )
    monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
    errors, checked = check_transcriptions(witness_dir)
    assert checked == 0
    assert "no local archive" in errors[0]


def test_witness_without_a_raw_range_is_out_of_scope(tmp_path, monkeypatch):
    witness_dir = tmp_path / "witnesses" / "ordinarium.test"
    witness_dir.mkdir(parents=True)
    (witness_dir / "edition.txt").write_text("# source: print edition\nAmen.\n", encoding="utf-8")
    monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
    assert check_transcriptions(witness_dir) == ([], 0)


def test_a_declared_archive_with_no_line_range_is_refused(tmp_path, monkeypatch):
    # The census mutation (2026-08-19): delete `(lines 29-31)` and the run
    # stayed green, saying so only by dropping one from the verdict's `raw=`
    # count. A witness compared against nothing has not been verified.
    witness_dir = tmp_path / "witnesses" / "ordinarium.test"
    raw_dir = tmp_path / "witnesses" / "raw"
    witness_dir.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    (raw_dir / "do-ordo.txt").write_text("S. Joannis Baptistæ.\n", encoding="utf-8")
    (witness_dir / "do.txt").write_text(
        "# path: web/Latin/Ordo.txt\nJoannis Baptistæ.\n", encoding="utf-8"
    )
    monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
    errors, checked = check_transcriptions(witness_dir)
    assert checked == 0
    assert len(errors) == 1
    assert errors[0] == (
        "do.txt: names web/Latin/Ordo.txt and declares no readable line range — nothing "
        "was compared, and a range is what says which lines this transcription stands on"
    )


def test_an_unparseable_range_is_refused_like_a_missing_one(tmp_path, monkeypatch):
    witness_dir = make_witness(tmp_path, "Joannis Baptistæ.")
    (witness_dir / "do.txt").write_text(
        "# path: web/Latin/Ordo.txt (lines first-second)\nJoannis Baptistæ.\n", encoding="utf-8"
    )
    monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
    errors, checked = check_transcriptions(witness_dir)
    assert checked == 0 and "no readable line range" in errors[0]


def test_a_witness_transcribed_from_page_images_is_out_of_scope(tmp_path, monkeypatch):
    # Thirteen witnesses name printed pages and scan leaves. There is no local
    # archive to compare those against, which is not the same as unverified.
    witness_dir = tmp_path / "witnesses" / "ordinarium.test"
    (tmp_path / "witnesses" / "raw").mkdir(parents=True)
    witness_dir.mkdir(parents=True)
    (witness_dir / "mr.txt").write_text(
        "# path: printed page 302 (scan leaf n382), 600 dpi\nAmen.\n", encoding="utf-8"
    )
    monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
    assert check_transcriptions(witness_dir) == ([], 0)


def test_declared_paschal_alleluia_is_checked_against_actual_optional_words(tmp_path, monkeypatch):
    witness_dir = make_witness(
        tmp_path, "Ave, María. Allelúja, allelúja.", "Ave, María. (Allelúja, allelúja.) (rubric)"
    )
    witness = witness_dir / "do.txt"
    witness.write_text("# seasonal-alleluia: include\n" + witness.read_text(), encoding="utf-8")
    monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
    assert check_transcriptions(witness_dir) == ([], 1)
    witness.write_text(
        witness.read_text().replace("Allelúja, allelúja.", "Allelúia, allelúia."), encoding="utf-8"
    )
    assert check_transcriptions(witness_dir)[0]  # never normalize source j to i


def test_optional_alleluia_is_not_included_without_explicit_declaration(tmp_path, monkeypatch):
    witness_dir = make_witness(tmp_path, "Ave, María. Allelúja.", "Ave, María. (Allelúja.)")
    monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
    assert check_transcriptions(witness_dir)[0]


def test_malformed_seasonal_projection_is_rejected(tmp_path, monkeypatch):
    witness_dir = make_witness(tmp_path, "Joannis Baptistæ.")
    witness = witness_dir / "do.txt"
    witness.write_text("# seasonal-alleluia: guess\n" + witness.read_text(), encoding="utf-8")
    monkeypatch.setattr("checks.attribute.CORPUS", tmp_path)
    assert "seasonal-alleluia" in check_transcriptions(witness_dir)[0][0]
