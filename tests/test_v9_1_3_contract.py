import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_version_is_9_1_3():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "9.1.3"


def test_committed_site_profiles_have_only_site_specific_cerbo_placeholders():
    davanod = (ROOT / "sites/davanod-moon.conf.example").read_text(encoding="utf-8")
    montpellier = (ROOT / "sites/montpellier-orin.conf.example").read_text(encoding="utf-8")

    assert "VICKY_CERBO_HOST=REPLACE_WITH_DAVANOD_CERBO_HOST" in davanod
    assert "VICKY_CERBO_USER=REPLACE_WITH_DAVANOD_CERBO_USER" in davanod
    assert "VICKY_CERBO_SSH_KEY=REPLACE_WITH_DAVANOD_PRIVATE_KEY_PATH" in davanod
    assert "VICKY_CERBO_HOST=REPLACE_WITH_MONTPELLIER_CERBO_HOST" in montpellier
    assert "VICKY_CERBO_USER=REPLACE_WITH_MONTPELLIER_CERBO_USER" in montpellier
    assert "VICKY_CERBO_SSH_KEY=REPLACE_WITH_MONTPELLIER_PRIVATE_KEY_PATH" in montpellier
    assert "192.168.1.63" not in davanod + montpellier


def test_configurator_persists_local_cerbo_values_in_both_generated_files(tmp_path):
    checkout = tmp_path / "checkout"
    (checkout / "scripts").mkdir(parents=True)
    (checkout / "sites").mkdir()
    shutil.copy2(ROOT / "scripts/configure-site.sh", checkout / "scripts/configure-site.sh")
    shutil.copy2(ROOT / "sites/davanod-moon.conf.example", checkout / "sites")
    key = tmp_path / "vicky-cerbo-key"
    key.write_text("test-only-private-key", encoding="utf-8")

    answers = "\n".join(
        [
            "awtrix_test",
            "",
            "mqtt_user",
            "mqtt_password",
            "cerbo.davanod.test",
            "cerbo_user",
            str(key),
        ]
    ) + "\n"
    subprocess.run(
        ["bash", str(checkout / "scripts/configure-site.sh"), "davanod"],
        input=answers,
        text=True,
        check=True,
    )

    generated_config = (checkout / "config.py").read_text(encoding="utf-8")
    generated_environment = (checkout / ".vicky-site").read_text(encoding="utf-8")
    for expected in ["cerbo.davanod.test", "cerbo_user", str(key)]:
        assert expected in generated_config
        assert expected in generated_environment
    assert (checkout / "config.py").stat().st_mode & 0o777 == 0o600
    assert (checkout / ".vicky-site").stat().st_mode & 0o777 == 0o600


def test_victron_unit_loads_local_environment_and_runtime_has_no_fixed_fallbacks():
    installer = (ROOT / "scripts/install-vicky9-services.sh").read_text(encoding="utf-8")
    client = (ROOT / "victron/awtrix_victron.py").read_text(encoding="utf-8")

    assert 'EnvironmentFile=$environment_file' in installer
    assert '"$REPO_ROOT/.vicky-site"' in installer
    assert 'required_setting("VICKY_CERBO_HOST")' in client
    assert 'required_setting("VICKY_CERBO_USER")' in client
    assert 'required_setting("VICKY_CERBO_SSH_KEY")' in client
    assert "192.168.1.63" not in client
    assert "/home/gerd/.ssh/id_ed25519" not in client
    assert "shell=True" not in client
