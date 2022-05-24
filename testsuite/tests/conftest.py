"""Root conftest"""
import pytest
from weakget import weakget

from testsuite.config import settings
from testsuite.openshift.client import OpenShiftClient
from testsuite.rhsso import RHSSO, Realm, RHSSOServiceConfiguration
from testsuite.utils import randomize, _whoami


@pytest.fixture(scope="session")
def testconfig():
    """Testsuite settings"""
    return settings


@pytest.fixture(scope="session")
def openshift(testconfig):
    """Returns OpenShift client builder"""
    return OpenShiftClient(weakget(testconfig)["openshift"]["project"] % None)


@pytest.fixture(scope="session")
def rhsso_service_info(request, testconfig, blame):
    """
    Set up client for zync
    :return: dict with all important details
    """
    cnf = testconfig["rhsso"]
    assert cnf["password"] is not None, "SSO admin password neither discovered not set in config"
    rhsso = RHSSO(server_url=cnf["url"],
                  username=cnf["username"],
                  password=cnf["password"])
    realm: Realm = rhsso.create_realm(blame("realm"), accessTokenLifespan=24*60*60)

    if not testconfig["skip_cleanup"]:
        request.addfinalizer(realm.delete)

    client = realm.create_client(
        name=blame("client"),
        directAccessGrantsEnabled=True,
        publicClient=False,
        protocol="openid-connect",
        standardFlowEnabled=False)

    username = cnf["test_user"]["username"]
    password = cnf["test_user"]["password"]
    user = realm.create_user(username, password)

    return RHSSOServiceConfiguration(rhsso, realm, client, user, username, password)


@pytest.fixture(scope="session")
def blame(request):
    """Returns function that will add random identifier to the name"""
    def _blame(name: str, tail: int = 3) -> str:
        """Create 'scoped' name within given test

        This returns unique name for object(s) to avoid conflicts

        Args:
            :param name: Base name, e.g. 'svc'
            :param tail: length of random suffix"""

        nodename = request.node.name
        if nodename.startswith("test_"):  # is this always true?
            nodename = nodename[5:]

        context = nodename.lower().split("_")[0]
        if len(context) > 2:
            context = context[:2] + context[2:-1].translate(str.maketrans("", "", "aiyu")) + context[-1]

        if "." in context:
            context = context.split(".")[0]

        return randomize(f"{name[:8]}-{_whoami()[:8]}-{context[:9]}", tail=tail)
    return _blame
