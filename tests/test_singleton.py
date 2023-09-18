import pytest
from aircmd.models.singleton import Singleton

class SingletonChild(Singleton):
    def __init__(self):
        if not self._initialized[self.__class__]:
            self.value = "initialized"
            self._initialized[self.__class__] = True

def test_singleton_instance():
    instance1 = SingletonChild()
    instance2 = SingletonChild()
    assert instance1 is instance2

def test_singleton_unique_per_subclass():
    class AnotherSingletonChild(Singleton):
        pass

    instance1 = SingletonChild()
    instance2 = AnotherSingletonChild()
    assert instance1 is not instance2

def test_singleton_not_initialized():
    instance = SingletonChild()
    assert not instance._initialized[SingletonChild]

def test_singleton_initialized():
    instance = SingletonChild()
    instance.value  # This should initialize the instance
    assert instance._initialized[SingletonChild]

@pytest.mark.skip(reason="This test requires a dynamic plugin loading scenario")
def test_singleton_in_plugin_scenario():
    pass
