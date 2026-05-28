import pandas as pd

from epdm_sim.db import import_experiments_dataframe, init_database, insert_experiment, load_model_run, query_experiments, save_model_run


def test_sqlite_init_insert_query(tmp_path):
    db_path = tmp_path / "epdm.sqlite"
    conn = init_database(db_path)
    conn.close()
    insert_experiment({"run_id": "db-1", "temperature_C": 100, "ENB_wt": 6.8}, db_path)
    df = query_experiments(db_path)
    assert "db-1" in df["run_id"].tolist()


def test_import_dataframe_and_model_run_roundtrip(tmp_path):
    db_path = tmp_path / "epdm.sqlite"
    count = import_experiments_dataframe(pd.DataFrame([{"run_id": "a", "Mw": 300000}, {"run_id": "b", "Mw": 350000}]), db_path)
    assert count == 2
    save_model_run("run-a", "flowsheet", {"polymer_kg_h": 1.2}, "hash", db_path)
    payload = load_model_run("run-a", db_path)
    assert payload["polymer_kg_h"] == 1.2

