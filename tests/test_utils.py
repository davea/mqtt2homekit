from mqtt2homekit.utils import display_name


def test_display_name():
    assert display_name('FooBar') == 'Foo Bar'
