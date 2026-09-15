# Vicky 8.2

Vicky 8.2 is based on the `v8.1` branch and incorporates the setup fixes identified during the MOON migration on 2026-09-01.

## Fixed: Mosquitto reachable only on localhost

AWTRIX is an external LAN device and therefore cannot use `127.0.0.1` as its broker address. Mosquitto must accept connections on the LAN interface.

Required broker configuration:

```text
listener 1883 0.0.0.0
allow_anonymous false
password_file /etc/mosquitto/passwd
```

The password file must remain protected but readable by the `mosquitto` service account:

```bash
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo chmod 640 /etc/mosquitto/passwd
sudo systemctl restart mosquitto
```

Verification:

```bash
sudo ss -ltnp | grep 1883
```

Expected result includes:

```text
0.0.0.0:1883
```

On the current MOON reference installation the LAN address is `192.168.1.70`, so the AWTRIX MQTT broker is:

```text
Broker: 192.168.1.70
Port:   1883
```

Vicky processes running locally on MOON may continue to use `127.0.0.1:1883`.

## Fixed: Mosquitto exit status 13 after restart

V8.1 created `/etc/mosquitto/passwd` with mode `0600`. When owned by root this can prevent the Mosquitto service user from reading the file and cause startup failure with exit status 13.

V8.2 standardizes the file to:

```text
owner: root
group: mosquitto
mode: 0640
```

## Fixed: stale Cerbo/GX SSH host key

After a Cerbo/GX reinstall or SSH host-key change, Victron refresh may fail with:

```text
Host key verification failed.
```

Repair procedure:

```bash
ssh-keygen -R 192.168.1.63
ssh-keyscan -H 192.168.1.63 >> ~/.ssh/known_hosts
```

## Required: passwordless Cerbo/GX SSH key

The Victron service runs non-interactively with `BatchMode=yes`. A normal SSH login that asks for the Cerbo root password is therefore **not sufficient**. The MOON public key must be installed once on the Cerbo/GX.

Install it with:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@192.168.1.63
```

The Cerbo root password is requested once during this step.

Then verify the exact non-interactive login used by Vicky:

```bash
ssh -o BatchMode=yes -i ~/.ssh/id_ed25519 root@192.168.1.63 'echo OK'
```

The expected result is immediately:

```text
OK
```

There must be **no password prompt**. If a password is requested, `awtrix_victron.py` and the systemd service will fail even though an interactive SSH login works.

V8.2 includes `upgrade-vicky8.2.sh`, which performs the Mosquitto repair, refreshes the configured Cerbo/GX host key and checks whether passwordless SSH is available. If the key is not yet authorized on the Cerbo, the script prints the required `ssh-copy-id` and `BatchMode=yes` test commands.

## Upgrade existing V8.1 installation

From the repository on MOON:

```bash
git fetch origin
git checkout v8.2
git pull --ff-only origin v8.2
bash upgrade-vicky8.2.sh
```

Use `bash upgrade-vicky8.2.sh` so the upgrade also works if the executable bit has not yet been set on a local checkout.

If an automatic MQTT publish test is desired, provide the password only for the command invocation rather than storing it in Git:

```bash
VICKY_MQTT_USER=mqtt_user VICKY_MQTT_PASS='your-password' bash upgrade-vicky8.2.sh
```

Do not commit MQTT passwords or other local credentials to the repository.
