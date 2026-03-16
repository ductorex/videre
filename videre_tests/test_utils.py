from videre.core.utils import OnClick, Procedure


def test_onclick_with_procedure():
    called = []
    on_click = OnClick(lambda: called.append(True))
    on_click()
    assert called == [True]


def test_onclick_none():
    on_click = OnClick(None)
    on_click()  # should not raise


def test_onclick_default():
    on_click = OnClick()
    on_click()  # should not raise


def test_procedure():
    result = []
    proc = Procedure(lambda a, b: result.append(a + b), 3, 7)
    proc()
    assert result == [10]


def test_procedure_ignores_call_args():
    result = []
    proc = Procedure(lambda x: result.append(x), 42)
    proc("ignored", key="also_ignored")
    assert result == [42]


def test_procedure_with_kwargs():
    result = []
    proc = Procedure(lambda a, key=None: result.append((a, key)), 1, key="hello")
    proc()
    assert result == [(1, "hello")]
