from shared.infrastructure.di import Factory, Singleton


class Repo:
    pass


class UseCase:
    def __init__(self, repo):
        self.repo = repo


def test_factory_resolves_dependencies():
    repo_provider = Factory(Repo)
    use_case_provider = Factory(UseCase, repo=repo_provider)
    uc = use_case_provider()
    assert isinstance(uc, UseCase)
    assert isinstance(uc.repo, Repo)


def test_factory_returns_new_instance_each_call():
    provider = Factory(Repo)
    assert provider() is not provider()


def test_singleton_returns_same_instance():
    provider = Singleton(Repo)
    assert provider() is provider()
