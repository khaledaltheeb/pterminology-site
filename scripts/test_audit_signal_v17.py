from html.parser import HTMLParser

from audit_signal_v17 import SignalParser, accessible_link_name


def parse(fragment: str) -> SignalParser:
    parser = SignalParser()
    parser.feed(fragment)
    return parser


def test_boolean_defer_presence() -> None:
    parser = parse('<script defer src="/assets/app.js"></script>')
    script = parser.scripts[0]
    assert script.get("defer") is None
    assert "defer" in script


def test_script_modes() -> None:
    parser = parse(
        '<script defer src="defer.js"></script>'
        '<script async src="async.js"></script>'
        '<script type="module" src="module.js"></script>'
        '<script src="blocking.js"></script>'
    )
    deferred, asynchronous, modules, blocking = parser.scripts
    assert "defer" in deferred
    assert "async" in asynchronous
    assert modules.get("type") == "module"
    assert "defer" not in blocking and "async" not in blocking and blocking.get("type") != "module"


def test_accessible_link_names() -> None:
    parser = parse(
        '<a href="/text">نص ظاهر</a>'
        '<a href="/aria" aria-label="اسم مساعد"><img src="a.png" alt=""></a>'
        '<a href="/title" title="عنوان الرابط"></a>'
        '<a href="/image"><img src="b.png" alt="وصف الصورة"></a>'
        '<a href="/bad"><img src="c.png" alt=""></a>'
    )
    names = [accessible_link_name(link) for link in parser.links]
    assert names == ["نص ظاهر", "اسم مساعد", "عنوان الرابط", "وصف الصورة", ""]


def main() -> None:
    test_boolean_defer_presence()
    test_script_modes()
    test_accessible_link_names()
    print("audit signal v17 regression tests passed")


if __name__ == "__main__":
    main()
