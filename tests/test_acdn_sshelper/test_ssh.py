from acdn_sshelper import gcloud
from acdn_sshelper.ssh import jumphost_user


def test_jumphost_user():
    account = gcloud.Account("j.doe@example.com")
    assert jumphost_user(account) == "j_doe_example_com"
