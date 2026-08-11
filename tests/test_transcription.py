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
