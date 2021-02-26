# acdn-sshelper

This is a simple script I use at work to easily connect to our VM instances on [Google Cloud](https://cloud.google.com/).

We use a particular setup that involves bouncing servers and short-lived SSH certificates issued by [Vault](https://www.vaultproject.io/).
This script has probably no interest, except for poor souls coerced to use this setup!

For this to work, you'll need

* The `gcloud` command, with an active login.
* The `vault` command, with an active login.

Please refer to our internal docs to install these commands and log in.

When run, the script generates two files:

* A proper SSH configuration file, with host entries for each instance.
* A signed SSH certificate, required to connect from bounce servers to target ones.

## Installation

You may install this project with

```console
$ python3 -m pip install git+https://github.com/vivienm/acdn-sshelper.git
```

## Walkthrough

Behavior may be customized with environment variables.
See `acdn-sshelper --help` for a comprehensive list.

```console
$ cat ~/.bashrc
...
export ACDN_SSHELPER_IDENTITY_FILE=~/.ssh/id_rsa_acdn
export ACDN_SSHELPER_SSH_CONFIG=~/.ssh/config_acdn
```

The generated config file may be included into the default one.

```console
$ cat ~/.ssh/config
...
Include ~/.ssh/config_acdn
```

Generate SSH configuration file and client certificate.
You may want to run it periodically.

```console
$ acdn-sshelper
[INFO] Created signed certificate '/run/user/1000/acdn-sshelper/id_rsa.cert'
[INFO] Found GCS account 'me@example.com'
[INFO] Found GCS projects ['dev', 'prod']
[INFO] Created SSH config file '/home/me/.ssh/config_acdn'
```

You should now be able to connect using plain ol' SSH!

```console
$ ssh foo-leader.dev.gcs
```
