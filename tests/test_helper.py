from pmc.catch import helper


class A:
    pass


def test_is_class():

    assert helper.class_or_instancemethod.is_class(1) is False
    assert helper.class_or_instancemethod.is_class(A) is True


def test_is_instance():
    assert helper.class_or_instancemethod.is_instance(1) is True
    assert helper.class_or_instancemethod.is_instance(A) is False
